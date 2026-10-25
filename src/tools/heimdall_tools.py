"""
src/tools/heimdall_tools.py
============================
Tool implementations available to the Heimdall agent.

CRITICAL: Every hard rule is enforced HERE in code, not just in the prompt.
  - As-of date gate (documents AND trade rows).
  - Event scope enforcement.
  - Exclusion of quarantined, damaged, duplicate, and post-as-of items.
  - Query deduplication (hash-based; no repeated normalised queries).
  - Tool-call budget enforcement.
  - Agent memory isolation (Heimdall may only read/write its own memory).
  - Citation validation (ref must resolve to a real manifest item or trade row).
  - Injection-flagged document policy enforcement.

The LLM cannot bypass any of these — they are enforced by the calling code,
not by instructions inside the model context.
"""

from __future__ import annotations

import hashlib
import json
import re
from datetime import date, datetime
from typing import Any, Dict, List, Optional, Tuple

from src.supabase_client import get_supabase_admin
from src.memory.memory_store import (
    read_memory as _mem_read,
    write_memory as _mem_write,
)

# ---------------------------------------------------------------------------
# Prompt-injection detection patterns
# ---------------------------------------------------------------------------
_INJECTION_PATTERNS: List[Tuple[str, str]] = [
    (r"ignore\s+(previous|all|your)\s+(instructions?|rules?|constraints?)", "directive_override"),
    (r"reveal\s+(your\s+)?(system\s+prompt|prompt|instructions?|rules?)", "prompt_extraction"),
    (r"you\s+are\s+now\s+(a\s+)?(?!heimdall|the\s+gatekeeper)", "role_hijack"),
    (r"(call|invoke|execute|run)\s+(this\s+)?(tool|function|api|endpoint)", "tool_manipulation"),
    (r"change\s+(your\s+)?(answer|response|output|conclusion)", "output_manipulation"),
    (r"do\s+not\s+cite\s+this", "citation_suppression"),
    (r"you\s+must\s+conclude", "forced_conclusion"),
    (r"forget\s+(everything|all|previous)", "memory_wipe"),
    (r"as\s+(a|an)\s+(language\s+model|llm|ai|assistant)", "identity_confusion"),
    (r"(new\s+instructions?|updated\s+instructions?|override\s+instructions?)", "instruction_override"),
]

_INJECTION_REGEX = [
    (re.compile(pattern, re.IGNORECASE), rule_id)
    for pattern, rule_id in _INJECTION_PATTERNS
]


def _scan_for_injection(text: str) -> List[Dict[str, Any]]:
    """Return list of detected injection patterns with rule IDs and spans."""
    detections = []
    for regex, rule_id in _INJECTION_REGEX:
        for m in regex.finditer(text):
            detections.append({
                "rule_id": rule_id,
                "pattern": m.group(0),
                "start": m.start(),
                "end": m.end(),
            })
    return detections


# ---------------------------------------------------------------------------
# Reliability weight computation (Section 15.3)
# ---------------------------------------------------------------------------

_TIER_WEIGHTS = {1: 1.00, 2: 0.80, 3: 0.60, 4: 0.25}

def compute_reliability_weight(
    tier: int,
    is_corrected: bool = False,
    correction_resolved: bool = False,
    is_retracted: bool = False,
    is_contradicted: bool = False,
    wrong_event: bool = False,
    is_damaged: bool = False,
    is_duplicate: bool = False,
    injection_flagged: bool = False,
) -> float:
    """
    Compute effective reliability weight.
    Hard gates: wrong_event, retracted, duplicate, injection_flagged → 0.
    """
    if wrong_event or is_retracted or is_duplicate or injection_flagged:
        return 0.0

    base = _TIER_WEIGHTS.get(tier, 0.25)

    correction_factor = 1.0
    if is_corrected:
        correction_factor = 0.85 if correction_resolved else 0.50

    contradiction_factor = 0.75 if is_contradicted else 1.0
    quality_factor = 0.60 if is_damaged else 1.0

    return round(base * correction_factor * contradiction_factor * quality_factor, 4)


# ---------------------------------------------------------------------------
# Query deduplication cache
# ---------------------------------------------------------------------------
_QUERY_CACHE: Dict[str, List[Dict[str, Any]]] = {}
_QUERY_COUNT: Dict[str, int] = {}

