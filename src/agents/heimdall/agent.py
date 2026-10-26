"""
src/agents/heimdall/agent.py
=============================
Heimdall — Gatekeeper of the Trial of the Nine Realms.

Orchestrates the full case-creation workflow:
  1. Reads Case File and private memory.
  2. Extracts and normalises scope from the user question.
  3. Verifies the event (real / rumour / unverifiable).
  4. Builds evidence index.
  5. Reports ingest quality.
  6. Writes all results back to the shared Case File.
  7. Decides who wakes next.

LLM: Groq (llama-3.3-70b-versatile) via openai-compatible client.
The LLM is steered by HEIMDALL_SYSTEM_PROMPT but all hard rules are
enforced by the tool layer (heimdall_tools.py), which the LLM cannot bypass.
"""

from __future__ import annotations

import json
import os
import re
import time
import traceback
import uuid
from datetime import date, datetime, timezone
from typing import Any, Dict, List, Optional

from openai import OpenAI
from pydantic import ValidationError

from src.agents.prompts.heimdall_prompt import HEIMDALL_SYSTEM_PROMPT, HEIMDALL_SYNTHESIS_PROMPT
from src.agents.heimdall.verification import (
    extract_event_proposition,
    classify_evidence_relationship,
    evaluate_verification_verdict,
    build_verification_reasons,
)
from src.schemas.case_file import (
    AuditEvent,
    CaseScope,
    EvidenceIndexEntry,
    HeimdallOutput,
    IngestReport,
    MemoryAction,
    VerificationResult,
)
from src.tools.heimdall_tools import (
    compute_reliability_weight,
    find_tables,
    get_doc,
    get_table,
    heimdall_read_memory,
    heimdall_write_memory,
    post_to_case_file,
    read_case_file,
    record_event,
    reset_tool_budget,
    search_docs,
    search_knowledge_graph,
    verify_citation,
)

from dotenv import load_dotenv
load_dotenv()
from src.config import get_settings

# ---------------------------------------------------------------------------
# LLM provider setup — Groq primary, Gemini fallback
# ---------------------------------------------------------------------------
GROQ_BASE_URL = "https://api.groq.com/openai/v1"
GROQ_MODEL = os.getenv("GROQ_MODEL", "qwen/qwen3.8-27b")
FALLBACK_MODELS = list(dict.fromkeys([
    GROQ_MODEL,
    "qwen/qwen3.8-27b",
    "openai/gpt-oss-120b",
    "openai/gpt-oss-20b",
]))
MAX_TOKENS = int(os.getenv("GROQ_MAX_TOKENS", "2500"))
TEMPERATURE = 0.0  # Deterministic — evidence analysis, not creative writing

GEMINI_BASE_URL = "https://generativelanguage.googleapis.com/v1beta/openai/"
settings = get_settings()
GEMINI_MODEL = settings.GEMINI_MODEL or os.getenv("GEMINI_MODEL", "gemini-3.5-flash-lite")
GEMINI_FALLBACK_MODELS = list(dict.fromkeys([
    GEMINI_MODEL,
    settings.GEMINI_FALLBACK_MODEL or "gemini-2.5-flash",
    "gemini-2.5-flash",
]))

_groq_client: Optional[OpenAI] = None
_gemini_client: Optional[OpenAI] = None


def _get_groq_client() -> Optional[OpenAI]:
    global _groq_client
    if _groq_client is None:
        settings = get_settings()
        api_key = settings.GROQ_API_KEY or os.getenv("GROQ_API_KEY", "")
        if not api_key:
            return None
        _groq_client = OpenAI(
            api_key=api_key,
            base_url=GROQ_BASE_URL,
        )
    return _groq_client


def _get_gemini_client() -> Optional[OpenAI]:
    """Returns an OpenAI-compatible client for Gemini, or None if no key is set."""
    global _gemini_client
    if _gemini_client is None:
        settings = get_settings()
        api_key = settings.GEMINI_API_KEY or os.getenv("GEMINI_API_KEY", "")
        if not api_key:
            return None
        _gemini_client = OpenAI(
            api_key=api_key,
            base_url=GEMINI_BASE_URL,
        )
    return _gemini_client


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


# ---------------------------------------------------------------------------
# JSON extraction helper
# ---------------------------------------------------------------------------

