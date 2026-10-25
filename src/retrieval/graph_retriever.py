import logging
from datetime import date
from typing import List, Dict, Any, Optional

from src.schemas.graph import (
    GraphNode,
    GraphEdge,
    GraphTriplet,
    GraphPath,
    SubgraphResult,
)
from src.graph.store import KnowledgeGraphStore, get_graph_store

logger = logging.getLogger(__name__)


class DualLevelGraphRetriever:
    """
    Dual-Level Graph Retriever implementing local entity subgraph traversal
    and multi-hop supply-chain causal pathfinding.
    Enforces the Simulated Clock (as-of date) and citation grounding.
    """

    def __init__(self, graph_store: Optional[KnowledgeGraphStore] = None):
        self.store = graph_store or get_graph_store()

    def retrieve_local_subgraph(
        self,
        country: str,
        sector: Optional[str] = None,
        as_of_date: Optional[date] = None,
        max_depth: int = 2,
        max_tier: int = 4,
    ) -> SubgraphResult:
        """
        Low-Level Retrieval: Extracts the 2-hop local ego network around a country and/or sector.
        """
        seed_nodes: List[str] = []
        c_lower = country.lower().strip()
        
        # Match seed nodes
        for node_id, node in self.store.nodes_data.items():
            if node.name.lower() == c_lower or (node.country and node.country.lower() == c_lower):
                seed_nodes.append(node_id)
            elif sector and node.sector and node.sector.lower() == sector.lower():
                seed_nodes.append(node_id)

        if not seed_nodes:
            # Fallback: search by ID substring
            seed_nodes = [nid for nid in self.store.nodes_data if c_lower in nid]

        if not seed_nodes:
            return SubgraphResult()

        return self.store.get_subgraph(
            seed_node_ids=seed_nodes,
            max_depth=max_depth,
            as_of_date=as_of_date,
            max_tier=max_tier,
        )

    def retrieve_causal_paths(
        self,
        target_country: str,
        source_event: Optional[str] = None,
        as_of_date: Optional[date] = None,
        max_depth: int = 4,
    ) -> List[GraphPath]:
        """
        High-Level Retrieval: Finds directed supply-chain and disruption paths
        connecting the disruption event to the target country.
        """
        c_lower = target_country.lower().strip()
        target_node_id = f"nation:{c_lower}"
        if target_node_id not in self.store.nodes_data:
            # Try to find by name
            for nid, n in self.store.nodes_data.items():
                if n.name.lower() == c_lower:
                    target_node_id = nid
                    break

        # Identify source event nodes
        source_node_ids: List[str] = []
        if source_event:
            s_lower = source_event.lower()
            for nid, n in self.store.nodes_data.items():
                if s_lower in n.name.lower() or s_lower in nid.lower():
                    source_node_ids.append(nid)

        if not source_node_ids:
            # Default to all disruption event nodes in the graph
            source_node_ids = [
                nid for nid, n in self.store.nodes_data.items()
                if "disruption" in nid or "strike" in nid or "expiry" in nid
            ]

        all_paths: List[GraphPath] = []
        for src_id in source_node_ids:
            paths = self.store.find_paths(
                source_id=src_id,
                target_id=target_node_id,
                max_depth=max_depth,
                as_of_date=as_of_date,
            )
            all_paths.extend(paths)

        return all_paths

    def format_graph_context_for_agent(
        self,
        agent_role: str,
        country: str,
        sector: Optional[str] = None,
        as_of_date: Optional[date] = None,
        event_id: Optional[str] = None,
    ) -> str:
        """
        Synthesizes formatted Knowledge Graph intelligence tailored for
        the specified agent (Thor, Loki, Heimdall, Odin).
        """
        subgraph = self.retrieve_local_subgraph(
            country=country,
            sector=sector,
            as_of_date=as_of_date,
            max_depth=2,
        )

        paths = self.retrieve_causal_paths(
            target_country=country,
            as_of_date=as_of_date,
        )

        bottlenecks = self.store.detect_bottlenecks(
            target_country=country,
            sector=sector,
            as_of_date=as_of_date,
        )

        substitutions = self.store.detect_substitutions(
            target_country=country,
            sector=sector,
            as_of_date=as_of_date,
        )

        lines: List[str] = []
        lines.append(f"### KNOWLEDGE GRAPH INTELLIGENCE ({country.upper()} / {str(sector).upper()})")
        lines.append(f"*Simulated Clock Cutoff: {as_of_date.isoformat() if as_of_date else 'None'}*")
        lines.append("")

        # 1. Supply Chain & Causal Paths
        if paths:
            lines.append("#### Multi-Hop Supply Chain Paths:")
            for p in paths:
                tag = " [BOTTLENECK DETECTED]" if p.is_bottleneck else ""
                tag += " [SUBSTITUTION DETECTED]" if p.is_substitution else ""
                cit_str = f" (Citations: {', '.join(p.citations)})" if p.citations else ""
                lines.append(f"- **Path{tag}:** {p.summary}{cit_str}")
            lines.append("")

        # 2. Agent-Specific Focus Areas
        role_lower = agent_role.lower()

        if role_lower in ("heimdall", "all"):
            from src.schemas.graph import EntityType
            lines.append("#### Gatekeeper Geopolitical Topology & Event Scope (Heimdall Scope):")
            connected_countries = sorted(list({n.country for n in subgraph.nodes if n.country}))
            connected_sectors = sorted(list({n.sector for n in subgraph.nodes if n.sector}))
            if connected_countries:
                lines.append(f"- **Connected Sovereign Geographies:** {', '.join(connected_countries)}")
            if connected_sectors:
                lines.append(f"- **Impacted Trade Sectors:** {', '.join(connected_sectors)}")
            authorities = [n for n in subgraph.nodes if n.entity_type in (EntityType.AGREEMENT, EntityType.DISRUPTION_EVENT, EntityType.CHOKEPOINT)]
            for a in authorities:
                lines.append(f"- **{a.name} ({a.entity_type.value.upper()})**: {a.description} [Source: {a.source_doc_id or 'Graph'}]")
            lines.append("")

        if role_lower in ("thor", "all", "odin"):
            if bottlenecks:
                lines.append("#### Verified Transit Bottlenecks & Capacity Caps (Thor Ammunition):")
                for b in bottlenecks:
                    lines.append(
                        f"- **{b['source']} --[{b['relation'].upper()}]--> {b['target']}**: "
                        f"{b['description']} [{b['citation']}]"
                    )
                lines.append("")

        if role_lower in ("loki", "all", "odin"):
            if substitutions:
                lines.append("#### Commercial Substitutions & Logistics Adaptation (Loki Ammunition):")
                for s in substitutions:
                    lines.append(
                        f"- **{s['source']} --[{s['relation'].upper()}]--> {s['target']}**: "
                        f"{s['description']} [{s['citation']}]"
                    )
                lines.append("")

        # 3. Direct Subgraph Relationships
        if subgraph.triplets:
            lines.append("#### Local Subgraph Facts (Triplets):")
            for t in subgraph.triplets[:8]:
                lines.append(f"- {t.source_name} --[{t.relation_type}]--> {t.target_name} [{t.citation}]: {t.description}")
            lines.append("")

        return "\n".join(lines)


_graph_retriever: Optional[DualLevelGraphRetriever] = None

def get_graph_retriever() -> DualLevelGraphRetriever:
    global _graph_retriever
    if _graph_retriever is None:
        _graph_retriever = DualLevelGraphRetriever()
    return _graph_retriever
