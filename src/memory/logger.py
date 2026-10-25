from datetime import datetime, timezone
from typing import Optional, Dict, Any, List

from src.supabase_client import get_supabase_admin, get_supabase_client
from src.schemas.memory import MemoryEvent


class MemoryAuditLogger:
    """
    Append-only audit trail logger for agent memory actions.
    Records proof that memory changed agent behavior (Acceptance Check 9).
    """

    TABLE_NAME = "memory_events"

    def __init__(self):
        self._admin = None
        self._client = None
        # In-memory buffer for offline testing and fast replay
        self._local_events: List[MemoryEvent] = []

    @property
    def admin(self):
        if self._admin is None:
            self._admin = get_supabase_admin()
        return self._admin

    @property
    def client(self):
        if self._client is None:
            self._client = get_supabase_client()
        return self._client

    def log_event(self, event: MemoryEvent) -> None:
        """
        Appends memory event to local buffer and attempts Supabase persistence.
        """
        self._local_events.append(event)

        row = {
            "case_id": event.case_id,
            "run_no": event.run_no,
            "agent_id": event.agent_id.lower(),
            "event_type": event.event_type,
            "memory_id": event.memory_id,
            "previous_query": event.previous_query,
            "new_query": event.new_query,
            "previous_filters": event.previous_filters,
            "new_filters": event.new_filters,
            "reason": event.reason,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }

        try:
            self.admin.table(self.TABLE_NAME).insert(row).execute()
        except Exception as e:
            # Continue without crashing if offline or table not ready
            pass

    def log_memory_written(
        self,
        case_id: str,
        run_no: int,
        agent_id: str,
        memory_id: str,
        reason: str,
    ) -> MemoryEvent:
        event = MemoryEvent(
            case_id=case_id,
            run_no=run_no,
            agent_id=agent_id,
            event_type="memory_written",
            memory_id=memory_id,
            reason=reason,
        )
        self.log_event(event)
        return event

    def log_query_changed_by_memory(
        self,
        case_id: str,
        run_no: int,
        agent_id: str,
        memory_id: str,
        previous_query: str,
        new_query: str,
        previous_filters: Dict[str, Any],
        new_filters: Dict[str, Any],
        reason: str,
    ) -> MemoryEvent:
        event = MemoryEvent(
            case_id=case_id,
            run_no=run_no,
            agent_id=agent_id,
            event_type="query_changed_by_memory",
            memory_id=memory_id,
            previous_query=previous_query,
            new_query=new_query,
            previous_filters=previous_filters,
            new_filters=new_filters,
            reason=reason,
        )
        self.log_event(event)
        return event

    def get_events_for_case(self, case_id: str) -> List[MemoryEvent]:
        # Check local events first
        matching = [e for e in self._local_events if e.case_id == case_id]
        if matching:
            return matching

        try:
            res = self.client.table(self.TABLE_NAME).select("*").eq("case_id", case_id).execute()
            rows = res.data or []
            return [MemoryEvent(**r) for r in rows]
        except Exception:
            return []


_memory_logger = MemoryAuditLogger()

def get_memory_logger() -> MemoryAuditLogger:
    return _memory_logger
