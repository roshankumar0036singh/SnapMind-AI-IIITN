import pytest

from src.retrieval.hyde import SelectiveHyDE, HyDEResult


def test_hyde_agent_angle_generation():
    engine = SelectiveHyDE()

    scope = {
        "event_id": "EVT-ORV-01",
        "countries": ["Midgard", "Tolan"],
        "sectors": ["wheat", "maize"],
    }

    # Thor perspective
    thor_text = engine.generate_hypothetical_document(
        query_text="grain export halt",
        agent_id="thor",
        scope=scope,
    )
    assert "critical bottlenecks" in thor_text
    assert "wheat, maize" in thor_text
    assert "Midgard, Tolan" in thor_text

    # Loki perspective
    loki_text = engine.generate_hypothetical_document(
        query_text="grain export halt",
        agent_id="loki",
        scope=scope,
    )
    assert "contingency inventory" in loki_text
    assert "alternative suppliers" in loki_text

    # Heimdall perspective
    heimdall_text = engine.generate_hypothetical_document(
        query_text="grain export halt",
        agent_id="heimdall",
        scope=scope,
    )
    assert "Formal notice" in heimdall_text
    assert "customs clearance" in heimdall_text


def test_hyde_embedding_generation():
    engine = SelectiveHyDE()

    result = engine.generate_hyde_embedding(
        query_text="grain corridor closure impact",
        agent_id="thor",
        scope={"countries": ["Midgard"], "sectors": ["wheat"]},
        trigger_reason="run_2_gap_filling",
    )

    assert isinstance(result, HyDEResult)
    assert result.is_hyde is True
    assert result.original_query == "grain corridor closure impact"
    assert len(result.embedding) == 768
    assert result.trigger_reason == "run_2_gap_filling"
