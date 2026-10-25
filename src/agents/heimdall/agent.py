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
import traceback
import uuid
from datetime import date, datetime, timezone
from typing import Any, Dict, List, Optional

from openai import OpenAI
from pydantic import ValidationError

from src.agents.prompts.heimdall_prompt import HEIMDALL_SYSTEM_PROMPT
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
    verify_citation,
)

# ---------------------------------------------------------------------------
# Groq client setup
# ---------------------------------------------------------------------------
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
GROQ_BASE_URL = "https://api.groq.com/openai/v1"
GROQ_MODEL = "llama-3.3-70b-versatile"
MAX_TOKENS = 4096
TEMPERATURE = 0.0  # Deterministic — evidence analysis, not creative writing

_groq_client: Optional[OpenAI] = None


def _get_groq_client() -> OpenAI:
    global _groq_client
    if _groq_client is None:
        if not GROQ_API_KEY:
            raise ValueError(
                "GROQ_API_KEY not set. Add it to .env file as GROQ_API_KEY=gsk_..."
            )
        _groq_client = OpenAI(
            api_key=GROQ_API_KEY,
            base_url=GROQ_BASE_URL,
        )
    return _groq_client


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


# ---------------------------------------------------------------------------
# JSON extraction helper
# ---------------------------------------------------------------------------