MAX_TOOL_CALLS = 30  # Heimdall-wide budget
_tool_call_counter = [0]

def _check_budget() -> None:
    if _tool_call_counter[0] >= MAX_TOOL_CALLS:
        raise RuntimeError(
            f"Heimdall tool-call budget exhausted ({MAX_TOOL_CALLS} calls). "
            "Stop searching, record the limit, and return current findings."
        )
    _tool_call_counter[0] += 1


def _query_hash(query: str, filters: Dict[str, Any]) -> str:
    payload = json.dumps({"q": query.strip().lower(), "f": filters}, sort_keys=True)
    return hashlib.sha256(payload.encode()).hexdigest()[:16]


def reset_tool_budget() -> None:
    """Call at the start of each agent invocation to reset counters."""
    _tool_call_counter[0] = 0
    _QUERY_CACHE.clear()
    _QUERY_COUNT.clear()


# ---------------------------------------------------------------------------
# search_docs — hybrid BM25 + vector with as-of gate
# ---------------------------------------------------------------------------

def search_docs(
    query: str,
    filters: Optional[Dict[str, Any]] = None,
    as_of: Optional[date] = None,
    event_id: Optional[str] = None,
    top_k: int = 8,
    embedding_fn=None,
) -> List[Dict[str, Any]]:
    """
    Hybrid document search with mandatory enforcement:
      - as_of date gate
      - event scope enforcement (if event_id provided)
      - exclusion of damaged, retracted, duplicate, injection-flagged docs
      - query deduplication
      - tool-call budget

    Returns a list of safe result dicts. Document content is labelled
    as `content_untrusted: True` so the LLM cannot mistake it for instructions.
    """
    _check_budget()
    filters = filters or {}

    # Resolve effective date gate
    effective_as_of = as_of or filters.get("date_lte")
    if isinstance(effective_as_of, str):
        effective_as_of = date.fromisoformat(effective_as_of)

    canonical_filters = {
        "date_lte": str(effective_as_of) if effective_as_of else None,
        "event_id": event_id or filters.get("event_id"),
        "country": filters.get("country"),
        "sector": filters.get("sector"),
        "exclude_retracted": filters.get("exclude_retracted", True),
        "exclude_damaged": filters.get("exclude_damaged", True),
        "exclude_duplicates": filters.get("exclude_duplicates", True),
        "max_tier": filters.get("max_tier", 4),
    }

    q_hash = _query_hash(query, canonical_filters)

    # Return cached result if query was already run
    if q_hash in _QUERY_CACHE:
        return _QUERY_CACHE[q_hash]

    db = get_supabase_admin()

    # --- BM25 / FTS path ---
    bm25_q = db.table("runemark_documents").select(
        "doc_id, title, content, country, sector, event_id, pub_date, "
        "source_type, reliability_tier, is_retracted, is_corrected, "
        "is_damaged, damage_type, is_duplicate, duplicate_of, is_injection_attempt, "
        "retracted_by, corrected_by"
    )

    if effective_as_of:
        bm25_q = bm25_q.lte("pub_date", str(effective_as_of))
    if canonical_filters["exclude_retracted"]:
        bm25_q = bm25_q.eq("is_retracted", False)
    if canonical_filters["exclude_damaged"]:
        bm25_q = bm25_q.eq("is_damaged", False)
    if canonical_filters["exclude_duplicates"]:
        bm25_q = bm25_q.eq("is_duplicate", False)
    if canonical_filters["country"]:
        bm25_q = bm25_q.eq("country", canonical_filters["country"])
    if canonical_filters["sector"]:
        bm25_q = bm25_q.eq("sector", canonical_filters["sector"])
    if canonical_filters["max_tier"] < 4:
        bm25_q = bm25_q.lte("reliability_tier", canonical_filters["max_tier"])

    # Injection policy: exclude injection-flagged by default
    bm25_q = bm25_q.eq("is_injection_attempt", False)

    # Multi-term / question keyword matching
    clean_query = query.strip()
    words = [w for w in clean_query.split() if len(w) > 2]
    if len(words) > 3:
        STOPWORDS = {
            "what", "when", "where", "which", "with", "from", "that", "this", "these", "those",
            "have", "been", "were", "will", "would", "could", "should", "give", "high", "range",
            "exposed", "about", "before", "after", "between", "under", "over", "does", "did",
            "many", "much", "more", "most", "some", "such", "than", "then", "into", "onto",
            "also", "only", "other", "their", "there", "they", "them", "then", "your", "ours",
            "january", "february", "march", "april", "may", "june", "july", "august", "september", "october", "november", "december"
        }
        tokens = re.findall(r'[A-Za-z0-9_-]+', clean_query)
        keywords = [t for t in tokens if len(t) > 3 and t.lower() not in STOPWORDS]
        caps = [t for t in keywords if t[0].isupper() or (t.startswith("E") and any(c.isdigit() for c in t))]
        others = [t for t in keywords if t not in caps]
        search_terms = (caps + others)[:6]
        if search_terms:
            or_conditions = []
            for t in search_terms:
                or_conditions.append(f"content.ilike.%{t}%")
                or_conditions.append(f"title.ilike.%{t}%")
            bm25_q = bm25_q.or_(",".join(or_conditions))
        else:
            bm25_q = bm25_q.or_(f"content.ilike.%{clean_query}%,title.ilike.%{clean_query}%")
    else:
        bm25_q = bm25_q.or_(f"content.ilike.%{clean_query}%,title.ilike.%{clean_query}%")

    bm25_q = bm25_q.limit(top_k * 4)
    raw_results = bm25_q.execute().data or []

    # --- Post-filter: event scope ---
    def _passes_event_filter(doc: Dict[str, Any]) -> bool:
        """Only include docs that match the event_id or have EVENT_ID = NONE (background)."""
        doc_event = (doc.get("event_id") or "NONE").upper()
        if not canonical_filters["event_id"]:
            return True  # No event scope restriction
        required = canonical_filters["event_id"].upper()
        if doc_event == required:
            return True
        if doc_event == "NONE":
            return True  # Background doc — allowed but must be flagged
        return False

    filtered = [d for d in raw_results if _passes_event_filter(d)]

    # Prioritize event-specific documents over background profiles
    filtered.sort(key=lambda d: 0 if (d.get("event_id") or "NONE").upper() not in ("NONE", "") else 1)
    # --- Scan retrieved content for injection patterns ---
    results = []
    for doc in filtered[:top_k]:
        content = doc.get("content", "")
        injection_hits = _scan_for_injection(content)
        is_background = (doc.get("event_id") or "NONE").upper() == "NONE"

        effective_weight = compute_reliability_weight(
            tier=doc.get("reliability_tier", 4),
            is_corrected=doc.get("is_corrected", False),
            correction_resolved=False,
            is_retracted=doc.get("is_retracted", False),
            is_contradicted=False,
            wrong_event=False,
            is_damaged=doc.get("is_damaged", False),
            is_duplicate=doc.get("is_duplicate", False),
            injection_flagged=bool(injection_hits),
        )

        results.append({
            "doc_id": doc["doc_id"],
            "title": doc.get("title"),
            "country": doc.get("country"),
            "sector": doc.get("sector"),
            "event_id": doc.get("event_id"),
            "pub_date": str(doc.get("pub_date") or ""),
            "source_type": doc.get("source_type"),
            "reliability_tier": doc.get("reliability_tier"),
            "is_retracted": doc.get("is_retracted", False),
            "retracted_by": doc.get("retracted_by"),
            "is_corrected": doc.get("is_corrected", False),
            "corrected_by": doc.get("corrected_by"),
            "is_damaged": doc.get("is_damaged", False),
            "damage_type": doc.get("damage_type"),
            "is_duplicate": doc.get("is_duplicate", False),
            "duplicate_of": doc.get("duplicate_of"),
            "is_background": is_background,
            "injection_detected": bool(injection_hits),
            "injection_patterns": injection_hits,
            "effective_weight": effective_weight,
            # Content is clearly labelled as untrusted data
            "content_untrusted": content[:2000],  # truncate to prevent prompt stuffing
            "content_full_available": len(content) > 2000,
        })

    _QUERY_CACHE[q_hash] = results
    return results


