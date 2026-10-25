"""
src/agents/thor/thor_agent.py
=============================
Thor: The Alarm.
Advocate for High Supply-Chain Exposure.
Deterministic wake conditions, autonomous Supabase retrieval, Gemini structured reasoning.
"""

from __future__ import annotations

import json
from typing import Any, Dict, List
from pydantic import BaseModel, Field

from src.agents.base import BaseAgent
from src.agents.prompts.thor_prompts import (
    THOR_SYSTEM_PROMPT,
    THOR_CLAIM_GENERATION_PROMPT,
    THOR_CROSS_EXAMINATION_PROMPT,
)
from src.agents.thor.thor_tools import ThorToolsBinding
from src.schemas.case_file import CaseFile, RunRecord
from src.schemas.claims import Claim, Attack, Defence, ClaimKind


class ThorRound1Output(BaseModel):
    claims: List[Claim] = Field(
        ...,
        min_length=1,
        description="2 to 3 evidence-backed claims arguing for high exposure.",
    )


class ThorRound2Output(BaseModel):
    attacks: List[Attack] = Field(
        ...,
        min_length=1,
        description="At least one targeted attack challenging Loki's claims.",
    )
    defences: List[Defence] = Field(
        default_factory=list,
        description="Responses to opposing attacks (new evidence or concession).",
    )


