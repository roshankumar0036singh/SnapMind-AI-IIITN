from typing import List, Optional, Dict, Any

from src.supabase_client import get_supabase_client, get_supabase_admin
from src.schemas.memory import MemoryRecord, MemoryScope, MemoryType


class AgentMemoryStore:
    """
    CRUD persistence layer for private lasting agent memories in Supabase.
    Enforces strict agent_id isolation (Thor cannot read Loki's memory, Odin cannot read Thor's).
    Fulfills Phase 9 and CONTEXT_UPDATED.md Section 15.1.
    """

    TABLE_NAME = "agent_memories"

    def __init__(self):
        self._client = None
        self._admin = None

    @property
    def client(self):
        if self._client is None:
            self._client = get_supabase_client()
        return self._client

    @property
    def admin(self):
        if self._admin is None:
            self._admin = get_supabase_admin()
        return self._admin

    def get_memories_for_agent(
        self,
        agent_id: str,
        status: str = "active",
    ) -> List[MemoryRecord]:
        """
        Retrieves active memory records strictly filtered by agent_id.
        Uses admin client to bypass RLS.
        """
        try:
            res = (
                self.admin.table(self.TABLE_NAME)
                .select("*")
                .eq("agent_id", agent_id.lower())
                .eq("status", status)
                .execute()
            )
            rows = res.data or []
            records = []
            for row in rows:
                scope_val = row.get("scope") or "global"
                scope_key = scope_val
                sub_val = None
                if isinstance(scope_val, str) and ":" in scope_val:
                    scope_key, sub_val = scope_val.split(":", 1)
                elif isinstance(scope_val, str) and scope_val.startswith("{"):
                    import json
                    try:
                        scope_dict = json.loads(scope_val)
                        sub_val = scope_dict.get("event_id") or scope_dict.get("country")
                        scope_key = "event" if "event_id" in scope_dict else "global"
                    except Exception:
                        pass
                elif isinstance(scope_val, dict):
                    sub_val = scope_val.get("event_id") or scope_val.get("country")
                    scope_key = "event" if "event_id" in scope_val else "global"

                row_copy = dict(row)
                row_copy["scope"] = scope_key
                row_copy["scope_value"] = sub_val
                try:
                    records.append(MemoryRecord(**row_copy))
                except Exception:
                    pass
            return records
        except Exception as e:
            print(f"Warning: Failed to fetch memories from Supabase for {agent_id} ({e})")
            return []

    def save_memory(self, record: MemoryRecord) -> bool:
        """
        Upserts a private memory record into Supabase.
        """
        scope_str = record.scope.value if hasattr(record.scope, "value") else str(record.scope)
        if record.scope_value:
            scope_str = f"{scope_str}:{record.scope_value}"

        row = {
            "id": record.id,
            "agent_id": record.agent_id.lower(),
            "memory_type": record.memory_type.value if hasattr(record.memory_type, "value") else str(record.memory_type),
            "content": record.content,
            "scope": scope_str,
            "basis_refs": record.basis_refs,
            "confidence": record.confidence,
            "created_run": record.created_run,
            "last_used_run": record.last_used_run,
            "status": record.status,
        }

        try:
            self.admin.table(self.TABLE_NAME).upsert(row, on_conflict="id").execute()
            return True
        except Exception as e:
            raise RuntimeError(f"Failed to save memory record {record.id} to Supabase: {e}")

    def update_status(self, memory_id: str, new_status: str) -> bool:
        """
        Marks a memory record as 'superseded' or 'rejected'.
        """
        try:
            self.admin.table(self.TABLE_NAME).update({"status": new_status}).eq("id", memory_id).execute()
            return True
        except Exception as e:
            print(f"Warning: Failed to update memory status for {memory_id}: {e}")
            return False