# ---------------------------------------------------------------------------
# get_doc — full document retrieval with safety checks
# ---------------------------------------------------------------------------

def get_doc(
    doc_id: str,
    as_of: Optional[date] = None,
    event_id: Optional[str] = None,
) -> Optional[Dict[str, Any]]:
    """
    Retrieve a single document by ID.
    Enforces: as-of date, event scope, injection scan.
    Returns None if the document is ineligible.
    """
    _check_budget()
    db = get_supabase_admin()

    doc = None
    try:
        result = (
            db.table("runemark_documents")
            .select("*")
            .eq("doc_id", doc_id)
            .limit(1)
            .execute()
        )
        if result.data:
            doc = result.data[0]
    except Exception:
        pass

    if not doc:
        try:
            from src.ingestion.okf_converter import OKFConverter
            doc = OKFConverter.load_okf_document(doc_id)
        except Exception:
            pass

    if not doc:
        return None

    # As-of gate
    if as_of and doc.get("pub_date"):
        pub = date.fromisoformat(str(doc["pub_date"]))
        if pub > as_of:
            return {
                "doc_id": doc_id,
                "excluded_reason": "post_as_of",
                "pub_date": str(pub),
                "as_of": str(as_of),
            }

    # Event scope check
    doc_event = (doc.get("event_id") or "NONE").upper()
    if event_id:
        required = event_id.upper()
        if doc_event not in (required, "NONE"):
            return {
                "doc_id": doc_id,
                "excluded_reason": "wrong_event",
                "doc_event_id": doc_event,
                "required_event_id": required,
            }

    # Hard gate: retracted
    if doc.get("is_retracted"):
        return {
            "doc_id": doc_id,
            "excluded_reason": "retracted",
            "retracted_by": doc.get("retracted_by"),
        }

    # Injection scan
    content = doc.get("content", "")
    injection_hits = _scan_for_injection(content)
    is_background = doc_event == "NONE"

    return {
        "doc_id": doc["doc_id"],
        "title": doc.get("title"),
        "country": doc.get("country"),
        "sector": doc.get("sector"),
        "event_id": doc.get("event_id"),
        "pub_date": str(doc.get("pub_date") or ""),
        "source_type": doc.get("source_type"),
        "reliability_tier": doc.get("reliability_tier"),
        "is_retracted": doc.get("is_retracted", False),
        "retracted_by": doc.get("retracted_by"),
        "is_corrected": doc.get("is_corrected", False),
        "corrected_by": doc.get("corrected_by"),
        "is_damaged": doc.get("is_damaged", False),
        "damage_type": doc.get("damage_type"),
        "is_duplicate": doc.get("is_duplicate", False),
        "duplicate_of": doc.get("duplicate_of"),
        "is_background": is_background,
        "injection_detected": bool(injection_hits),
        "injection_patterns": injection_hits,
        # Full content as untrusted data block
        "content_untrusted": content,
        "effective_weight": compute_reliability_weight(
            tier=doc.get("reliability_tier", 4),
            is_corrected=doc.get("is_corrected", False),
            is_retracted=doc.get("is_retracted", False),
            is_damaged=doc.get("is_damaged", False),
            is_duplicate=doc.get("is_duplicate", False),
            injection_flagged=bool(injection_hits),
        ),
    }


