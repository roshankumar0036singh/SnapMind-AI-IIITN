import pytest
from datetime import date
from pathlib import Path

from src.schemas.graph import (
    EntityType,
    RelationType,
    GraphNode,
    GraphEdge,
    GraphTriplet,
    GraphPath,
    SubgraphResult,
)
from src.graph.store import KnowledgeGraphStore
from src.retrieval.graph_retriever import DualLevelGraphRetriever


@pytest.fixture
def sample_graph(tmp_path: Path) -> KnowledgeGraphStore:
    store = KnowledgeGraphStore(storage_path=tmp_path / "test_graph.json")

    # Add Nations & Ports
    store.add_node(
        GraphNode(
            node_id="nation:midgard",
            name="Midgard",
            entity_type=EntityType.NATION,
            country="Midgard",
            description="Consumer nation dependent on grain.",
            pub_date=date(2026, 1, 1),
            reliability_tier=1,
        )
    )
    store.add_node(
        GraphNode(
            node_id="nation:vanir",
            name="Vanir",
            entity_type=EntityType.NATION,
            country="Vanir",
            description="Exporter nation.",
            pub_date=date(2026, 1, 1),
            reliability_tier=1,
        )
    )
    store.add_node(
        GraphNode(
            node_id="chokepoint:orvan_grain_port",
            name="Orvan Grain Port",
            entity_type=EntityType.CHOKEPOINT,
            country="Orvan",
            description="Primary grain terminal.",
            pub_date=date(2026, 1, 1),
            reliability_tier=1,
        )
    )
    store.add_node(
        GraphNode(
            node_id="disruption:orvan_port_strike",
            name="Orvan Port Strike",
            entity_type=EntityType.DISRUPTION_EVENT,
            country="Orvan",
            description="Dock strike.",
            pub_date=date(2026, 9, 14),
            reliability_tier=1,
        )
    )

    # 1. Valid Disruption Edge
    store.add_edge(
        GraphEdge(
            edge_id="edge:strike_to_port",
            source_id="disruption:orvan_port_strike",
            target_id="chokepoint:orvan_grain_port",
            relation_type=RelationType.DISRUPTED_BY,
            citation="ORV-0005#P1",
            pub_date=date(2026, 9, 15),
            as_of_limit=date(2027, 1, 25),
            reliability_tier=1,
        )
    )

    # 2. Valid Port to Midgard Edge (Bottlenecked)
    store.add_edge(
        GraphEdge(
            edge_id="edge:port_to_midgard",
            source_id="chokepoint:orvan_grain_port",
            target_id="nation:midgard",
            relation_type=RelationType.BOTTLENECKED_AT,
            citation="ORV-0047#P2",
            pub_date=date(2026, 9, 20),
            as_of_limit=date(2027, 1, 25),
            reliability_tier=1,
            properties={"capacity_pct": 95},
        )
    )

    # 3. Retracted Edge (Deliberate Trap)
    store.add_edge(
        GraphEdge(
            edge_id="edge:fake_miracle_recovery",
            source_id="chokepoint:orvan_grain_port",
            target_id="nation:midgard",
            relation_type=RelationType.EXPORTS_TO,
            citation="ORV-0099#P1",
            pub_date=date(2026, 9, 25),
            as_of_limit=date(2027, 1, 25),
            reliability_tier=1,
            is_retracted=True,
        )
    )

    # 4. Post-Cutoff Edge (Future Leak - Temporal Violation)
    store.add_edge(
        GraphEdge(
            edge_id="edge:future_treaty_2028",
            source_id="nation:vanir",
            target_id="nation:midgard",
            relation_type=RelationType.EXPORTS_TO,
            citation="WLD-0050#P1",
            pub_date=date(2028, 5, 1),
            as_of_limit=date(2028, 5, 1),
            reliability_tier=1,
        )
    )

    return store


def test_graph_node_and_edge_schemas():
    node = GraphNode(
        node_id="nation:ravik",
        name="Ravik",
        entity_type=EntityType.NATION,
        country="Ravik",
        pub_date=date(2026, 1, 1),
    )
    assert node.node_id == "nation:ravik"
    assert node.entity_type == EntityType.NATION

    edge = GraphEdge(
        edge_id="edge:ravik_test",
        source_id="nation:ravik",
        target_id="nation:midgard",
        relation_type=RelationType.EXPORTS_TO,
        citation="ORV-0018#P1",
        pub_date=date(2026, 10, 1),
        as_of_limit=date(2027, 1, 25),
    )
    assert edge.source_id == "nation:ravik"
    assert edge.citation == "ORV-0018#P1"


