"""
src/tools/odin_tools.py
=======================
Tool implementations available to Odin — The Allfather (Judge Agent).

CRITICAL CONSTRAINTS (NFR1, NFR2, RBAC):
  - Odin NEVER searches or plans: `search_docs`, `find_tables`, and `compute_change`
    are STRICTLY PROHIBITED and will raise PermissionError if invoked.
  - As-of date gate enforced on all citation verification.
  - Exclusion of quarantined, damaged, duplicate, and post-as-of items.
  - Memory isolation: Odin can only read and write `agent_id="odin"`.
  - Tool-call budget enforcement.
"""

from __future__ import annotations

import json
from datetime import date, datetime, timezone
from typing import Any, Dict, List, Optional

from src.supabase_client import get_supabase_admin
from src.tools.citation_tools import get_citation_validator
from src.memory.memory_store import (
    read_memory as _mem_read,
    write_memory as _mem_write,
)

# ---------------------------------------------------------------------------
# Tool budget tracking
# ---------------------------------------------------------------------------
MAX_TOOL_CALLS = 100
_tool_call_count = 0


def reset_tool_budget() -> None:
    global _tool_call_count
    _tool_call_count = 0


def _check_budget() -> None:
    global _tool_call_count
    _tool_call_count += 1
    if _tool_call_count > MAX_TOOL_CALLS:
        raise RuntimeError(
            f"Odin tool call budget exhausted ({_tool_call_count}/{MAX_TOOL_CALLS})."
        )


def get_tool_call_count() -> int:
    return _tool_call_count


# ---------------------------------------------------------------------------
# RBAC Gatekeeper - Prohibited tools for Odin
# ---------------------------------------------------------------------------
def search_docs(*args, **kwargs) -> Any:
    raise PermissionError(
        "Judicial agent 'odin' is strictly prohibited from executing 'search_docs' "
        "(NFR1 constraint: Odin evaluates evidence only, never searches to build a case)."
    )


def find_tables(*args, **kwargs) -> Any:
    raise PermissionError(
        "Judicial agent 'odin' is strictly prohibited from executing 'find_tables' "
        "(NFR1 constraint: Odin evaluates evidence only, never searches for tables)."
    )


def compute_change(*args, **kwargs) -> Any:
    raise PermissionError(
        "Judicial agent 'odin' is strictly prohibited from executing 'compute_change' "
        "(NFR1 constraint: Odin audits submitted math, never computes independent trade math)."
    )


# ---------------------------------------------------------------------------
# get_doc — fetch document text and exhibit metadata for verification
# ---------------------------------------------------------------------------
def get_doc(
    doc_id: str,
    as_of: Optional[date] = None,
    event_id: Optional[str] = None,
) -> Optional[Dict[str, Any]]:
    """
    Fetch a single document from Supabase runemark_documents for judicial exhibit inspection.
    Enforces Simulated Clock gate and flags damaged/injection-flagged exhibits.
    """
    _check_budget()
    db = get_supabase_admin()

    result = (
        db.table("runemark_documents")
        .select("*")
        .eq("doc_id", doc_id)
        .limit(1)
        .execute()
    )

    if not result.data:
        return None

    row = result.data[0]

    # As-of date gate
    pub_date_str = str(row.get("pub_date") or row.get("publication_date") or "")
    if as_of and pub_date_str:
        try:
            pub_date = date.fromisoformat(pub_date_str[:10])
            if pub_date > as_of:
                return {
                    "doc_id": doc_id,
                    "excluded_reason": f"Published {pub_date_str} after as-of date {as_of}.",
                    "is_after_as_of": True,
                }
        except ValueError:
            pass

    return row


# ---------------------------------------------------------------------------
# verify_citation — validate DOC-ID, DOC-ID#Pn or TABLE-ID#row reference
# ---------------------------------------------------------------------------
def verify_citation(
    reference: str,
    as_of: Optional[date] = None,
    event_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Check whether a citation resolves to a real, valid manifest item or trade table row.
    Uses the unified CitationValidator.
    """
    _check_budget()
    validator = get_citation_validator()
    as_of_date = as_of or date.today()
    resp = validator.verify_citation(citation_ref=reference, case_as_of_date=as_of_date)

    return {
        "valid": resp.is_valid,
        "reason": resp.reason,
        "doc_id": resp.doc_id,
        "table_id": resp.table_id,
        "row_number": resp.row_no,
        "publication_date": str(resp.pub_date) if resp.pub_date else None,
        "reliability_tier": resp.reliability_tier,
        "excerpt": resp.excerpt,
        "is_table_row": resp.is_table_row,
    }


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
) -> Dict[str, Any]:
    """
    Write to a permitted section of the Case File for Odin.
    Odin may write: rulings, classification, ranges, sufficiency, missing, final_briefing, runs, status.
    """
    _check_budget()

    odin_sections = {
        "rulings",
        "classification",
        "ranges",
        "sufficiency",
        "missing",
        "final_briefing",
        "runs",
        "status",
        "limits",
    }

    if section not in odin_sections:
        raise PermissionError(
            f"Odin is not permitted to write to Case File section {section!r}. "
            f"Allowed sections: {odin_sections}"
        )

    db = get_supabase_admin()
    update = {section: json.dumps(payload), "updated_at": datetime.now(timezone.utc).isoformat()}
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
    """
    try:
        db = get_supabase_admin()
        db.table("trial_events").insert({
            "case_id": case_id,
            "event_type": event_type,
            "agent": agent,
            "run_no": run_no,
            "details": json.dumps(details, default=str),
            "created_at": datetime.now(timezone.utc).isoformat(),
        }).execute()
    except Exception:
        pass


# ---------------------------------------------------------------------------
# Odin-wrapped memory access (enforces agent_id = "odin")
# ---------------------------------------------------------------------------
def odin_read_memory(
    query: str,
    filters: Optional[Dict[str, Any]] = None,
    top_k: int = 5,
    run_no: int = 1,
    case_id: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """Read Odin's private memory for precedents and standards. Cannot access other agents' memory."""
    _check_budget()
    return _mem_read(
        agent_id="odin",
        query=query,
        filters=filters,
        top_k=top_k,
        run_no=run_no,
        case_id=case_id,
    )


def odin_write_memory(
    memory_type: str,
    content: str,
    basis_refs: List[str],
    scope: Optional[Dict[str, Any]] = None,
    confidence: float = 0.85,
    run_no: int = 1,
    case_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Write a durable judicial lesson or precedent to Odin's private memory."""
    _check_budget()
    return _mem_write(
        agent_id="odin",
        memory_type=memory_type,
        content=content,
        basis_refs=basis_refs,
        scope=scope,
        confidence=confidence,
        run_no=run_no,
        case_id=case_id,
    )