def _extract_json(text: str) -> Optional[Dict[str, Any]]:
    """
    Extract the first valid JSON object from an LLM response.
    The LLM is instructed to return ONLY JSON but may add preamble.
    """
    # Try direct parse first
    text = text.strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # Find first { ... } block
    match = re.search(r'\{[\s\S]+\}', text)
    if match:
        try:
            return json.loads(match.group(0))
        except json.JSONDecodeError:
            pass

    return None


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
            agent="heimdall",
            run_no=run_no,
            details=details,
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

    user_prompt = f"""
CASE ID: {case_id}
RUN: {run_no}
AS-OF DATE: {as_of_date or "UNKNOWN — search the event pack for a date"}
EVENT ID: {event_id or "UNKNOWN — resolve from corpus"}

USER QUESTION:
{question}
{memory_context}
{send_back_context}

INSTRUCTIONS:
1. Extract scope (event name, event ID, as-of date, countries, sectors, trade flows).
2. Search for evidence using the tools described in your prompt.
3. Verify the event as real / rumour / unverifiable.
4. Build the evidence index.
5. Report ingest quality.
6. Identify evidence gaps.
7. Return ONLY valid JSON matching the schema in section 17 of your prompt.

CRITICAL RULES:
- Do NOT use any date after {as_of_date or "the as-of date you find"} as evidence.
- Do NOT invent document IDs, dates, entity names, or citations.
- Every factual claim must cite a real DOC-ID or TABLE-ID#row.
- Do NOT estimate exposure magnitude (that is Thor and Loki's job).
- Do NOT plan for another agent.
- Distinguish sourced facts from inferences clearly.
"""

    groq = _get_groq_client()

    messages = [
        {"role": "system", "content": HEIMDALL_SYSTEM_PROMPT},
        {"role": "user", "content": user_prompt},
    ]

    llm_response_text = ""
    try:
        response = groq.chat.completions.create(
            model=GROQ_MODEL,
            messages=messages,
            max_tokens=MAX_TOKENS,
            temperature=TEMPERATURE,
        )
        llm_response_text = response.choices[0].message.content or ""
        _audit("llm_call_complete", {"tokens_used": response.usage.total_tokens if response.usage else 0})
    except Exception as e:
        _audit("llm_call_failed", {"error": str(e), "traceback": traceback.format_exc()[:500]})
        return _make_failed_output(
            run_no=run_no,
            reason=f"LLM call failed: {e}",
            audit_events=audit_events,
            memory_actions=memory_actions,
        )

    # ------------------------------------------------------------------
    # Step 3: Parse and validate LLM JSON output
    # ------------------------------------------------------------------
    raw_output = _extract_json(llm_response_text)
    if raw_output is None:
        _audit("json_parse_failed", {"raw_response_preview": llm_response_text[:500]})
        return _make_failed_output(
            run_no=run_no,
            reason="LLM did not return valid JSON.",
            audit_events=audit_events,
            memory_actions=memory_actions,
        )

    # Validate through Pydantic
    try:
        output = HeimdallOutput.model_validate(raw_output)
    except ValidationError as e:
        _audit("schema_validation_failed", {"errors": str(e)[:500]})
        # Try to salvage what we can
        output = _salvage_partial_output(raw_output, run_no, audit_events, memory_actions)

    # ------------------------------------------------------------------
    # Step 4: Enforce hard rules post-LLM
    # ------------------------------------------------------------------

    # 4a. Verify all citations the LLM proposed in the evidence index
    verified_index: List[EvidenceIndexEntry] = []
    for entry in output.evidence_index:
        ref = entry.ref
        if not ref:
            continue
        try:
            check = verify_citation(ref, as_of=as_of, event_id=output.scope.event_id)
            if not check["valid"]:
                entry.usable = False
                entry.warnings.append(f"Citation invalid: {check['reason']}")
                _audit("citation_invalid", {"ref": ref, "reason": check["reason"]})
            else:
                _audit("citation_verified", {"ref": ref})
        except Exception as e:
            entry.usable = False
            entry.warnings.append(f"Citation verification error: {e}")
        verified_index.append(entry)

    output.evidence_index = verified_index

    # 4b. Enforce as-of date on scope
    if as_of and output.scope.as_of and output.scope.as_of > as_of:
        _audit("as_of_override", {
            "llm_as_of": str(output.scope.as_of),
            "enforced_as_of": str(as_of),
        })
        output.scope.as_of = as_of

    # If LLM returned no as-of and we have one from the caller, set it
    if not output.scope.as_of and as_of:
        output.scope.as_of = as_of

    # 4c. Enforce wake_next rules
    verdict = output.verification.verdict
    if verdict in ("rumour", "unverifiable"):
        if output.wake_next == "thor_and_loki":
            output.wake_next = "odin" if verdict == "unverifiable" else "none"
            _audit("wake_next_corrected", {
                "verdict": verdict,
                "corrected_wake_next": output.wake_next,
            })

    # 4d. Do a search pass to augment evidence index if LLM left it sparse
    if len(output.evidence_index) < 3 and output.scope.event_id:
        _audit("sparse_evidence_fallback", {"existing_count": len(output.evidence_index)})
        try:
            fallback_results = search_docs(
                query=output.scope.event_name or question[:100],
                filters={
                    "event_id": output.scope.event_id,
                    "date_lte": str(as_of) if as_of else None,
                    "exclude_retracted": True,
                    "exclude_damaged": True,
                    "exclude_duplicates": True,
                },
                as_of=as_of,
                event_id=output.scope.event_id,
                top_k=5,
            )
            for doc in fallback_results:
                if not any(e.ref == doc["doc_id"] for e in output.evidence_index):
                    output.evidence_index.append(EvidenceIndexEntry(
                        ref=doc["doc_id"],
                        reason_relevant="Fallback search result",
                        event_id=doc.get("event_id"),
                        date=doc.get("pub_date"),
                        source_tier=doc.get("reliability_tier"),
                        country=doc.get("country"),
                        sector=doc.get("sector"),
                        usable=not doc.get("injection_detected", False),
                        warnings=["injection_flagged"] if doc.get("injection_detected") else [],
                        is_background=doc.get("is_background", False),
                        effective_weight=doc.get("effective_weight"),
                    ))
        except Exception as e:
            _audit("fallback_search_error", {"error": str(e)})

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
    run_no: int,
    reason: str,
    audit_events: List[AuditEvent],
    memory_actions: List[MemoryAction],
) -> HeimdallOutput:
    return HeimdallOutput(
        agent="heimdall",
        run_no=run_no,
        status="failed",
        verification=VerificationResult(
            verdict="unverifiable",
            confidence=0.0,
            reasons=[f"Agent failed: {reason}"],
        ),
        evidence_gaps=[reason],
        audit_events=audit_events + [AuditEvent(
            event_type="heimdall_failed",
            agent="heimdall",
            run_no=run_no,
            details={"reason": reason},
            timestamp=datetime.now(timezone.utc).isoformat(),
        )],
        memory_actions=memory_actions,
        wake_next="none",
    )


def _salvage_partial_output(
    raw: Dict[str, Any],
    run_no: int,
    audit_events: List[AuditEvent],
    memory_actions: List[MemoryAction],
) -> HeimdallOutput:
    """Try to salvage a partial LLM output that failed strict Pydantic validation."""
    output = HeimdallOutput(
        agent="heimdall",
        run_no=run_no,
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

    db.table("case_files").insert({
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
    }).execute()

    return cid
