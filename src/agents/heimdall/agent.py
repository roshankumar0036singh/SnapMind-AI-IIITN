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
    verify_citation,
)

from dotenv import load_dotenv
load_dotenv()
from src.config import get_settings

# ---------------------------------------------------------------------------
# LLM provider setup — Groq primary, Gemini fallback
# ---------------------------------------------------------------------------
GROQ_BASE_URL = "https://api.groq.com/openai/v1"
GROQ_MODEL = os.getenv("GROQ_MODEL", "openai/gpt-oss-20b")
FALLBACK_MODELS = list(dict.fromkeys([
    GROQ_MODEL,
    "openai/gpt-oss-120b",
    "qwen/qwen3.8-27b",
]))
MAX_TOKENS = int(os.getenv("GROQ_MAX_TOKENS", "1500"))
TEMPERATURE = 0.0  # Deterministic — evidence analysis, not creative writing

GEMINI_BASE_URL = "https://generativelanguage.googleapis.com/v1beta/openai/"
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-1.5-flash")

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

def _extract_json(text: str) -> Optional[Dict[str, Any]]:
    """
    Extract the first valid JSON object from an LLM response.
    Handles: clean JSON, code-fence wrappers, preamble text, and
    truncated output (tries progressively shorter trailing substrings).
    """
    text = text.strip()

    # Strip ```json ... ``` or ``` ... ``` code fences
    fence_match = re.search(r'```(?:json)?\s*([\s\S]+?)```', text)
    if fence_match:
        text = fence_match.group(1).strip()

    # Try direct parse
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # Find the outermost { ... } block
    start = text.find('{')
    if start == -1:
        return None

    # Try from `start` to end
    try:
        return json.loads(text[start:])
    except json.JSONDecodeError:
        pass

    # The JSON may be truncated — walk backwards from the end to find a valid close
    candidate = text[start:]
    last_brace = len(candidate)
    for _ in range(50):  # max 50 shrink attempts
        last_brace = candidate.rfind('}', 0, last_brace)
        if last_brace == -1:
            break
        try:
            return json.loads(candidate[:last_brace + 1])
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

    # Initial evidence retrieval
    initial_docs_context = ""
    docs: List[Dict[str, Any]] = []
    try:
        docs = search_docs(
            query=question[:120],
            as_of=as_of,
            top_k=6,
        )
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

    llm_response_text = ""
    last_err = "GROQ_API_KEY not configured" if groq is None else None
    tokens_limit = MAX_TOKENS

    # ---------------------------------------------------------------
    # Phase A: Try all Groq models with per-model rate-limit retries
    # ---------------------------------------------------------------
    if groq is not None:
        for model_name in FALLBACK_MODELS:
            for attempt in range(3):
                try:
                    response = groq.chat.completions.create(
                        model=model_name,
                        messages=messages,
                        max_tokens=tokens_limit,
                        temperature=TEMPERATURE,
                    )
                    llm_response_text = response.choices[0].message.content or ""
                    _audit("llm_call_complete", {
                        "provider": "groq",
                        "model": model_name,
                        "tokens_used": response.usage.total_tokens if response.usage else 0,
                    })
                    last_err = None
                    break
                except Exception as e:
                    last_err = e
                    err_msg = str(e).lower()
                    is_rate_limit = (
                        "rate_limit" in err_msg or "429" in err_msg
                        or "413" in err_msg or "tpm" in err_msg or "otpm" in err_msg
                    )

                    if is_rate_limit:
                        if tokens_limit > 800:
                            tokens_limit = 800
                        # Honour Groq's retry-after hint if present
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

            if last_err is None:
                break  # got a good response

    # ---------------------------------------------------------------
    # Phase B: Gemini fallback (only if Groq completely failed)
    # ---------------------------------------------------------------
    if last_err is not None:
        gemini = _get_gemini_client()
        if gemini is not None:
            _audit("llm_gemini_fallback", {"groq_error": str(last_err)[:200]})
            try:
                response = gemini.chat.completions.create(
                    model=GEMINI_MODEL,
                    messages=messages,
                    max_tokens=MAX_TOKENS,
                    temperature=TEMPERATURE,
                )
                llm_response_text = response.choices[0].message.content or ""
                _audit("llm_call_complete", {
                    "provider": "gemini",
                    "model": GEMINI_MODEL,
                    "tokens_used": response.usage.total_tokens if response.usage else 0,
                })
                last_err = None
            except Exception as e:
                last_err = e
                _audit("llm_gemini_failed", {"error": str(e)[:300]})
        else:
            _audit("llm_gemini_skipped", {"reason": "GEMINI_API_KEY not set"})

    if last_err is not None:
        _audit("llm_call_failed", {"error": str(last_err), "traceback": traceback.format_exc()[:500]})
        return _make_failed_output(
            case_id=case_id,
            event_name=event_id or "Unverified Event",
            run_no=run_no,
            reason=f"LLM call failed: {last_err}",
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
            case_id=case_id,
            event_name=event_id or "Unverified Event",
            run_no=run_no,
            reason="LLM did not return valid JSON.",
            audit_events=audit_events,
            memory_actions=memory_actions,
        )

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

    # 4e. Enforce wake_next deterministically
    verdict = output.verification.verdict
    if verdict == "real":
        output.wake_next = "thor_and_loki"
        _audit("wake_next_enforced", {"verdict": verdict, "wake_next": "thor_and_loki"})
    elif verdict == "unverifiable":
        if output.evidence_gaps and output.verification.confidence >= 0.3:
            output.wake_next = "odin"
            _audit("wake_next_enforced", {"verdict": verdict, "wake_next": "odin"})
        else:
            output.wake_next = "none"
            _audit("wake_next_enforced", {"verdict": verdict, "wake_next": "none"})
    else:  # rumour
        output.wake_next = "none"
        _audit("wake_next_enforced", {"verdict": verdict, "wake_next": "none"})

    # 4f. Mark complete if scope and verdict are established
    if verdict in ("real", "unverifiable") and output.scope.scope_status == "complete":
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