def test_graph_temporal_clock_and_trap_exclusion(sample_graph: KnowledgeGraphStore):
    # Simulated clock cutoff: 2027-01-25
    clock_cutoff = date(2027, 1, 25)

    subgraph = sample_graph.get_subgraph(
        seed_node_ids=["chokepoint:orvan_grain_port"],
        max_depth=2,
        as_of_date=clock_cutoff,
    )

    edge_ids = [e.edge_id for e in subgraph.edges]

    # Valid edges must be present
    assert "edge:strike_to_port" in edge_ids
    assert "edge:port_to_midgard" in edge_ids

    # Retracted edge (trap) must be strictly excluded
    assert "edge:fake_miracle_recovery" not in edge_ids

    # Future edge (dated 2028-05-01) must be strictly excluded
    assert "edge:future_treaty_2028" not in edge_ids


def test_graph_multi_hop_pathfinding(sample_graph: KnowledgeGraphStore):
    paths = sample_graph.find_paths(
        source_id="disruption:orvan_port_strike",
        target_id="nation:midgard",
        max_depth=3,
        as_of_date=date(2027, 1, 25),
    )

    assert len(paths) >= 1
    p = paths[0]
    assert p.path_nodes == ["Orvan Port Strike", "Orvan Grain Port", "Midgard"]
    assert p.is_bottleneck is True
    assert "ORV-0005#P1" in p.citations
    assert "ORV-0047#P2" in p.citations


def test_dual_level_graph_retriever(sample_graph: KnowledgeGraphStore):
    retriever = DualLevelGraphRetriever(graph_store=sample_graph)

    # Format context for Thor
    thor_context = retriever.format_graph_context_for_agent(
        agent_role="thor",
        country="Midgard",
        as_of_date=date(2027, 1, 25),
    )

    assert "KNOWLEDGE GRAPH INTELLIGENCE" in thor_context
    assert "Orvan Grain Port" in thor_context
    assert "ORV-0047#P2" in thor_context
    assert "BOTTLENECK DETECTED" in thor_context


def test_graph_disk_serialization(sample_graph: KnowledgeGraphStore, tmp_path: Path):
    save_file = tmp_path / "serialized_graph.json"
    sample_graph.save_to_disk(save_file)
    assert save_file.exists()

    new_store = KnowledgeGraphStore(storage_path=save_file)
    assert len(new_store.nodes_data) == len(sample_graph.nodes_data)
    assert len(new_store.edges_data) == len(sample_graph.edges_data)
    assert new_store.get_node("nation:midgard") is not None


def test_heimdall_graph_role(sample_graph: KnowledgeGraphStore):
    retriever = DualLevelGraphRetriever(graph_store=sample_graph)
    heimdall_ctx = retriever.format_graph_context_for_agent(
        agent_role="heimdall",
        country="Midgard",
        as_of_date=date(2027, 1, 25),
    )
    assert "Gatekeeper Geopolitical Topology & Event Scope" in heimdall_ctx
    assert "Connected Sovereign Geographies" in heimdall_ctx


def test_bottleneck_vs_substitution_distinction(sample_graph: KnowledgeGraphStore):
    # Add a substitution edge with negative phrasing
    sample_graph.add_edge(
        GraphEdge(
            edge_id="edge:sub_negative_phrase",
            source_id="chokepoint:orvan_grain_port",
            target_id="nation:midgard",
            relation_type=RelationType.EXPORTS_TO,
            citation="ORV-0016#P3",
            pub_date=date(2026, 10, 1),
            as_of_limit=date(2027, 1, 25),
            description="Absence of alternative corridor leaves Tolan highly exposed.",
        )
    )

    # Bottleneck edge
    sample_graph.add_edge(
        GraphEdge(
            edge_id="edge:rail_limit",
            source_id="nation:vanir",
            target_id="nation:midgard",
            relation_type=RelationType.BOTTLENECKED_AT,
            citation="ORV-0018#P3",
            pub_date=date(2026, 10, 20),
            as_of_limit=date(2027, 1, 25),
            description="Capping maximum substitute grain transfer.",
            properties={"capacity_pct": 95},
        )
    )

    # Genuine substitution edge
    sample_graph.add_edge(
        GraphEdge(
            edge_id="edge:real_substitution",
            source_id="nation:vanir",
            target_id="nation:midgard",
            relation_type=RelationType.SUBSTITUTES_WITH,
            citation="ORV-0006#P1",
            pub_date=date(2026, 10, 20),
            as_of_limit=date(2027, 1, 25),
            description="Millers actively offset Orvan sea loading drops by booking alternative wheat supplies from Vanir.",
        )
    )

    bottlenecks = sample_graph.detect_bottlenecks(target_country="Midgard")
    substitutions = sample_graph.detect_substitutions(target_country="Midgard")

    b_ids = [b["edge_id"] for b in bottlenecks]
    s_ids = [s["edge_id"] for s in substitutions]

    # Bottleneck edge must be in bottlenecks, NOT in substitutions
    assert "edge:rail_limit" in b_ids
    assert "edge:rail_limit" not in s_ids

    # Negative phrasing edge must NOT be in substitutions
    assert "edge:sub_negative_phrase" not in s_ids

    # Real substitution must be in substitutions
    assert "edge:real_substitution" in s_ids