# ---------------------------------------------------------------------------
# find_tables — locate relevant trade tables
# ---------------------------------------------------------------------------

def find_tables(
    filters: Optional[Dict[str, Any]] = None,
    as_of: Optional[date] = None,
) -> List[Dict[str, Any]]:
    """
    Find trade tables matching filters. Returns metadata only (no raw rows).
    """
    _check_budget()
    filters = filters or {}
    db = get_supabase_admin()

    q = db.table("trade_tables").select(
        "table_id, country_pair, sector, unit, period, event_id, status, source_file"
    ).eq("status", "ok")

    if filters.get("event_id"):
        q = q.eq("event_id", filters["event_id"])
    if filters.get("country"):
        q = q.ilike("country_pair", f"%{filters['country']}%")
    if filters.get("sector"):
        q = q.eq("sector", filters["sector"])

    results = q.limit(20).execute()
    return results.data or []


# ---------------------------------------------------------------------------
# get_table — retrieve a trade table with as-of row filtering
# ---------------------------------------------------------------------------

def get_table(
    table_id: str,
    as_of: Optional[date] = None,
) -> Dict[str, Any]:
    """
    Retrieve a trade table and its rows.
    Enforces: excludes rows after as_of date; flags bad rows.
    Returns metadata + valid rows + excluded rows.
    """
    _check_budget()
    db = get_supabase_admin()

    # Table metadata
    table_res = (
        db.table("trade_tables")
        .select("*")
        .eq("table_id", table_id)
        .limit(1)
        .execute()
    )
    if not table_res.data:
        return {"table_id": table_id, "error": "not_found"}

    table_meta = table_res.data[0]

    # All rows for this table
    rows_res = (
        db.table("trade_rows")
        .select("*")
        .eq("table_id", table_id)
        .order("row_no")
        .execute()
    )
    all_rows = rows_res.data or []

    valid_rows = []
    excluded_rows = []
    issues = []

    seen_months = set()
    prev_row_no = None

    for row in all_rows:
        row_no = row.get("row_no")
        month_str = str(row.get("month") or "")
        row_status = row.get("row_status", "ok")

        # Check for row-number gaps
        if prev_row_no is not None and row_no is not None:
            if row_no != prev_row_no + 1:
                issues.append({
                    "issue_type": "row_number_gap",
                    "details": f"Gap between row {prev_row_no} and row {row_no}",
                })
        prev_row_no = row_no

        # As-of gate on trade rows
        if as_of and month_str:
            try:
                month_date = date.fromisoformat(month_str[:10])
                if month_date > as_of:
                    excluded_rows.append({**row, "exclusion_reason": "post_as_of"})
                    issues.append({
                        "issue_type": "post_as_of",
                        "details": f"Row {row_no} month {month_str} is after as-of {as_of}",
                        "row_no": row_no,
                    })
                    continue
            except ValueError:
                issues.append({
                    "issue_type": "bad_date",
                    "details": f"Row {row_no} has unparseable month: {month_str!r}",
                })

        # Repeated row check
        if month_str in seen_months:
            issues.append({
                "issue_type": "repeated_row",
                "details": f"Row {row_no} duplicates month {month_str}",
                "row_no": row_no,
            })
            excluded_rows.append({**row, "exclusion_reason": "repeated_month"})
            continue
        seen_months.add(month_str)

        # Row status check
        if row_status != "ok":
            excluded_rows.append({**row, "exclusion_reason": row_status})
            issues.append({
                "issue_type": row_status,
                "details": f"Row {row_no} status: {row_status} — {row.get('flag_reason', '')}",
                "row_no": row_no,
            })
            continue

        valid_rows.append(row)

    return {
        "table_id": table_id,
        "meta": table_meta,
        "valid_rows": valid_rows,
        "excluded_rows": excluded_rows,
        "issues": issues,
        "valid_row_count": len(valid_rows),
        "excluded_row_count": len(excluded_rows),
    }


