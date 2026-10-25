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
        """
        try:
            res = (
                self.client.table(self.TABLE_NAME)
                .select("*")
                .eq("agent_id", agent_id.lower())
                .eq("status", status)
                .execute()
            )
            rows = res.data or []
            return [MemoryRecord(**row) for row in rows]
        except Exception as e:
            print(f"Warning: Failed to fetch memories from Supabase for {agent_id} ({e})")
            return []

    def save_memory(self, record: MemoryRecord) -> bool:
        """
        Upserts a private memory record into Supabase.
        """
        row = {
            "id": record.id,
            "agent_id": record.agent_id.lower(),
            "memory_type": record.memory_type.value if hasattr(record.memory_type, "value") else str(record.memory_type),
            "content": record.content,
            "scope": record.scope.value if hasattr(record.scope, "value") else str(record.scope),
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