class ThorAgent(BaseAgent):
    """
    Thor: The Alarm Agent.
    Argues that supply-chain disruption causes severe, acute economic and physical exposure.
    """

    def __init__(self):
        super().__init__("thor")
        self.tools_binding = ThorToolsBinding(self.tools)

    def can_wake(self, case: CaseFile) -> bool:
        """
        Deterministic wake-up condition:
        1. Case verification is confirmed 'real'.
        2. Round 1: Thor has submitted 0 claims in the active run.
        3. Round 2: Both Thor and Loki have submitted claims, but Thor has 0 attacks in active run.
        """
        if not case.verification:
            return False

        verdict = getattr(case.verification, "verdict", "")
        if str(verdict).lower() != "real":
            return False

        current_run = self.get_current_run(case)
        thor_claims = [c for c in current_run.claims if c.agent == "thor"]
        loki_claims = [c for c in current_run.claims if c.agent == "loki"]
        thor_attacks = [a for a in current_run.attacks if a.from_agent == "thor"]

        # Round 1 condition: Thor needs to submit claims
        if len(thor_claims) == 0:
            return True

        # Round 2 condition: Both submitted Round 1 claims, Thor hasn't attacked yet
        if len(thor_claims) > 0 and len(loki_claims) > 0 and len(thor_attacks) == 0:
            return True

        return False

    async def act(self, case: CaseFile) -> Dict[str, Any]:
        """
        Executes Thor's turn based purely on blackboard state.
        """
        current_run = self.get_current_run(case)
        scope_info = self.extract_scope_details(case)
        as_of_date = scope_info["as_of_date"]
        target_country = scope_info["countries"][0] if scope_info["countries"] else None
        target_sector = scope_info["sectors"][0] if scope_info["sectors"] else None
        event_id = scope_info["event_id"]

        thor_claims = [c for c in current_run.claims if c.agent == "thor"]
        loki_claims = [c for c in current_run.claims if c.agent == "loki"]
        loki_attacks = [a for a in current_run.attacks if a.from_agent == "loki"]

        # -------------------------------------------------------------
        # 1. Check Private Lasting Memory (Acceptance Check 9)
        # -------------------------------------------------------------
        memories = self.read_private_memory(
            event_id=event_id,
            country=target_country,
            sector=target_sector,
        )
        max_tier_filter = 4
        applied_memory_notes = []

        for m in memories:
            content = getattr(m, "content", "")
            applied_memory_notes.append(content)
            # Memory-driven behavior adjustment:
            if "avoid tier 4" in content.lower() or "reject tier 4" in content.lower():
                max_tier_filter = 3
                self.log_trial_event(
                    case_id=case.case_id,
                    event_type="query_changed_by_memory",
                    run_no=current_run.run_no,
                    details={
                        "agent": "thor",
                        "memory_id": getattr(m, "id", "mem_thor"),
                        "reason": "Restricted search tier ceiling to Tier 3 based on prior judicial lesson.",
                        "new_max_tier": 3,
                    },
                )

        memory_context = (
            "\n".join([f"- {note}" for note in applied_memory_notes])
            if applied_memory_notes
            else "No relevant prior memory lessons."
        )

        # -------------------------------------------------------------
        # ROUND 1: GATHER HIGH-EXPOSURE EVIDENCE & SUBMIT CLAIMS
        # -------------------------------------------------------------
        if len(thor_claims) == 0:
            # 2. Autonomous search via Supabase & Gemini embeddings
            retrieved_docs = self.tools_binding.gather_high_exposure_evidence(
                question=case.question,
                as_of_date=as_of_date,
                country=target_country,
                sector=target_sector,
                event_id=event_id,
                max_tier=max_tier_filter,
                top_k=6,
            )

            # 3. Autonomous trade table decline calculations
            trade_calcs = self.tools_binding.compute_worst_case_trade_decline(
                sector=target_sector,
                country_pair=target_country,
                as_of_date=as_of_date,
            )

            # Format evidence for prompt
            docs_text = "\n\n".join([
                f"[{d.chunk_id or d.doc_id}] (Tier {d.reliability_tier}, Date: {d.pub_date}, Country: {d.country}, Sector: {d.sector}): "
                f"'{d.title}'\nExcerpt: {d.text}"
                for d in retrieved_docs
            ]) if retrieved_docs else "No direct document evidence retrieved from database."

            trade_text = "\n\n".join([
                f"Table {t.get('table_id')}: Baseline Avg = {t.get('baseline_average')}, "
                f"Post-Event Avg = {t.get('comparison_average')}, Drop = {t.get('percentage_change')}%. "
                f"Verifiable Row Citations: {t.get('citations')}"
                for t in trade_calcs
            ]) if trade_calcs else "No direct trade table rows found."

            prompt = THOR_CLAIM_GENERATION_PROMPT.format(
                question=case.question,
                as_of=str(as_of_date),
                scope=json.dumps(scope_info, default=str),
                evidence_text=docs_text,
                trade_text=trade_text,
                memory_context=memory_context,
            )

            # 4. Generate structured claims via Gemini 2.5 Flash
            result: ThorRound1Output = self.call_gemini_structured(
                prompt=prompt,
                system_prompt=THOR_SYSTEM_PROMPT,
                response_schema=ThorRound1Output,
                temperature=0.1,
            )

            # Standardize claim metadata
            for idx, c in enumerate(result.claims):
                c.agent = "thor"
                c.run_no = current_run.run_no
                c.round_no = 1
                c.status = "submitted"
                if target_country and c.country.lower() not in [x.lower() for x in scope_info.get("countries", [])]:
                    c.country = target_country
                if target_sector and c.sector.lower() not in [x.lower() for x in scope_info.get("sectors", [])]:
                    c.sector = target_sector
                if not c.claim_id:
                    c.claim_id = f"CLM-THOR-R{current_run.run_no}-{idx+1:02d}"

            current_run.claims.extend(result.claims)

            self.log_trial_event(
                case_id=case.case_id,
                event_type="thor_claims_submitted",
                run_no=current_run.run_no,
                details={
                    "claims_count": len(result.claims),
                    "claim_ids": [c.claim_id for c in result.claims],
                },
            )

            return {
                "agent": "thor",
                "round": 1,
                "action": "claims_submitted",
                "claims": [c.model_dump(mode="json") for c in result.claims],
            }

        # -------------------------------------------------------------
        # ROUND 2: CROSS-EXAMINATION (ATTACKS & DEFENCES)
        # -------------------------------------------------------------
        # Search fresh counter-evidence to refute Loki's resilience claims
        dispute_topic = case.question
        new_counter_docs = self.tools_binding.search_counter_evidence(
            dispute_topic=dispute_topic,
            as_of_date=as_of_date,
            max_tier=3,
            top_k=4,
        )

        new_docs_text = "\n\n".join([
            f"[{d.chunk_id or d.doc_id}] (Tier {d.reliability_tier}): {d.title}\n{d.text}"
            for d in new_counter_docs
        ]) if new_counter_docs else "No additional counter-evidence retrieved."

        opponent_claims_json = [c.model_dump(mode="json") for c in loki_claims]
        opponent_attacks_json = [a.model_dump(mode="json") for a in loki_attacks]

        prompt = THOR_CROSS_EXAMINATION_PROMPT.format(
            question=case.question,
            as_of=str(as_of_date),
            opponent_claims=json.dumps(opponent_claims_json, indent=2),
            opponent_attacks=json.dumps(opponent_attacks_json, indent=2),
            new_evidence_text=new_docs_text,
        )

        result_r2: ThorRound2Output = self.call_gemini_structured(
            prompt=prompt,
            system_prompt=THOR_SYSTEM_PROMPT,
            response_schema=ThorRound2Output,
            temperature=0.1,
        )

        # Standardize attack metadata
        for idx, a in enumerate(result_r2.attacks):
            a.from_agent = "thor"
            if not a.attack_id:
                a.attack_id = f"ATK-THOR-R{current_run.run_no}-{idx+1:02d}"

        # Standardize defence metadata
        for idx, d in enumerate(result_r2.defences):
            if not d.defence_id:
                d.defence_id = f"DEF-THOR-R{current_run.run_no}-{idx+1:02d}"

            # If Thor conceded, store durable strategic lesson in private memory
            if d.response_type == "concede":
                self.record_private_lesson(
                    content=f"Conceded on {d.attack_id}: {d.text}",
                    memory_type="concession_rationale",
                    scope="country",
                    scope_value=target_country,
                    basis_refs=d.new_refs,
                    confidence=0.95,
                    run_no=current_run.run_no,
                )

        current_run.attacks.extend(result_r2.attacks)
        current_run.defences.extend(result_r2.defences)

        self.log_trial_event(
            case_id=case.case_id,
            event_type="thor_cross_examination_complete",
            run_no=current_run.run_no,
            details={
                "attacks_count": len(result_r2.attacks),
                "defences_count": len(result_r2.defences),
            },
        )

        return {
            "agent": "thor",
            "round": 2,
            "action": "cross_examination_submitted",
            "attacks": [a.model_dump(mode="json") for a in result_r2.attacks],
            "defences": [d.model_dump(mode="json") for d in result_r2.defences],
        }