# ---------------------------------------------------------------------------
# verify_citation — validate a DOC-ID or TABLE-ID#row reference
# ---------------------------------------------------------------------------

def verify_citation(
    reference: str,
    as_of: Optional[date] = None,
    event_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Check whether a citation reference resolves to a real, eligible manifest item
    or trade table row.

    Returns a dict with:
      - valid: bool
      - reason: str explaining the outcome
      - metadata: dict with doc/row info if found
    """
    _check_budget()
    db = get_supabase_admin()

    if not reference or not reference.strip():
        return {"valid": False, "reason": "Empty reference string", "metadata": {}}

    reference = reference.strip()

    # TABLE-ID#row format
    if "#" in reference:
        parts = reference.split("#", 1)
        table_id = parts[0]
        try:
            row_no = int(parts[1])
        except ValueError:
            return {
                "valid": False,
                "reason": f"Invalid row number in reference: {reference!r}",
                "metadata": {},
            }

        row_res = (
            db.table("trade_rows")
            .select("*")
            .eq("table_id", table_id)
            .eq("row_no", row_no)
            .limit(1)
            .execute()
        )
        if not row_res.data:
            return {
                "valid": False,
                "reason": f"Trade row {reference!r} not found in manifest.",
                "metadata": {},
            }

        row = row_res.data[0]
        month_str = str(row.get("month") or "")
        if as_of and month_str:
            try:
                month_date = date.fromisoformat(month_str[:10])
                if month_date > as_of:
                    return {
                        "valid": False,
                        "reason": f"Trade row month {month_str} is after as-of {as_of}.",
                        "metadata": row,
                    }
            except ValueError:
                pass

        if row.get("row_status", "ok") != "ok":
            return {
                "valid": False,
                "reason": f"Trade row has non-ok status: {row.get('row_status')}",
                "metadata": row,
            }

        return {"valid": True, "reason": "Trade row verified.", "metadata": row}

    # DOC-ID format
    doc = get_doc(doc_id=reference, as_of=as_of, event_id=event_id)
    if doc is None:
        return {
            "valid": False,
            "reason": f"Document {reference!r} not found in manifest.",
            "metadata": {},
        }
    if "excluded_reason" in doc:
        return {
            "valid": False,
            "reason": f"Document excluded: {doc['excluded_reason']}",
            "metadata": doc,
        }
    if doc.get("is_damaged"):
        return {
            "valid": False,
            "reason": f"Document is damaged ({doc.get('damage_type')}); cannot be cited.",
            "metadata": doc,
        }
    if doc.get("injection_detected"):
        return {
            "valid": False,
            "reason": "Document is injection-flagged; excluded from citation by policy.",
            "metadata": doc,
        }

    return {"valid": True, "reason": "Document verified.", "metadata": doc}


# ---------------------------------------------------------------------------
# read_case_file / post_to_case_file
# ---------------------------------------------------------------------------

def read_case_file(case_id: str) -> Optional[Dict[str, Any]]:
    """Read the shared Case File blackboard for a given case."""
    _check_budget()
    db = get_supabase_admin()
    result = (
        db.table("case_files")
        .select("*")
        .eq("case_id", case_id)
        .limit(1)
        .execute()
    )
    return result.data[0] if result.data else None


def post_to_case_file(
    case_id: str,
    section: str,
    payload: Dict[str, Any],
    allowed_sections: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """
    Write to a permitted section of the Case File.
    Heimdall may write: scope, verification, ingest_report, runs (evidence_index slot).
    This function enforces the section whitelist.
    """
    _check_budget()

    heimdall_sections = {"scope", "verification", "ingest_report", "runs", "limits"}
    allowed = allowed_sections or heimdall_sections

    if section not in allowed:
        raise PermissionError(
            f"Heimdall is not permitted to write to Case File section {section!r}. "
            f"Allowed sections: {allowed}"
        )

    db = get_supabase_admin()
    update = {section: json.dumps(payload), "updated_at": datetime.utcnow().isoformat()}
    result = (
        db.table("case_files")
        .update(update)
        .eq("case_id", case_id)
        .execute()
    )
    return result.data[0] if result.data else {}


# ---------------------------------------------------------------------------
# record_event — append-only audit trail
# ---------------------------------------------------------------------------

def record_event(
    case_id: str,
    event_type: str,
    agent: str,
    run_no: int,
    details: Dict[str, Any],
) -> None:
    """
    Append an audit event. Never modifies existing events.
    Failures here must not crash the agent.
    """
    try:
        db = get_supabase_admin()
        db.table("trial_events").insert({
            "case_id": case_id,
            "event_type": event_type,
            "agent": agent,
            "run_no": run_no,
            "details": json.dumps(details),
            "created_at": datetime.utcnow().isoformat(),
        }).execute()
    except Exception:
        pass  # Audit log failure must not crash the agent


# ---------------------------------------------------------------------------
# Heimdall-wrapped memory access (enforces agent_id = "heimdall")
# ---------------------------------------------------------------------------

def heimdall_read_memory(
    query: str,
    filters: Optional[Dict[str, Any]] = None,
    top_k: int = 5,
    run_no: int = 1,
    case_id: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """Read Heimdall's own private memory. Cannot access other agents' memory."""
    _check_budget()
    return _mem_read(
        agent_id="heimdall",
        query=query,
        filters=filters,
        top_k=top_k,
        run_no=run_no,
        case_id=case_id,
    )


def heimdall_write_memory(
    memory_type: str,
    content: str,
    basis_refs: List[str],
    scope: Optional[Dict[str, Any]] = None,
    confidence: float = 0.8,
    run_no: int = 1,
    case_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Write a durable lesson to Heimdall's private memory."""
    _check_budget()
    return _mem_write(
        agent_id="heimdall",
        memory_type=memory_type,
        content=content,
        basis_refs=basis_refs,
        scope=scope,
        confidence=confidence,
        run_no=run_no,
        case_id=case_id,
    )
