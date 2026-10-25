"""
src/memory/memory_store.py
==========================
Private agent memory store.

Enforces agent_id isolation — an agent can ONLY read/write its own records.
Backed by the Supabase `agent_memories` and `memory_events` tables defined in
supabase_schema.sql.

Memory is NOT evidence. It is agent-internal strategy knowledge.
"""

from __future__ import annotations

import hashlib
import json
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from src.supabase_client import get_supabase_admin


# ---------------------------------------------------------------------------
# Valid agent IDs — enforced on every operation
# ---------------------------------------------------------------------------
VALID_AGENTS = {"heimdall", "thor", "loki", "odin"}

# Valid memory types for Heimdall
HEIMDALL_MEMORY_TYPES = {
    "query_strategy",
    "source_warning",
    "entity",
    "correction",
    "method_warning",
    "verification_rule",
    "failed_query",
    "document_quality",
}


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _assert_agent(agent_id: str) -> None:
    if agent_id not in VALID_AGENTS:
        raise ValueError(f"Invalid agent_id: {agent_id!r}. Must be one of {VALID_AGENTS}.")


# ---------------------------------------------------------------------------
# Write memory
# ---------------------------------------------------------------------------

def write_memory(
    agent_id: str,
    memory_type: str,
    content: str,
    basis_refs: List[str],
    scope: Optional[Dict[str, Any]] = None,
    confidence: float = 1.0,
    run_no: int = 1,
    case_id: Optional[str] = None,
    memory_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Persist a durable memory record for `agent_id`.

    Enforces:
    - Agent identity isolation (agent_id must match).
    - Schema validation (required fields present).
    - Deduplication: if a very similar active record exists (same agent + type +
      content hash), return the existing one without creating a duplicate.

    Returns the stored memory record dict.
    """
    _assert_agent(agent_id)

    if not content or not content.strip():
        raise ValueError("Memory content must not be empty.")
    if not basis_refs:
        raise ValueError("Memory must include at least one basis_ref citation.")

    mem_id = memory_id or f"{agent_id.upper()[:1]}-MEM-{uuid.uuid4().hex[:8].upper()}"
    content_hash = hashlib.sha256(f"{agent_id}:{memory_type}:{content}".encode()).hexdigest()[:16]

    db = get_supabase_admin()

    # Dedup check: look for an active record with the same content hash
    existing = (
        db.table("agent_memories")
        .select("id")
        .eq("agent_id", agent_id)
        .eq("memory_type", memory_type)
        .eq("status", "active")
        .like("content", f"%{content_hash}%")
        .limit(1)
        .execute()
    )
    if existing.data:
        return {"deduplicated": True, "existing_id": existing.data[0]["id"]}

    record = {
        "id": mem_id,
        "agent_id": agent_id,
        "memory_type": memory_type,
        "content": f"[hash:{content_hash}] {content}",
        "scope": json.dumps(scope or {}),
        "basis_refs": json.dumps(basis_refs),
        "confidence": confidence,
        "created_run": run_no,
        "last_used_run": run_no,
        "status": "active",
        "created_at": _now_iso(),
        "updated_at": _now_iso(),
    }

    result = db.table("agent_memories").insert(record).execute()

    # Append to memory_events audit log
    _log_memory_event(
        agent_id=agent_id,
        event_type="memory_written",
        memory_id=mem_id,
        case_id=case_id,
        run_no=run_no,
        reason=f"New {memory_type} lesson created",
    )

    return result.data[0] if result.data else record


# ---------------------------------------------------------------------------
# Read memory
# ---------------------------------------------------------------------------

def read_memory(
    agent_id: str,
    query: str,
    filters: Optional[Dict[str, Any]] = None,
    top_k: int = 5,
    run_no: int = 1,
    case_id: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """
    Retrieve up to `top_k` active memory records for `agent_id`.

    Filters supported:
    - memory_type: str
    - event_id: str  (matched against scope JSON)
    - min_confidence: float

    Enforces agent_id isolation — only this agent's records are returned.
    Excludes superseded and rejected records.
    """
    _assert_agent(agent_id)
    filters = filters or {}

    db = get_supabase_admin()

    q = (
        db.table("agent_memories")
        .select("*")
        .eq("agent_id", agent_id)
        .eq("status", "active")
    )

    if "memory_type" in filters:
        q = q.eq("memory_type", filters["memory_type"])

    if "min_confidence" in filters:
        q = q.gte("confidence", filters["min_confidence"])

    q = q.order("confidence", desc=True).limit(top_k * 3)  # over-fetch for client-side ranking
    result = q.execute()
    records = result.data or []

    # Client-side filter by event_id in scope JSON
    if "event_id" in filters and filters["event_id"]:
        event_filter = filters["event_id"]
        filtered = []
        for r in records:
            scope = json.loads(r.get("scope") or "{}")
            if scope.get("event_id") in (event_filter, None):
                filtered.append(r)
        records = filtered

    # Simple keyword ranking on content
    query_lower = query.lower()
    scored = []
    for r in records:
        score = r.get("confidence", 0.5)
        if query_lower in (r.get("content") or "").lower():
            score += 0.3
        if query_lower in (r.get("memory_type") or "").lower():
            score += 0.1
        scored.append((score, r))

    scored.sort(key=lambda x: x[0], reverse=True)
    top_records = [r for _, r in scored[:top_k]]

    if top_records:
        _log_memory_event(
            agent_id=agent_id,
            event_type="memory_read",
            memory_id=top_records[0].get("id", ""),
            case_id=case_id,
            run_no=run_no,
            reason=f"Query: {query[:120]}",
        )

    return top_records


# ---------------------------------------------------------------------------
# Update / supersede memory
# ---------------------------------------------------------------------------

def update_memory(
    agent_id: str,
    memory_id: str,
    updates: Dict[str, Any],
    run_no: int = 1,
    case_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Update an existing memory record owned by `agent_id`.
    Enforces ownership.
    """
    _assert_agent(agent_id)
    db = get_supabase_admin()

    # Verify ownership before update
    existing = (
        db.table("agent_memories")
        .select("id, agent_id")
        .eq("id", memory_id)
        .single()
        .execute()
    )
    if not existing.data:
        raise ValueError(f"Memory record {memory_id!r} not found.")
    if existing.data["agent_id"] != agent_id:
        raise PermissionError(
            f"Agent {agent_id!r} cannot modify memory owned by {existing.data['agent_id']!r}."
        )

    updates["updated_at"] = _now_iso()
    updates["last_used_run"] = run_no

    result = (
        db.table("agent_memories")
        .update(updates)
        .eq("id", memory_id)
        .execute()
    )

    _log_memory_event(
        agent_id=agent_id,
        event_type="memory_updated",
        memory_id=memory_id,
        case_id=case_id,
        run_no=run_no,
        reason=f"Updated fields: {list(updates.keys())}",
    )

    return result.data[0] if result.data else {}


def supersede_memory(
    agent_id: str,
    old_memory_id: str,
    new_content: str,
    new_basis_refs: List[str],
    run_no: int = 1,
    case_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Mark an old memory as superseded and write a new one.
    Preserves provenance.
    """
    _assert_agent(agent_id)

    # Mark old as superseded
    update_memory(
        agent_id=agent_id,
        memory_id=old_memory_id,
        updates={"status": "superseded"},
        run_no=run_no,
        case_id=case_id,
    )

    # Write new, referencing old
    new_id = f"{agent_id.upper()[:1]}-MEM-{uuid.uuid4().hex[:8].upper()}"
    return write_memory(
        agent_id=agent_id,
        memory_type="supersedes",
        content=f"[supersedes:{old_memory_id}] {new_content}",
        basis_refs=new_basis_refs + [old_memory_id],
        run_no=run_no,
        case_id=case_id,
        memory_id=new_id,
    )


# ---------------------------------------------------------------------------
# Append-only memory event log
# ---------------------------------------------------------------------------

def _log_memory_event(
    agent_id: str,
    event_type: str,
    memory_id: str,
    case_id: Optional[str] = None,
    run_no: int = 1,
    reason: str = "",
    previous_query: Optional[str] = None,
    new_query: Optional[str] = None,
    previous_filters: Optional[Dict[str, Any]] = None,
    new_filters: Optional[Dict[str, Any]] = None,
) -> None:
    """Write an immutable audit event to `memory_events`."""
    try:
        db = get_supabase_admin()
        db.table("memory_events").insert({
            "case_id": case_id,
            "run_no": run_no,
            "agent_id": agent_id,
            "event_type": event_type,
            "memory_id": memory_id,
            "previous_query": previous_query,
            "new_query": new_query,
            "previous_filters": json.dumps(previous_filters or {}),
            "new_filters": json.dumps(new_filters or {}),
            "reason": reason,
            "created_at": _now_iso(),
        }).execute()
    except Exception:
        # Audit log failure must never crash the agent
        pass