def _repair_truncated_json(text: str) -> Optional[Dict[str, Any]]:
    """
    Repair truncated JSON strings (e.g. cut off by max_tokens).
    Balances unclosed quotes, brackets, and braces.
    """
    s = text.strip()
    if not s or not s.startswith('{'):
        return None

    stack = []
    in_string = False
    escape = False

    for c in s:
        if in_string:
            if escape:
                escape = False
            elif c == '\\':
                escape = True
            elif c == '"':
                in_string = False
        else:
            if c == '"':
                in_string = True
            elif c in ('{', '['):
                stack.append(c)
            elif c == '}':
                if stack and stack[-1] == '{':
                    stack.pop()
            elif c == ']':
                if stack and stack[-1] == '[':
                    stack.pop()

    repaired = s
    if in_string:
        repaired += '"'

    repaired = re.sub(r',\s*$', '', repaired)
    repaired = re.sub(r':\s*"?"?\s*$', '', repaired)

    for open_char in reversed(stack):
        if open_char == '{':
            repaired += '}'
        elif open_char == '[':
            repaired += ']'

    try:
        res = json.loads(repaired)
        if isinstance(res, dict):
            return res
    except Exception:
        pass

    # Progressively peel back to previous key-value separator
    for _ in range(50):
        idx = max(repaired[:-1].rfind(','), repaired[:-1].rfind('{'), repaired[:-1].rfind('['))
        if idx <= 0:
            break
        candidate = repaired[:idx]
        cand_stack = []
        cand_str = False
        cand_esc = False
        for ch in candidate:
            if cand_str:
                if cand_esc:
                    cand_esc = False
                elif ch == '\\':
                    cand_esc = True
                elif ch == '"':
                    cand_str = False
            else:
                if ch == '"':
                    cand_str = True
                elif ch in ('{', '['):
                    cand_stack.append(ch)
                elif ch == '}':
                    if cand_stack and cand_stack[-1] == '{':
                        cand_stack.pop()
                elif ch == ']':
                    if cand_stack and cand_stack[-1] == '[':
                        cand_stack.pop()
        for oc in reversed(cand_stack):
            if oc == '{':
                candidate += '}'
            elif oc == '[':
                candidate += ']'
        try:
            res = json.loads(candidate)
            if isinstance(res, dict):
                return res
        except Exception:
            repaired = candidate

    return None


def _extract_json(text: str) -> Optional[Dict[str, Any]]:
    """
    Extract the first valid JSON object from an LLM response.
    Handles: clean JSON, code-fence wrappers, preamble text, and
    truncated output (uses bracket stack balance and string repair).
    """
    if not text or not text.strip():
        return None
    text = text.strip()

    # Strip ```json ... ``` or ``` ... ``` code fences
    fence_match = re.search(r'```(?:json)?\s*([\s\S]+?)```', text)
    if fence_match:
        text = fence_match.group(1).strip()

    # Try direct parse
    try:
        res = json.loads(text)
        if isinstance(res, dict):
            return res
    except json.JSONDecodeError:
        pass

    # Find the outermost { ... } block
    start = text.find('{')
    if start == -1:
        return None

    candidate = text[start:]
    try:
        res = json.loads(candidate)
        if isinstance(res, dict):
            return res
    except json.JSONDecodeError:
        pass

    end = candidate.rfind('}')
    if end != -1 and end > 0:
        try:
            res = json.loads(candidate[:end + 1])
            if isinstance(res, dict):
                return res
        except json.JSONDecodeError:
            pass

    return _repair_truncated_json(candidate)


# ---------------------------------------------------------------------------
# Search strategy helpers
# ---------------------------------------------------------------------------

def _build_verification_searches(
    event_name: Optional[str],
    event_id: Optional[str],
    countries: List[str],
    sectors: List[str],
    as_of: Optional[date],
) -> List[Dict[str, Any]]:
    """
    Build a progressive set of focused search queries for event verification.
    Returns a list of {query, filters} dicts.
    """
    queries = []
    base_filters = {
        "date_lte": str(as_of) if as_of else None,
        "exclude_retracted": True,
        "exclude_damaged": True,
        "exclude_duplicates": True,
    }

    # Round 1: Direct event searches
    if event_name:
        queries.append({"query": event_name, "filters": {**base_filters, "event_id": event_id}})
    if event_id:
        queries.append({"query": f"event {event_id}", "filters": {**base_filters, "event_id": event_id}})

    # Round 2: Official notices
    if countries:
        for country in countries[:2]:
            queries.append({
                "query": f"official notice {country}",
                "filters": {**base_filters, "country": country, "max_tier": 1},
            })

    # Round 3: Corrections and retractions
    if event_name:
        queries.append({
            "query": f"correction retraction {event_name}",
            "filters": {**base_filters, "event_id": event_id},
        })

    # Round 4: Sector trade flows
    for sector in sectors[:2]:
        queries.append({
            "query": f"{sector} trade disruption imports exports",
            "filters": {**base_filters, "sector": sector, "event_id": event_id},
        })

    # Round 5: Contradictions
    if event_name:
        queries.append({
            "query": f"dispute contradiction deny {event_name}",
            "filters": {**base_filters, "event_id": event_id},
        })

    return queries


# ---------------------------------------------------------------------------
# Main Heimdall run function
# ---------------------------------------------------------------------------

