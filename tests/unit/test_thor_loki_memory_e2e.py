"""
tests/unit/test_thor_loki_memory_e2e.py
=======================================
Unit & E2E tests for Thor and Loki's private agent memory:
  1. Private memory isolation (FR6.1 - Thor cannot read Loki's memory).
  2. Memory-driven behavioral change with logged event (Acceptance Check 9).
  3. Post-trial judicial memory distillation (FR6.1 - Learning from Odin's rulings).
"""

from datetime import date
from unittest.mock import MagicMock, patch
import pytest

from src.agents.thor.thor_agent import ThorAgent
from src.agents.loki.loki_agent import LokiAgent
from src.schemas.case_file import CaseFile, RunRecord, EventScope, CaseStatus
from src.schemas.claims import Claim
from src.schemas.rulings import Ruling, RulingOutcome, RulingBasis
from src.schemas.memory import MemoryRecord, MemoryType, MemoryScope
from src.memory.manager import MemoryManager
from src.engine.trial_workflow import distill_agent_memories_post_trial


class MockMemoryStore:
    def __init__(self):
        self.memories = []

    def get_memories_for_agent(self, agent_id: str, status: str = "active"):
        return [m for m in self.memories if m.agent_id == agent_id.lower() and m.status == status]

    def save_memory(self, record):
        self.memories.append(record)
        return True


def test_thor_and_loki_memory_isolation():
    """Verify Thor cannot read Loki's memory and vice-versa (FR6.1)."""
    mock_store = MockMemoryStore()
    manager = MemoryManager(store=mock_store)

    # Seed Thor lesson
    thor_mem = manager.record_lesson(
        agent_id="thor",
        memory_type=MemoryType.SOURCE_LESSON,
        content="Avoid Tier 4 social rumors in Skagen maritime transit.",
        scope=MemoryScope.GLOBAL,
        basis_refs=["DOC-01"],
    )

    # Seed Loki lesson
    loki_mem = manager.record_lesson(
        agent_id="loki",
        memory_type=MemoryType.SEARCH_STRATEGY,
        content="Search alternative rail transit corridors for grain mitigation.",
        scope=MemoryScope.SECTOR,
        scope_value="agriculture",
        basis_refs=["DOC-02"],
    )

    # Thor queries memory
    from src.schemas.memory import MemoryQuery
    thor_results = manager.retrieve_relevant_memories(MemoryQuery(agent_id="thor"))
    assert len(thor_results) == 1
    assert thor_results[0].agent_id == "thor"
    assert "Avoid Tier 4" in thor_results[0].content

    # Loki queries memory
    loki_results = manager.retrieve_relevant_memories(MemoryQuery(agent_id="loki"))
    assert len(loki_results) == 1
    assert loki_results[0].agent_id == "loki"
    assert "rail transit" in loki_results[0].content


def test_acceptance_check_9_behavior_modification_logged():
    """
    Acceptance Check 9:
    Logged action shows memory changing what an agent did (query_changed_by_memory).
    """
    thor = ThorAgent()

    # Mock read_private_memory to return a rule saying 'avoid tier 4'
    mock_memory = MemoryRecord(
        id="MEM-THOR-TEST-01",
        agent_id="thor",
        memory_type=MemoryType.SOURCE_LESSON,
        content="Prior judicial ruling: avoid tier 4 rumors in Tolan wheat trade.",
        scope=MemoryScope.GLOBAL,
        basis_refs=["DOC-HIST-001"],
    )

    case = CaseFile(
        case_id="CASE-MEM-TEST-01",
        question="What is the exposure in Tolan wheat trade?",
        as_of=date(2027, 1, 25),
        status=CaseStatus.OPEN,
        scope=EventScope(
            event_id="E5",
            event_name="Port Strike",
            target_countries=["Tolan"],
            target_sectors=["wheat"],
            as_of_date=date(2027, 1, 25),
        ),
        runs=[RunRecord(run_no=1)],
    )

    with patch.object(thor, "read_private_memory", return_value=[mock_memory]):
        with patch.object(thor, "log_trial_event") as mock_log_event:
            with patch.object(thor.tools_binding, "gather_high_exposure_evidence", return_value=[]) as mock_gather:
                with patch.object(thor.tools_binding, "compute_worst_case_trade_decline", return_value=[]):
                    with patch.object(thor, "call_gemini_structured", return_value=MagicMock(claims=[])):
                        import asyncio
                        asyncio.run(thor.act(case))

                        # Verify behavior modification occurred: max_tier restricted from 4 to 3
                        mock_gather.assert_called_once()
                        _, kwargs = mock_gather.call_args
                        assert kwargs.get("max_tier") == 3, "Thor should have modified search tier to 3 based on memory"

                        # Verify Acceptance Check 9 event was logged
                        assert mock_log_event.called
                        call_args = mock_log_event.call_args_list
                        event_types = [c[1].get("event_type") for c in call_args]
                        assert "query_changed_by_memory" in event_types, "Must log query_changed_by_memory event"


def test_post_trial_memory_distillation():
    """Verify Thor and Loki learn durable lessons from Odin's rulings."""
    mock_store = MockMemoryStore()
    manager = MemoryManager(store=mock_store)

    case = CaseFile(
        case_id="CASE-DISTILL-01",
        question="Test Question",
        as_of=date(2027, 1, 25),
        runs=[
            RunRecord(
                run_no=1,
                claims=[
                    Claim(
                        claim_id="CLM-THOR-99",
                        agent="thor",
                        text="Unverified rumor claim.",
                        country="Midgard",
                        sector="maritime",
                        citations=["DOC-RUMOR"],
                    ),
                    Claim(
                        claim_id="CLM-LOKI-99",
                        agent="loki",
                        text="Conceded buffer claim.",
                        country="Tolan",
                        sector="wheat",
                        citations=["DOC-BUFFER"],
                    ),
                ],
                rulings=[
                    Ruling(
                        ruling_id="RUL-01",
                        claim_id="CLM-THOR-99",
                        outcome=RulingOutcome.REJECTED,
                        basis=RulingBasis.INFERENCE,
                        reasoning="Citation failed temporal cutoff.",
                        refs_checked=["DOC-RUMOR"],
                    ),
                    Ruling(
                        ruling_id="RUL-02",
                        claim_id="CLM-LOKI-99",
                        outcome=RulingOutcome.CONCEDED,
                        basis=RulingBasis.SOURCED_FACT,
                        reasoning="Formally conceded in cross-examination.",
                        refs_checked=["DOC-BUFFER"],
                    ),
                ],
            )
        ],
    )

    with patch("src.memory.manager.get_memory_manager", return_value=manager):
        distill_agent_memories_post_trial(case, run_no=1)

    # Thor should have a new lesson for the rejected claim
    thor_memories = manager.retrieve_relevant_memories(MemoryManager().store and None or MagicMock(agent_id="thor", event_id=None, country=None, sector=None, top_k=5))
    # Directly check store
    thor_records = mock_store.get_memories_for_agent("thor")
    assert len(thor_records) == 1
    assert "REJECTED by Odin" in thor_records[0].content
    assert "RUL-01" in thor_records[0].basis_refs

    # Loki should have a new lesson for the conceded claim
    loki_records = mock_store.get_memories_for_agent("loki")
    assert len(loki_records) == 1
    assert "Conceded on CLM-LOKI-99" in loki_records[0].content
    assert "RUL-02" in loki_records[0].basis_refs
