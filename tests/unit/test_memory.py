from unittest.mock import MagicMock
import pytest

from src.memory.store import AgentMemoryStore
from src.memory.manager import MemoryManager
from src.memory.logger import MemoryAuditLogger
from src.schemas.memory import MemoryType, MemoryScope, MemoryQuery, MemoryRecord


def test_memory_store_isolation():
    store = AgentMemoryStore()
    mock_client = MagicMock()
    mock_table = MagicMock()
    mock_select = MagicMock()
    mock_eq1 = MagicMock()
    mock_eq2 = MagicMock()
    mock_execute = MagicMock()

    mock_client.table.return_value = mock_table
    mock_table.select.return_value = mock_select
    mock_select.eq.return_value = mock_eq1
    mock_eq1.eq.return_value = mock_eq2
    mock_eq2.execute.return_value = mock_execute
    mock_execute.data = [
        {
            "id": "MEM-THOR-01",
            "agent_id": "thor",
            "memory_type": "search_strategy",
            "content": "Focus on port capacity declines.",
            "scope": "global",
            "confidence": 1.0,
            "status": "active",
        }
    ]
    store._client = mock_client

    memories = store.get_memories_for_agent("thor")
    assert len(memories) == 1
    assert memories[0].agent_id == "thor"

    # Verify query filtered by agent_id == 'thor'
    mock_select.eq.assert_called_with("agent_id", "thor")


def test_memory_manager_scope_ranking():
    mock_store = MagicMock()
    mock_store.get_memories_for_agent.return_value = [
        MemoryRecord(
            id="MEM-GLOBAL",
            agent_id="loki",
            memory_type=MemoryType.SOURCE_LESSON,
            content="General verification rule across all runs.",
            scope=MemoryScope.GLOBAL,
            confidence=1.0,
        ),
        MemoryRecord(
            id="MEM-EVENT-E5",
            agent_id="loki",
            memory_type=MemoryType.SEARCH_STRATEGY,
            content="Orvan rail routes offset sea corridor disruption.",
            scope=MemoryScope.EVENT,
            scope_value="E5",
            confidence=1.0,
        ),
    ]

    manager = MemoryManager(store=mock_store)
    query = MemoryQuery(agent_id="loki", event_id="E5", top_k=5)
    ranked = manager.retrieve_relevant_memories(query)

    assert len(ranked) == 2
    # Event-specific memory for E5 must rank higher than global
    assert ranked[0].id == "MEM-EVENT-E5"
    assert ranked[1].id == "MEM-GLOBAL"


def test_memory_audit_logger():
    logger = MemoryAuditLogger()
    event = logger.log_query_changed_by_memory(
        case_id="case_E5_001",
        run_no=2,
        agent_id="loki",
        memory_id="MEM-LOKI-01",
        previous_query="grain imports",
        new_query="grain imports official",
        previous_filters={"tier_max": 4},
        new_filters={"tier_max": 2},
        reason="Tier 4 source was rejected by Odin in Run 1",
    )

    assert event.event_type == "query_changed_by_memory"
    assert event.new_filters["tier_max"] == 2

    events = logger.get_events_for_case("case_E5_001")
    assert len(events) == 1
    assert events[0].event_type == "query_changed_by_memory"
