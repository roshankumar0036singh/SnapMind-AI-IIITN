"""
src/agents/base.py
==================
Base agent architecture for Runemark agents (Thor, Loki).
Enforces:
  - Role-based tool access via AgentToolRegistry (NFR1 planner-free design)
  - Isolated private lasting memory per agent_id (Acceptance Check 9)
  - Google Gemini (gemini-2.5-flash) client with strict Pydantic structured output
  - Simulated clock and as-of date gating
"""

from __future__ import annotations

import os
from abc import ABC, abstractmethod
from datetime import date, datetime, timezone
from typing import Any, Dict, List, Optional, Type, TypeVar

from google import genai
from pydantic import BaseModel

from src.config import get_settings
from src.schemas.case_file import CaseFile, RunRecord, EventScope, CaseScope
from src.schemas.claims import Claim, Attack, Defence
from src.schemas.memory import MemoryQuery, MemoryType, MemoryScope, MemoryRecord
from src.tools.registry import get_tool_registry, AgentToolRegistry

T = TypeVar("T", bound=BaseModel)
settings = get_settings()


class BaseAgent(ABC):
    """
    Abstract Base Class for Thor and Loki agents.
    Provides standard Gemini generation, memory access, and tool execution.
    """

    DEFAULT_MODEL = "gemini-3.5-flash-lite"

    def __init__(self, agent_id: str):
        self.agent_id = agent_id.lower().strip()
        self.model_name = settings.GEMINI_MODEL or self.DEFAULT_MODEL
        self.tools: AgentToolRegistry = get_tool_registry()

        # Initialize Google GenAI Client
        api_key = settings.GEMINI_API_KEY or os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise ValueError(
                f"GEMINI_API_KEY not configured in .env for agent '{self.agent_id}'."
            )
        self.genai_client = genai.Client(api_key=api_key)

    @abstractmethod
    def can_wake(self, case: CaseFile) -> bool:
        """
        Deterministic wake-up condition evaluated over CaseFile state.
        Determined purely by CaseFile blackboard state — no supervisor planner.
        """
        pass

    @abstractmethod
    async def act(self, case: CaseFile) -> Dict[str, Any]:
        """
        Execute agent turn (formulate claims, attacks, or defences).
        """
        pass

    def call_gemini_structured(
        self,
        prompt: str,
        system_prompt: str,
        response_schema: Type[T],
        temperature: float = 0.1,
    ) -> T:
        """
        Calls Google Gemini API with guaranteed Pydantic structured output schema.
        Primary: gemini-3.5-flash-lite
        Fallback: gemini-3.6-flash (then gemini-2.5-flash)
        Includes automatic retry with exponential backoff on 503/429 errors.
        """
        import time
        from google.genai.errors import ServerError, ClientError

        # Model hierarchy: User defined -> gemini-3.5-flash-lite -> gemini-3.6-flash -> gemini-2.5-flash
        models_to_try = [
            self.model_name,
            "gemini-3.5-flash-lite",
            settings.GEMINI_FALLBACK_MODEL or "gemini-3.6-flash",
            "gemini-3.6-flash",
            "gemini-2.5-flash",
        ]
        # Deduplicate while preserving order
        unique_models = []
        for m in models_to_try:
            if m and m not in unique_models:
                unique_models.append(m)

        config = {
            "response_mime_type": "application/json",
            "response_schema": response_schema,
            "temperature": temperature,
            "system_instruction": system_prompt,
        }

        last_err = None
        for current_model in unique_models:
            for attempt in range(3):
                try:
                    response = self.genai_client.models.generate_content(
                        model=current_model,
                        contents=prompt,
                        config=config,
                    )
                    if response.parsed is not None:
                        return response.parsed
                    elif response.text:
                        # Attempt to parse json directly if response.parsed was None
                        import json
                        clean_text = response.text.strip()
                        if clean_text.startswith("```json"):
                            clean_text = clean_text[7:]
                        if clean_text.endswith("```"):
                            clean_text = clean_text[:-3]
                        parsed_dict = json.loads(clean_text)
                        return response_schema.model_validate(parsed_dict)
                except (ServerError, ClientError) as e:
                    last_err = e
                    status_code = getattr(e, "code", 500)
                    # Retry on 503 (Unavailable) or 429 (Resource Exhausted)
                    if "503" in str(e) or "429" in str(e) or status_code in (503, 429):
                        wait_sec = (attempt + 1) * 2
                        print(f"[{self.agent_id.upper()}] Gemini {current_model} busy ({e}). Retrying in {wait_sec}s...")
                        time.sleep(wait_sec)
                        continue
                    break
                except Exception as e:
                    last_err = e
                    break

        raise RuntimeError(
            f"Gemini generation failed for schema {response_schema.__name__} after retries: {last_err}"
        )

    def extract_scope_details(self, case: CaseFile) -> Dict[str, Any]:
        """
        Safely extracts event_id, target countries, sectors, and as_of date
        regardless of whether scope is stored as EventScope or CaseScope.
        """
        scope_obj = case.scope
        as_of_dt = case.as_of
        if isinstance(as_of_dt, str):
            as_of_dt = date.fromisoformat(as_of_dt)

        event_id = None
        countries: List[str] = []
        sectors: List[str] = []

        if scope_obj:
            if hasattr(scope_obj, "event_id") and scope_obj.event_id:
                event_id = scope_obj.event_id
            if hasattr(scope_obj, "target_countries") and scope_obj.target_countries:
                countries = list(scope_obj.target_countries)
            elif hasattr(scope_obj, "countries") and scope_obj.countries:
                countries = list(scope_obj.countries)

            if hasattr(scope_obj, "target_sectors") and scope_obj.target_sectors:
                sectors = list(scope_obj.target_sectors)
            elif hasattr(scope_obj, "sectors") and scope_obj.sectors:
                sectors = list(scope_obj.sectors)

            if hasattr(scope_obj, "as_of_date") and scope_obj.as_of_date:
                as_of_dt = scope_obj.as_of_date
            elif hasattr(scope_obj, "as_of") and scope_obj.as_of:
                as_of_dt = scope_obj.as_of

        return {
            "event_id": event_id,
            "countries": countries,
            "sectors": sectors,
            "as_of_date": as_of_dt,
        }

    def get_current_run(self, case: CaseFile) -> RunRecord:
        """
        Retrieves the active run or initializes Run 1 on the blackboard.
        """
        if not case.runs:
            run = RunRecord(run_no=1)
            case.runs.append(run)
            return run
        return case.runs[-1]

    def read_private_memory(
        self,
        event_id: Optional[str] = None,
        country: Optional[str] = None,
        sector: Optional[str] = None,
    ) -> List[MemoryRecord]:
        """
        Reads own private memory through the RBAC registry.
        Isolated strictly by agent_id (Thor cannot read Loki's memory).
        """
        memories = self.tools.execute_tool(
            self.agent_id,
            "read_memory",
            event_id=event_id,
            country=country,
            sector=sector,
            limit=5,
        )
        return memories or []

    def record_private_lesson(
        self,
        content: str,
        memory_type: str = "strategy",
        scope: str = "global",
        scope_value: Optional[str] = None,
        basis_refs: Optional[List[str]] = None,
        confidence: float = 0.9,
        run_no: int = 1,
    ) -> Any:
        """
        Writes a durable strategic lesson into own private lasting memory.
        """
        return self.tools.execute_tool(
            self.agent_id,
            "write_memory",
            content=content,
            memory_type=memory_type,
            scope=scope,
            scope_value=scope_value,
            basis_refs=basis_refs or [],
            confidence=confidence,
            run_no=run_no,
        )

    def log_trial_event(
        self,
        case_id: str,
        event_type: str,
        run_no: int,
        details: Dict[str, Any],
    ) -> None:
        """
        Appends an event to the trial_events audit table in Supabase.
        """
        try:
            admin_db = self.tools.searcher.client
            admin_db.table("trial_events").insert({
                "case_id": case_id,
                "event_type": event_type,
                "agent": self.agent_id,
                "run_no": run_no,
                "details": details,
                "created_at": datetime.now(timezone.utc).isoformat(),
            }).execute()
        except Exception as e:
            # Audit log failure must not crash the agent
            pass