def run_heimdall(
    case_id: str,
    question: str,
    as_of_date: Optional[str] = None,
    event_id: Optional[str] = None,
    run_no: int = 1,
    send_back_categories: Optional[List[str]] = None,
) -> HeimdallOutput:
    """
    Main entry point for the Heimdall agent.

    Parameters
    ----------
    case_id : str
        Unique identifier for this trial case.
    question : str
        The user's supply-chain disruption question.
    as_of_date : str, optional
        ISO date string (YYYY-MM-DD) for the temporal boundary.
    event_id : str, optional
        Pre-resolved event ID, if known.
    run_no : int
        Which run this is (1 = fresh case, 2+ = send-back).
    send_back_categories : list, optional
        Missing evidence categories from Odin's send-back.

    Returns
    -------
    HeimdallOutput
        Validated Pydantic model. Written to the Case File on success.
    """
    # Reset tool budget for this invocation
    reset_tool_budget()

    audit_events: List[AuditEvent] = []
    memory_actions: List[MemoryAction] = []

    def _audit(event_type: str, details: Dict[str, Any]) -> None:
        audit_events.append(AuditEvent(
            event_type=event_type,
            actor="heimdall",
            details={"run_no": run_no, **details},
            timestamp=_now_iso(),
        ))
        try:
            record_event(
                case_id=case_id,
                event_type=event_type,
                agent="heimdall",
                run_no=run_no,
                details=details,
            )
        except Exception:
            pass  # Audit failure must not crash the agent

    _audit("heimdall_started", {"question": question[:200], "as_of_date": as_of_date, "run_no": run_no})

    # ------------------------------------------------------------------
    # Step 1: Read Case File (if exists) and private memory
    # ------------------------------------------------------------------
    existing_case = None
    try:
        existing_case = read_case_file(case_id)
    except Exception as e:
        _audit("case_file_read_error", {"error": str(e)})

    # Parse as-of date
    as_of: Optional[date] = None
    if as_of_date:
        try:
            as_of = date.fromisoformat(as_of_date)
        except ValueError:
            _audit("as_of_parse_error", {"raw": as_of_date})

    # Read Heimdall's own private memory
    prior_memories: List[Dict[str, Any]] = []
    try:
        prior_memories = heimdall_read_memory(
            query=question[:200],
            filters={"event_id": event_id} if event_id else {},
            top_k=5,
            run_no=run_no,
            case_id=case_id,
        )
        if prior_memories:
            memory_actions.append(MemoryAction(
                action="read",
                memory_id=prior_memories[0].get("id", ""),
                reason=f"Pre-search memory retrieval. {len(prior_memories)} records found.",
            ))
            _audit("memory_read", {"count": len(prior_memories), "run_no": run_no})
    except Exception as e:
        _audit("memory_read_error", {"error": str(e)})

    # ------------------------------------------------------------------
    # Step 2: Build the LLM context and run initial scope extraction
    # ------------------------------------------------------------------
    memory_context = ""
    if prior_memories:
        memory_context = "\n\nRELEVANT PRIVATE MEMORY (yours — do not cite as evidence):\n"
        for m in prior_memories:
            memory_context += f"  [{m.get('id','')}] ({m.get('memory_type','')}) {m.get('content','')[:300]}\n"

    send_back_context = ""
    if send_back_categories:
        send_back_context = (
            "\n\nODIN SEND-BACK: The following evidence categories are missing. "
            "Search for NEW documents and rows for EACH category. "
            "Do not repeat Run 1 searches.\n"
            + "\n".join(f"  - {cat}" for cat in send_back_categories)
        )

    # Proposition pre-extraction for targeted retrieval
    prop_pre = extract_event_proposition(question, as_of_date=as_of, event_id=event_id)

    # Initial evidence retrieval
    initial_docs_context = ""
    docs: List[Dict[str, Any]] = []
    new_found_docs: List[Dict[str, Any]] = []
    try:
        # Round 1: General question search
        docs = search_docs(
            query=question[:200],
            as_of=as_of,
            event_id=event_id,
            top_k=6,
        )

        # Round 2: Specific claim & cause search
        claim_terms = []
        if prop_pre.get("subject") and prop_pre["subject"] != "Disruption Event":
            claim_terms.append(prop_pre["subject"])
        if prop_pre.get("cause"):
            claim_terms.append(prop_pre["cause"].replace("_", " "))
        if prop_pre.get("event_type") and prop_pre["event_type"] != "disruption":
            claim_terms.append(prop_pre["event_type"].replace("_", " "))
        claim_terms.extend(prop_pre.get("object", []))

        if claim_terms:
            claim_query = " ".join(claim_terms)
            claim_docs = search_docs(
                query=claim_query,
                as_of=as_of,
                event_id=event_id,
                top_k=6,
            )
            for cd in claim_docs:
                if not any(d.get("doc_id") == cd.get("doc_id") for d in docs):
                    docs.append(cd)
                    new_found_docs.append(cd)

        # Round 3: Operational status and authority search
        status_query = f"{prop_pre.get('subject', '')} authority operations berths open closed strike intact notice"
        status_docs = search_docs(
            query=status_query,
            as_of=as_of,
            event_id=event_id,
            top_k=6,
        )
        for sd in status_docs:
            if not any(d.get("doc_id") == sd.get("doc_id") for d in docs):
                docs.append(sd)
                new_found_docs.append(sd)

        # Targeted expansion for Odin send-back missing categories
        if send_back_categories:
            for cat in send_back_categories:
                cat_query = f"{question[:120]} {cat}"
                cat_docs = search_docs(
                    query=cat_query,
                    as_of=as_of,
                    event_id=event_id,
                    top_k=4,
                )
                for cd in cat_docs:
                    if not any(d.get("doc_id") == cd.get("doc_id") for d in docs):
                        docs.append(cd)
                        new_found_docs.append(cd)

        # Active memory adaptation: if prior memories note failed queries or query strategies
        if prior_memories:
            for m in prior_memories:
                m_type = m.get("memory_type", "")
                m_content = m.get("content", "")
                if m_type in ("failed_query", "query_strategy", "source_warning") and len(m_content) > 10:
                    # Clean the gap / strategy note to form a focused search query
                    clean_note = re.sub(r'Evidence gaps in run \d+:\s*', '', m_content)
                    adapted_query = f"{question[:120]} {clean_note[:80]}"
                    mem_docs = search_docs(
                        query=adapted_query,
                        as_of=as_of,
                        event_id=event_id,
                        top_k=4,
                    )
                    added_from_mem = False
                    for md in mem_docs:
                        if not any(d.get("doc_id") == md.get("doc_id") for d in docs):
                            docs.append(md)
                            new_found_docs.append(md)
                            added_from_mem = True

                    if added_from_mem:
                        _audit("query_changed_by_memory", {
                            "memory_id": m.get("id"),
                            "reason": f"Adapted search based on {m_type} memory: {m_content[:80]}",
                            "new_query": adapted_query,
                        })
                        memory_actions.append(MemoryAction(
                            action="applied",
                            memory_id=m.get("id", ""),
                            reason=f"Search expanded using guidance from {m_type}.",
                        ))

        if docs:
            initial_docs_context = "\n\nRETRIEVED CORPUS DOCUMENTS (evidence candidates):\n"
            for d in docs:
                content_text = d.get("content") or d.get("content_untrusted", "")
                event_code = d.get("event_id") or "NONE"
                initial_docs_context += (
                    f"  Doc ID: {d.get('doc_id')} | Event ID: {event_code} | Tier: T{d.get('reliability_tier', '3')} | Date: {d.get('pub_date')}\n"
                    f"  Title: {d.get('title')}\n"
                    f"  Content: {content_text[:350]}\n\n"
                )
    except Exception as e:
        _audit("initial_search_error", {"error": str(e)})

    # Graph RAG: Knowledge Graph topology & geopolitical scope
    graph_context = ""
    try:
        from src.retrieval.graph_retriever import get_graph_retriever
        graph_context = get_graph_retriever().format_graph_context_for_agent(
            agent_role="heimdall",
            country="Midgard",
            as_of_date=as_of,
        )
        if graph_context:
            _audit("graph_rag_retrieved", {"role": "heimdall"})
    except Exception as e:
        _audit("graph_rag_error", {"error": str(e)})

    # Compact, instruction-first user prompt (keeps token count low)
    doc_count = len(docs) if docs else 0
    user_prompt = (
        f"CASE ID: {case_id}\n"
        f"AS-OF DATE: {as_of_date or 'UNKNOWN'}\n"
        f"EVENT ID: {event_id or 'UNKNOWN — resolve from documents'}\n\n"
        f"QUESTION: {question}\n"
    )
    if memory_context:
        user_prompt += memory_context
    if send_back_context:
        user_prompt += send_back_context
    if graph_context:
        user_prompt += f"\n\n{graph_context}\n"
    if initial_docs_context:
        user_prompt += initial_docs_context
    else:
        user_prompt += "\nNo matching corpus documents found. Set verdict = unverifiable.\n"
    user_prompt += (
        f"\nINSTRUCTION: Output ONLY a JSON object. "
        f"Response must start with {{ and end with }}. No prose. No markdown."
    )

    groq = _get_groq_client()

    messages = [
        {"role": "system", "content": HEIMDALL_SYNTHESIS_PROMPT},
        {"role": "user", "content": user_prompt},
    ]

    raw_output: Optional[Dict[str, Any]] = None
    llm_response_text = ""
    last_err: Optional[Any] = "GROQ_API_KEY not configured" if groq is None else None

    # ---------------------------------------------------------------
    # Phase A: Try all Groq models with per-model rate-limit retries
    # ---------------------------------------------------------------
    if groq is not None:
        for model_name in FALLBACK_MODELS:
            tokens_limit = MAX_TOKENS
            for attempt in range(3):
                try:
                    call_kwargs: Dict[str, Any] = {
                        "model": model_name,
                        "messages": messages,
                        "max_tokens": tokens_limit,
                        "temperature": TEMPERATURE,
                    }
                    if "qwen" in model_name or "gpt-oss" in model_name:
                        call_kwargs["response_format"] = {"type": "json_object"}

                    response = groq.chat.completions.create(**call_kwargs)
                    llm_response_text = response.choices[0].message.content or ""
                    parsed = _extract_json(llm_response_text)
                    if parsed is not None and isinstance(parsed, dict):
                        raw_output = parsed
                        last_err = None
                        _audit("llm_call_complete", {
                            "provider": "groq",
                            "model": model_name,
                            "tokens_used": response.usage.total_tokens if response.usage else 0,
                        })
                        break
                    else:
                        _audit("llm_output_unparseable", {
                            "provider": "groq",
                            "model": model_name,
                            "attempt": attempt,
                            "preview": llm_response_text[:300],
                        })
                        last_err = f"Model {model_name} returned unparseable output"

                except Exception as e:
                    last_err = e
                    err_msg = str(e).lower()
                    is_rate_limit = (
                        "rate_limit" in err_msg or "429" in err_msg
                        or "413" in err_msg or "tpm" in err_msg or "otpm" in err_msg
                    )

                    if is_rate_limit:
                        if "otpm" in err_msg and tokens_limit > 1200:
                            tokens_limit = 1200
                        wait_time = 2.0 * (attempt + 1)
                        wait_match = re.search(r"try again in ([\d\.]+)s", err_msg)
                        if wait_match:
                            try:
                                wait_time = float(wait_match.group(1)) + 0.5
                            except ValueError:
                                pass
                        _audit("llm_rate_limit_retry", {
                            "model": model_name, "attempt": attempt,
                            "sleep_seconds": wait_time, "error": str(e)[:200],
                        })
                        if attempt == 2:
                            break  # exhausted retries for this model
                        time.sleep(min(wait_time, 20.0))
                        continue
                    else:
                        break  # non-rate-limit error, try next model

            if raw_output is not None:
                break  # got valid JSON

    # ---------------------------------------------------------------
    # Phase B: Gemini fallback (if Groq completely failed or didn't produce valid JSON)
    # ---------------------------------------------------------------
    if raw_output is None:
        gemini = _get_gemini_client()
        if gemini is not None:
            _audit("llm_gemini_fallback", {"groq_error": str(last_err)[:200] if last_err else "No valid JSON from Groq"})
            for g_model in GEMINI_FALLBACK_MODELS:
                for attempt in range(2):
                    try:
                        response = gemini.chat.completions.create(
                            model=g_model,
                            messages=messages,
                            max_tokens=MAX_TOKENS,
                            temperature=TEMPERATURE,
                            response_format={"type": "json_object"},
                        )
                        llm_response_text = response.choices[0].message.content or ""
                        parsed = _extract_json(llm_response_text)
                        if parsed is not None and isinstance(parsed, dict):
                            raw_output = parsed
                            last_err = None
                            _audit("llm_call_complete", {
                                "provider": "gemini",
                                "model": g_model,
                                "tokens_used": response.usage.total_tokens if response.usage else 0,
                            })
                            break
                    except Exception as e:
                        last_err = e
                        _audit("llm_gemini_failed", {"model": g_model, "attempt": attempt, "error": str(e)[:300]})
                        time.sleep(1.0)
                if raw_output is not None:
                    break
        else:
            _audit("llm_gemini_skipped", {"reason": "GEMINI_API_KEY not set"})

    if raw_output is None:
        _audit("llm_call_fallback_deterministic", {"reason": str(last_err)})
        raw_output = {
            "case_id": case_id,
            "event_name": prop_pre.get("subject") or event_id or "Disruption Event",
            "event_id": event_id,
            "as_of": as_of_date,
            "status": "complete",
            "scope": {
                "event_id": event_id,
                "event_name": prop_pre.get("subject") or "Disruption Event",
                "as_of": as_of_date,
                "countries": [prop_pre["location"]] if prop_pre.get("location") else [],
                "sectors": prop_pre.get("object", []),
                "trade_flows": [],
                "analysis_window": {"start": None, "end": as_of_date},
                "scope_status": "complete",
            },
            "verification": {
                "verdict": "unverifiable",
                "confidence": 0.0,
                "reasons": [],
            },
            "evidence_index": [],
            "evidence_gaps": [],
            "wake_next": "none",
        }

    # ------------------------------------------------------------------
    # Step 3: Parse and validate LLM JSON output
    # ------------------------------------------------------------------
    # Ensure case_id and event_name exist
    raw_output.setdefault("case_id", case_id)
    raw_output.setdefault("event_name", event_id or "Unverified Event")

    # Validate through Pydantic
    try:
        output = HeimdallOutput.model_validate(raw_output)
    except ValidationError as e:
        _audit("schema_validation_failed", {"errors": str(e)[:500]})
        # Try to salvage what we can
        output = _salvage_partial_output(raw_output, case_id, event_id or "Unverified Event", run_no, audit_events, memory_actions)

    # ------------------------------------------------------------------
    # Step 4: Enforce hard rules post-LLM
    # ------------------------------------------------------------------

    # 4a. Resolve and normalize event_id vs doc_id
    detected_event_id = event_id
    if not detected_event_id and docs:
        for d in docs:
            eid = d.get("event_id")
            if eid and eid.upper() not in ("NONE", ""):
                detected_event_id = eid
                break

    # If LLM put a doc_id (like ORV-0002) in event_id, normalize it
    if output.scope.event_id and (output.scope.event_id.startswith("ORV-") or output.scope.event_id.startswith("DOC-")):
        output.scope.event_id = detected_event_id
    if not output.scope.event_id and detected_event_id:
        output.scope.event_id = detected_event_id
    output.event_id = output.scope.event_id

    # Graph RAG scope enrichment: ensure all graph-modeled nations in question are included in scope
    try:
        from src.graph.store import get_graph_store
        g_store = get_graph_store()
        all_graph_nations = [n.name for n in g_store.nodes_data.values() if n.entity_type.value == "nation"]
        for nation in all_graph_nations:
            if nation.lower() in question.lower() and nation not in output.scope.countries:
                output.scope.countries.append(nation)
    except Exception:
        pass

    # 4b. Verify citations referenced by LLM
    for ref in (output.verification.supporting_refs or []):
        try:
            check = verify_citation(ref, as_of=as_of, event_id=output.scope.event_id)
            if not check["valid"]:
                _audit("citation_invalid", {"ref": ref, "reason": check["reason"]})
            else:
                _audit("citation_verified", {"ref": ref})
        except Exception as e:
            _audit("citation_error", {"ref": ref, "error": str(e)})

    # 4c. Compile candidate documents and build full evidence index
    all_candidate_docs: Dict[str, Dict[str, Any]] = {d["doc_id"]: d for d in (docs or []) if "doc_id" in d}
    if output.scope.event_id and len(all_candidate_docs) < 5:
        _audit("sparse_evidence_fallback", {"existing_count": len(all_candidate_docs)})
        try:
            fallback_results = search_docs(
                query=output.scope.event_name or question[:100],
                filters={
                    "event_id": output.scope.event_id,
                    "date_lte": str(as_of) if as_of else None,
                    "exclude_retracted": False,
                    "exclude_damaged": False,
                    "exclude_duplicates": True,
                },
                as_of=as_of,
                event_id=output.scope.event_id,
                top_k=6,
            )
            for doc in fallback_results:
                if doc.get("doc_id") and doc["doc_id"] not in all_candidate_docs:
                    all_candidate_docs[doc["doc_id"]] = doc
        except Exception as e:
            _audit("fallback_search_error", {"error": str(e)})

    # Build typed EvidenceIndexEntry items
    compiled_index: List[EvidenceIndexEntry] = []
    for doc_id, doc in all_candidate_docs.items():
        is_ret = doc.get("is_retracted", False)
        is_inj = doc.get("is_injection_attempt", False) or doc.get("injection_detected", False)
        is_dmg = doc.get("is_damaged", False)
        is_dup = doc.get("is_duplicate", False)
        tier_val = doc.get("reliability_tier") or 3
        try:
            tier_int = int(tier_val)
        except (ValueError, TypeError):
            tier_int = 3

        weight = compute_reliability_weight(
            tier=tier_int,
            is_retracted=is_ret,
            is_damaged=is_dmg,
            is_duplicate=is_dup,
            injection_flagged=is_inj,
        )

        warns: List[str] = []
        if is_inj:
            warns.append("injection_flagged")
        if is_ret:
            warns.append("retracted")
        if is_dmg:
            warns.append(f"damaged:{doc.get('damage_type', 'unknown')}")

        content_preview = (doc.get("content") or doc.get("content_untrusted") or "")[:200]
        compiled_index.append(EvidenceIndexEntry(
            entry_id=str(uuid.uuid4())[:8],
            doc_id=doc_id,
            ref=doc_id,
            title=doc.get("title", ""),
            source=doc.get("source_type", "unknown"),
            tier=f"T{tier_int}",
            date=doc.get("pub_date"),
            event_id=doc.get("event_id"),
            summary=content_preview,
            usable=weight > 0.0 and not is_inj and not is_ret,
            reliability_weight=weight,
            warnings=warns,
        ))

    output.evidence_index = compiled_index
    if send_back_categories and new_found_docs:
        new_ids = {d.get("doc_id") for d in new_found_docs if d.get("doc_id")}
        output.new_evidence = [e for e in compiled_index if e.doc_id in new_ids]
    elif run_no > 1:
        output.new_evidence = compiled_index

    # 4d. Enforce as-of date on scope
    if as_of and output.scope.as_of and output.scope.as_of > as_of:
        _audit("as_of_override", {
            "llm_as_of": str(output.scope.as_of),
            "enforced_as_of": str(as_of),
        })
        output.scope.as_of = as_of

    # If LLM returned no as-of and we have one from the caller, set it
    if not output.scope.as_of and as_of:
        output.scope.as_of = as_of

    # Enforce top-level as_of from caller (LLM sometimes leaves it null)
    if as_of_date and not output.as_of:
        try:
            output.as_of = date.fromisoformat(as_of_date)
        except Exception:
            pass

    # 4e. Deterministic Event Verification Evaluation
    candidate_doc_list = list(all_candidate_docs.values())
    prop = extract_event_proposition(
        question=question,
        as_of_date=as_of,
        event_id=output.scope.event_id or detected_event_id,
        hints={
            "subject": output.scope.event_name or output.event_name,
            "location": output.scope.countries[0] if output.scope.countries else None,
        },
    )
    det_eval = evaluate_verification_verdict(
        question=question,
        proposition=prop,
        as_of_date=as_of,
        retrieved_documents=candidate_doc_list,
        document_metadata=None,
        corrections=getattr(output.verification, "corrections", []),
        retractions=getattr(output.verification, "retractions", []),
        contradictions=getattr(output.verification, "contradictions", []),
        evidence_index=compiled_index,
    )

    # Enforce deterministic verification verdict and proposition metadata
    output.verification.verdict = det_eval["verdict"]
    output.verification.confidence = det_eval["confidence"]
    output.verification.proposition_status = det_eval["proposition_status"]
    output.verification.proposition = det_eval["proposition"]
    output.verification.evidence_roles = det_eval["evidence_roles"]
    output.verification.support_score = det_eval["support_score"]
    output.verification.contradiction_score = det_eval["contradiction_score"]
    output.verification.decision_basis = det_eval["decision_basis"]
    if det_eval["supporting_refs"]:
        output.verification.supporting_refs = det_eval["supporting_refs"]
    if det_eval["contradicting_refs"]:
        output.verification.contradicting_refs = det_eval["contradicting_refs"]
    if det_eval["reasons"]:
        output.verification.reasons = det_eval["reasons"]

    # 4f. Enforce wake_next deterministically based on proposition verdict
    verdict = output.verification.verdict
    if verdict == "real":
        output.wake_next = "thor_and_loki"
        _audit("wake_next_enforced", {"verdict": verdict, "wake_next": "thor_and_loki"})
    elif verdict == "unverifiable":
        output.wake_next = "none"
        _audit("wake_next_enforced", {"verdict": verdict, "wake_next": "none"})
    else:  # rumour
        output.wake_next = "none"
        _audit("wake_next_enforced", {"verdict": verdict, "wake_next": "none"})

    # 4g. Mark complete if scope and verdict are established
    if verdict in ("real", "rumour", "unverifiable") and output.scope.scope_status == "complete":
        output.status = "complete"

    # ------------------------------------------------------------------
    # Step 5: Write durable memory lessons
    # ------------------------------------------------------------------
    if output.verification.verdict == "real" and output.scope.event_id:
        try:
            mem_result = heimdall_write_memory(
                memory_type="verification_rule",
                content=(
                    f"Event {output.scope.event_id} ({output.scope.event_name}) verified as REAL "
                    f"in run {run_no} with confidence {output.verification.confidence:.2f}. "
                    f"Supporting refs: {', '.join(output.verification.supporting_refs[:3])}."
                ),
                basis_refs=output.verification.supporting_refs[:5] or ["question"],
                scope={"event_id": output.scope.event_id},
                confidence=output.verification.confidence,
                run_no=run_no,
                case_id=case_id,
            )
            memory_actions.append(MemoryAction(
                action="write",
                memory_id=mem_result.get("id", ""),
                reason="Verification result persisted for future runs.",
            ))
            _audit("memory_written", {"type": "verification_rule", "event_id": output.scope.event_id})
        except Exception as e:
            _audit("memory_write_error", {"error": str(e)})

    # Store failed queries in memory to prevent repetition
    if output.evidence_gaps:
        try:
            heimdall_write_memory(
                memory_type="failed_query",
                content=f"Evidence gaps in run {run_no}: {'; '.join(output.evidence_gaps[:5])}",
                basis_refs=["case_state"],
                scope={"event_id": output.scope.event_id},
                confidence=0.9,
                run_no=run_no,
                case_id=case_id,
            )
        except Exception:
            pass

    # ------------------------------------------------------------------
    # Step 6: Attach audit and memory actions to output
    # ------------------------------------------------------------------
    output.audit_events = audit_events
    output.memory_actions = memory_actions

    # ------------------------------------------------------------------
    # Step 7: Write to Case File blackboard
    # ------------------------------------------------------------------
    try:
        post_to_case_file(
            case_id=case_id,
            section="scope",
            payload=output.scope.model_dump(mode="json"),
        )
        post_to_case_file(
            case_id=case_id,
            section="verification",
            payload=output.verification.model_dump(mode="json"),
        )
        if output.ingest_report is not None:
            post_to_case_file(
                case_id=case_id,
                section="ingest_report",
                payload=output.ingest_report.model_dump(mode="json"),
            )
        _audit("case_file_updated", {"sections": ["scope", "verification", "ingest_report"]})
    except Exception as e:
        _audit("case_file_write_error", {"error": str(e)})
        output.status = "incomplete"

    _audit("heimdall_complete", {
        "verdict": output.verification.verdict,
        "wake_next": output.wake_next,
        "evidence_count": len(output.evidence_index),
        "gaps_count": len(output.evidence_gaps),
    })

    return output


