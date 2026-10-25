import uuid
from typing import List, Optional

from src.memory.store import AgentMemoryStore
from src.schemas.memory import MemoryRecord, MemoryType, MemoryScope, MemoryQuery


class MemoryManager:
    """
    Business logic and retrieval ranking for private agent memories.
    Fulfills CONTEXT_UPDATED.md Section 15.1.
    """

    def __init__(self, store: Optional[AgentMemoryStore] = None):
        self.store = store or AgentMemoryStore()

    def retrieve_relevant_memories(self, query: MemoryQuery) -> List[MemoryRecord]:
        """
        Retrieves top-k active memories for an agent matching the current case scope.
        Ranking hierarchy:
        1. Exact event scope match
        2. Country / Sector scope match
        3. Global scope lessons
        """
        all_memories = self.store.get_memories_for_agent(query.agent_id, status="active")
        if not all_memories:
            return []

        scored_records = []
        for mem in all_memories:
            score = mem.confidence

            # Scope matching bonuses
            if mem.scope == MemoryScope.EVENT and query.event_id:
                if mem.scope_value and mem.scope_value.lower() == query.event_id.lower():
                    score += 3.0
                else:
                    # Different event: ignore or deprioritize
                    score -= 1.0

            elif mem.scope in (MemoryScope.COUNTRY, MemoryScope.SECTOR):
                if query.country and mem.scope_value and mem.scope_value.lower() == query.country.lower():
                    score += 2.0
                elif query.sector and mem.scope_value and mem.scope_value.lower() == query.sector.lower():
                    score += 2.0

            elif mem.scope == MemoryScope.GLOBAL:
                score += 1.0

            scored_records.append((score, mem))

        # Sort descending by score
        scored_records.sort(key=lambda x: x[0], reverse=True)
        top_k = query.top_k or 5
        return [mem for _, mem in scored_records[:top_k]]

    def record_lesson(
        self,
        agent_id: str,
        memory_type: MemoryType,
        content: str,
        scope: MemoryScope = MemoryScope.GLOBAL,
        scope_value: Optional[str] = None,
        basis_refs: Optional[List[str]] = None,
        confidence: float = 1.0,
        run_no: int = 1,
    ) -> MemoryRecord:
        """
        Validates write qualification rules and persists a new memory record.
        """
        cleaned_content = content.strip()
        if len(cleaned_content) < 10:
            raise ValueError("Memory content must be at least 10 characters of actionable lesson.")

        record_id = f"MEM-{agent_id.upper()}-{uuid.uuid4().hex[:8]}"
        record = MemoryRecord(
            id=record_id,
            agent_id=agent_id.lower(),
            memory_type=memory_type,
            content=cleaned_content,
            scope=scope,
            scope_value=scope_value,
            basis_refs=basis_refs or [],
            confidence=confidence,
            created_run=run_no,
            last_used_run=run_no,
            status="active",
        )

        self.store.save_memory(record)
        return record