# ---------------------------------------------------------------------------
# Helper: build a minimal failed output
# ---------------------------------------------------------------------------

def _make_failed_output(
    case_id: str,
    event_name: str,
    run_no: int,
    reason: str,
    audit_events: List[AuditEvent],
    memory_actions: List[MemoryAction],
) -> HeimdallOutput:
    return HeimdallOutput(
        case_id=case_id,
        event_name=event_name,
        status="failed",
        verification=VerificationResult(
            verdict="unverifiable",
            confidence=0.0,
            reasons=[f"Agent failed: {reason}"],
        ),
        evidence_gaps=[reason],
        audit_events=audit_events + [AuditEvent(
            event_type="heimdall_failed",
            actor="heimdall",
            details={"reason": reason, "run_no": run_no},
            timestamp=datetime.now(timezone.utc).isoformat(),
        )],
        memory_actions=memory_actions,
        wake_next="none",
    )


def _salvage_partial_output(
    raw: Dict[str, Any],
    case_id: str,
    event_name: str,
    run_no: int,
    audit_events: List[AuditEvent],
    memory_actions: List[MemoryAction],
) -> HeimdallOutput:
    """Try to salvage a partial LLM output that failed strict Pydantic validation."""
    output = HeimdallOutput(
        case_id=case_id,
        event_name=raw.get("event_name") or event_name,
        status="incomplete",
        audit_events=audit_events,
        memory_actions=memory_actions,
    )

    # Scope
    if "scope" in raw:
        try:
            output.scope = CaseScope.model_validate(raw["scope"])
        except Exception:
            pass

    # Verification
    if "verification" in raw:
        try:
            output.verification = VerificationResult.model_validate(raw["verification"])
        except Exception:
            pass

    # Ingest report
    if "ingest_report" in raw:
        try:
            output.ingest_report = IngestReport.model_validate(raw["ingest_report"])
        except Exception:
            pass

    # Evidence index
    if "evidence_index" in raw and isinstance(raw["evidence_index"], list):
        for item in raw["evidence_index"]:
            try:
                output.evidence_index.append(EvidenceIndexEntry.model_validate(item))
            except Exception:
                pass

    # Evidence gaps
    if "evidence_gaps" in raw and isinstance(raw["evidence_gaps"], list):
        output.evidence_gaps = [str(g) for g in raw["evidence_gaps"]]

    # Wake next
    if "wake_next" in raw and raw["wake_next"] in ("thor_and_loki", "odin", "none"):
        output.wake_next = raw["wake_next"]

    return output


# ---------------------------------------------------------------------------
# Case initialisation helper
# ---------------------------------------------------------------------------

def initialise_case(
    question: str,
    as_of_date: Optional[str] = None,
    event_id: Optional[str] = None,
    case_id: Optional[str] = None,
) -> str:
    """
    Create a new Case File record in Supabase and return the case_id.
    Call this before run_heimdall.
    """
    from src.supabase_client import get_supabase_admin

    cid = case_id or f"CASE-{uuid.uuid4().hex[:12].upper()}"
    db = get_supabase_admin()

    row_data = {
        "case_id": cid,
        "question": question,
        "as_of": as_of_date or _now_iso()[:10],
        "status": "open",
        "scope": "{}",
        "verification": "{}",
        "ingest_report": "{}",
        "runs": "[]",
        "limits": json.dumps({
            "max_runs": 3,
            "rounds_used": 0,
            "tool_calls_used": 0,
            "tokens_used": 0,
            "hit": False,
        }),
        "created_at": _now_iso(),
        "updated_at": _now_iso(),
    }

    for attempt in range(3):
        try:
            db.table("case_files").insert(row_data).execute()
            break
        except Exception:
            if attempt == 2:
                raise
            time.sleep(1.0)

    return cid
