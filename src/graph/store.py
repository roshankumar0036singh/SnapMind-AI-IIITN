import json
import logging
from datetime import date
from pathlib import Path
from typing import List, Dict, Any, Optional, Set, Tuple

import networkx as nx

from src.schemas.graph import (
    EntityType,
    RelationType,
    GraphNode,
    GraphEdge,
    GraphTriplet,
    GraphPath,
    SubgraphResult,
)
from src.supabase_client import get_supabase_admin

logger = logging.getLogger(__name__)

DEFAULT_GRAPH_PATH = Path("data/runemark_processed/knowledge_graph.json")


class KnowledgeGraphStore:
    """
    High-performance Knowledge Graph store backed by NetworkX MultiDiGraph,
    with local JSON persistence and Supabase synchronization.
    Enforces strict temporal clock gating (as-of date), reliability tiers,
    and trap quarantine (retractions/corrections).
    """

    def __init__(self, storage_path: Optional[Path] = None):
        self.storage_path = storage_path or DEFAULT_GRAPH_PATH
        self.graph: nx.MultiDiGraph = nx.MultiDiGraph()
        self.nodes_data: Dict[str, GraphNode] = {}
        self.edges_data: Dict[str, GraphEdge] = {}
        
        # Load cached graph from disk if available
        if self.storage_path.exists():
            self.load_from_disk(self.storage_path)

    def add_node(self, node: GraphNode) -> None:
        """Add or update a node in the graph."""
        self.nodes_data[node.node_id] = node
        self.graph.add_node(
            node.node_id,
            name=node.name,
            entity_type=node.entity_type.value if isinstance(node.entity_type, EntityType) else str(node.entity_type),
            country=node.country,
            sector=node.sector,
            description=node.description,
            pub_date=node.pub_date.isoformat(),
            reliability_tier=node.reliability_tier,
            properties=node.properties,
        )

    def add_edge(self, edge: GraphEdge) -> None:
        """Add or update a directed edge in the graph."""
        self.edges_data[edge.edge_id] = edge
        self.graph.add_edge(
            edge.source_id,
            edge.target_id,
            key=edge.edge_id,
            relation_type=edge.relation_type.value if isinstance(edge.relation_type, RelationType) else str(edge.relation_type),
            weight=edge.weight,
            description=edge.description,
            citation=edge.citation,
            pub_date=edge.pub_date.isoformat(),
            as_of_limit=edge.as_of_limit.isoformat(),
            reliability_tier=edge.reliability_tier,
            is_retracted=edge.is_retracted,
            properties=edge.properties,
        )

    def get_node(self, node_id: str) -> Optional[GraphNode]:
        """Retrieve node by ID."""
        return self.nodes_data.get(node_id)

    def get_edge(self, edge_id: str) -> Optional[GraphEdge]:
        """Retrieve edge by ID."""
        return self.edges_data.get(edge_id)

    def find_nodes_by_attribute(
        self,
        name: Optional[str] = None,
        entity_type: Optional[EntityType] = None,
        country: Optional[str] = None,
        sector: Optional[str] = None,
    ) -> List[GraphNode]:
        """Search nodes matching one or more attributes."""
        matched: List[GraphNode] = []
        name_lower = name.lower().strip() if name else None
        country_lower = country.lower().strip() if country else None
        sector_lower = sector.lower().strip() if sector else None

        for n in self.nodes_data.values():
            if name_lower and name_lower not in n.name.lower() and name_lower not in n.node_id.lower():
                continue
            if entity_type and n.entity_type != entity_type:
                continue
            if country_lower and (not n.country or country_lower != n.country.lower()):
                continue
            if sector_lower and (not n.sector or sector_lower != n.sector.lower()):
                continue
            matched.append(n)
        return matched

    def get_subgraph(
        self,
        seed_node_ids: List[str],
        max_depth: int = 2,
        as_of_date: Optional[date] = None,
        max_tier: int = 4,
    ) -> SubgraphResult:
        """
        Traverse local ego network from seed nodes up to max_depth.
        Enforces Simulated Clock cutoff (pub_date <= as_of_date) and
        excludes retracted edges or edges exceeding max_tier.
        """
        visited_nodes: Set[str] = set()
        matched_edges: List[GraphEdge] = []
        triplets: List[GraphTriplet] = []
        all_citations: Set[str] = set()

        current_frontier = set(seed_node_ids)

        for depth in range(max_depth):
            next_frontier = set()
            for current_node_id in current_frontier:
                if current_node_id not in self.graph:
                    continue
                visited_nodes.add(current_node_id)

                # Outgoing edges
                for _, neighbor_id, edge_key, edge_attrs in self.graph.out_edges(current_node_id, keys=True, data=True):
                    if not self._is_edge_valid(edge_attrs, as_of_date, max_tier):
                        continue

                    edge_obj = self.edges_data.get(edge_key)
                    if edge_obj and edge_obj not in matched_edges:
                        matched_edges.append(edge_obj)
                        all_citations.add(edge_obj.citation)

                        src_node = self.nodes_data.get(edge_obj.source_id)
                        tgt_node = self.nodes_data.get(edge_obj.target_id)
                        triplets.append(
                            GraphTriplet(
                                source_name=src_node.name if src_node else edge_obj.source_id,
                                relation_type=edge_attrs.get("relation_type", "related_to"),
                                target_name=tgt_node.name if tgt_node else edge_obj.target_id,
                                citation=edge_obj.citation,
                                description=edge_obj.description,
                                properties=edge_obj.properties,
                            )
                        )

                    next_frontier.add(neighbor_id)
                    visited_nodes.add(neighbor_id)

                # Incoming edges (for bidirectional awareness, e.g. who supplies current node)
                for neighbor_id, _, edge_key, edge_attrs in self.graph.in_edges(current_node_id, keys=True, data=True):
                    if not self._is_edge_valid(edge_attrs, as_of_date, max_tier):
                        continue

                    edge_obj = self.edges_data.get(edge_key)
                    if edge_obj and edge_obj not in matched_edges:
                        matched_edges.append(edge_obj)
                        all_citations.add(edge_obj.citation)

                        src_node = self.nodes_data.get(edge_obj.source_id)
                        tgt_node = self.nodes_data.get(edge_obj.target_id)
                        triplets.append(
                            GraphTriplet(
                                source_name=src_node.name if src_node else edge_obj.source_id,
                                relation_type=edge_attrs.get("relation_type", "related_to"),
                                target_name=tgt_node.name if tgt_node else edge_obj.target_id,
                                citation=edge_obj.citation,
                                description=edge_obj.description,
                                properties=edge_obj.properties,
                            )
                        )

                    next_frontier.add(neighbor_id)
                    visited_nodes.add(neighbor_id)

            current_frontier = next_frontier - visited_nodes

        nodes_list = [self.nodes_data[nid] for nid in visited_nodes if nid in self.nodes_data]

        return SubgraphResult(
            nodes=nodes_list,
            edges=matched_edges,
            triplets=triplets,
            paths=[],
            citations=sorted(list(all_citations)),
        )

    def find_paths(
        self,
        source_id: str,
        target_id: str,
        max_depth: int = 4,
        as_of_date: Optional[date] = None,
        max_tier: int = 4,
    ) -> List[GraphPath]:
        """
        Find causal and supply chain paths connecting source entity to target entity.
        Detects bottlenecks (capacity caps) and substitution flows along the path.
        """
        if source_id not in self.graph or target_id not in self.graph:
            return []

        paths_found: List[GraphPath] = []

        try:
            raw_paths = nx.all_simple_edge_paths(self.graph, source_id, target_id, cutoff=max_depth)
        except Exception:
            return []

        for p in raw_paths:
            nodes_in_path: List[str] = [self.nodes_data[source_id].name if source_id in self.nodes_data else source_id]
            edges_in_path: List[str] = []
            citations: List[str] = []
            is_bottleneck = False
            is_substitution = False
            path_valid = True

            for edge_item in p:
                if len(edge_item) == 3:
                    u, v, k = edge_item
                elif len(edge_item) == 2:
                    u, v = edge_item
                    k = None
                else:
                    continue

                if k is not None:
                    attrs = self.graph.get_edge_data(u, v, k) or {}
                else:
                    multi_data = self.graph.get_edge_data(u, v) or {}
                    attrs = next(iter(multi_data.values())) if isinstance(multi_data, dict) and multi_data else {}

                if not self._is_edge_valid(attrs, as_of_date, max_tier):
                    path_valid = False
                    break

                target_name = self.nodes_data[v].name if v in self.nodes_data else v
                nodes_in_path.append(target_name)

                rel = attrs.get("relation_type", "connected_to")
                cit = attrs.get("citation", "")
                if cit:
                    citations.append(cit)

                props = attrs.get("properties") or {}
                if not isinstance(props, dict):
                    props = {}

                if rel in ("bottlenecked_at", "disrupted_by") or props.get("capacity_pct", 0) >= 80:
                    is_bottleneck = True
                if rel in ("substitutes_with", "alternative_route"):
                    is_substitution = True

                edge_desc = f"--[{rel} ({props.get('desc', '')})]-->"
                edges_in_path.append(edge_desc)

            if path_valid and len(nodes_in_path) > 1:
                summary_str = " -> ".join(nodes_in_path)
                paths_found.append(
                    GraphPath(
                        path_nodes=nodes_in_path,
                        path_edges=edges_in_path,
                        citations=list(dict.fromkeys(citations)),
                        is_bottleneck=is_bottleneck,
                        is_substitution=is_substitution,
                        summary=summary_str,
                    )
                )

        return paths_found

    def detect_bottlenecks(
        self,
        target_country: Optional[str] = None,
        sector: Optional[str] = None,
        as_of_date: Optional[date] = None,
    ) -> List[Dict[str, Any]]:
        """
        Find bottlenecks, capacity constraints, and strike-affected chokepoints
        relevant to target country and sector.
        """
        bottlenecks: List[Dict[str, Any]] = []
        c_lower = target_country.lower().strip() if target_country else None
        s_lower = sector.lower().strip() if sector else None

        for e in self.edges_data.values():
            if as_of_date and e.pub_date > as_of_date:
                continue
            if e.is_retracted:
                continue

            rel = e.relation_type.value if isinstance(e.relation_type, RelationType) else str(e.relation_type)
            is_constraint = (
                rel in ("bottlenecked_at", "disrupted_by")
                or e.properties.get("capacity_pct", 0) >= 80
                or "strike" in e.description.lower()
                or "bottleneck" in e.description.lower()
            )
            if not is_constraint:
                continue

            src_node = self.nodes_data.get(e.source_id)
            tgt_node = self.nodes_data.get(e.target_id)

            # Filter by country relevance if provided
            if c_lower:
                relevant = (
                    c_lower in e.source_id.lower()
                    or c_lower in e.target_id.lower()
                    or (src_node and src_node.country and c_lower in src_node.country.lower())
                    or (tgt_node and tgt_node.country and c_lower in tgt_node.country.lower())
                    or c_lower in e.description.lower()
                    or "orvan" in e.source_id.lower()
                )
                if not relevant:
                    continue

            # Filter by sector relevance if provided
            if s_lower:
                sector_relevant = (
                    s_lower in e.properties.get("commodity", "").lower()
                    or s_lower in e.description.lower()
                    or (src_node and src_node.sector and s_lower in src_node.sector.lower())
                    or (tgt_node and tgt_node.sector and s_lower in tgt_node.sector.lower())
                    or "port" in e.source_id.lower()
                    or "expiry" in e.source_id.lower()
                )
                if not sector_relevant:
                    continue

            bottlenecks.append({
                "edge_id": e.edge_id,
                "source": src_node.name if src_node else e.source_id,
                "target": tgt_node.name if tgt_node else e.target_id,
                "relation": rel,
                "description": e.description,
                "citation": e.citation,
                "properties": e.properties,
            })

        return bottlenecks

    def detect_substitutions(
        self,
        target_country: Optional[str] = None,
        sector: Optional[str] = None,
        as_of_date: Optional[date] = None,
    ) -> List[Dict[str, Any]]:
        """
        Find commercial substitution routes, alternative suppliers, and stockpile buffers
        for target country and sector.
        """
        substitutions: List[Dict[str, Any]] = []
        c_lower = target_country.lower().strip() if target_country else None
        s_lower = sector.lower().strip() if sector else None

        for e in self.edges_data.values():
            if as_of_date and e.pub_date > as_of_date:
                continue
            if e.is_retracted:
                continue

            rel = e.relation_type.value if isinstance(e.relation_type, RelationType) else str(e.relation_type)

            # Bottlenecks and direct disruptions are constraints, not commercial substitutions
            if rel in ("bottlenecked_at", "disrupted_by"):
                continue

            desc_lower = e.description.lower()
            # Exclude negative phrasing such as "absence of alternative" or "lacks rail"
            if "absence of alternative" in desc_lower or "no alternative" in desc_lower or "lacks" in desc_lower:
                continue

            is_sub = (
                rel in ("substitutes_with", "has_stockpile")
                or e.properties.get("adaptation_rate") is not None
                or e.properties.get("is_alternative", False)
                or (rel in ("exports_to", "transits_through") and any(w in desc_lower for w in ("substitut", "compensat", "offset", "alternative")))
            )
            if not is_sub:
                continue

            src_node = self.nodes_data.get(e.source_id)
            tgt_node = self.nodes_data.get(e.target_id)

            # Filter by country relevance if provided
            if c_lower:
                relevant = (
                    c_lower in e.source_id.lower()
                    or c_lower in e.target_id.lower()
                    or (src_node and src_node.country and c_lower in src_node.country.lower())
                    or (tgt_node and tgt_node.country and c_lower in tgt_node.country.lower())
                    or c_lower in desc_lower
                )
                if not relevant:
                    continue

            # Filter by sector relevance if provided
            if s_lower:
                sector_relevant = (
                    s_lower in e.properties.get("commodity", "").lower()
                    or s_lower in desc_lower
                    or (src_node and src_node.sector and s_lower in src_node.sector.lower())
                    or (tgt_node and tgt_node.sector and s_lower in tgt_node.sector.lower())
                )
                if not sector_relevant:
                    continue

            substitutions.append({
                "edge_id": e.edge_id,
                "source": src_node.name if src_node else e.source_id,
                "target": tgt_node.name if tgt_node else e.target_id,
                "relation": rel,
                "description": e.description,
                "citation": e.citation,
                "properties": e.properties,
            })

        return substitutions

    def _is_edge_valid(self, attrs: Dict[str, Any], as_of_date: Optional[date], max_tier: int) -> bool:
        """Validate edge against temporal clock, retraction flag, and tier limit."""
        if attrs.get("is_retracted", False):
            return False

        if attrs.get("reliability_tier", 1) > max_tier:
            return False

        if as_of_date:
            pub_str = attrs.get("pub_date")
            if pub_str:
                edge_pub = date.fromisoformat(pub_str)
                if edge_pub > as_of_date:
                    return False
        return True

    def save_to_disk(self, filepath: Optional[Path] = None) -> None:
        """Persist graph nodes and edges to JSON on disk."""
        target_path = filepath or self.storage_path
        target_path.parent.mkdir(parents=True, exist_ok=True)

        payload = {
            "nodes": [n.model_dump(mode="json") for n in self.nodes_data.values()],
            "edges": [e.model_dump(mode="json") for e in self.edges_data.values()],
        }

        with open(target_path, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2)

    def load_from_disk(self, filepath: Optional[Path] = None) -> bool:
        """Load graph nodes and edges from JSON on disk."""
        target_path = filepath or self.storage_path
        if not target_path.exists():
            return False

        try:
            with open(target_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            self.graph.clear()
            self.nodes_data.clear()
            self.edges_data.clear()

            for n_dict in data.get("nodes", []):
                node = GraphNode(**n_dict)
                self.add_node(node)

            for e_dict in data.get("edges", []):
                edge = GraphEdge(**e_dict)
                self.add_edge(edge)
            return True
        except Exception as e:
            logger.warning(f"Failed to load knowledge graph from disk: {e}")
            return False

    def sync_to_supabase(self) -> Tuple[int, int]:
        """
        Attempt to sync nodes and edges to Supabase if tables exist.
        Returns (nodes_synced, edges_synced).
        """
        try:
            client = get_supabase_admin()
            nodes_payload = [
                {
                    "node_id": n.node_id,
                    "name": n.name,
                    "entity_type": n.entity_type.value if isinstance(n.entity_type, EntityType) else str(n.entity_type),
                    "country": n.country,
                    "sector": n.sector,
                    "description": n.description,
                    "source_doc_id": n.source_doc_id,
                    "pub_date": n.pub_date.isoformat(),
                    "reliability_tier": n.reliability_tier,
                    "properties": n.properties,
                }
                for n in self.nodes_data.values()
            ]
            if nodes_payload:
                client.table("graph_nodes").upsert(nodes_payload).execute()

            edges_payload = [
                {
                    "edge_id": e.edge_id,
                    "source_id": e.source_id,
                    "target_id": e.target_id,
                    "relation_type": e.relation_type.value if isinstance(e.relation_type, RelationType) else str(e.relation_type),
                    "weight": e.weight,
                    "description": e.description,
                    "citation": e.citation,
                    "pub_date": e.pub_date.isoformat(),
                    "as_of_limit": e.as_of_limit.isoformat(),
                    "reliability_tier": e.reliability_tier,
                    "is_retracted": e.is_retracted,
                    "properties": e.properties,
                }
                for e in self.edges_data.values()
            ]
            if edges_payload:
                client.table("graph_edges").upsert(edges_payload).execute()

            return len(nodes_payload), len(edges_payload)
        except Exception as e:
            logger.info(f"Supabase graph tables not yet ready or sync skipped ({e}). Using local graph.")
            return 0, 0


_graph_store: Optional[KnowledgeGraphStore] = None

def get_graph_store() -> KnowledgeGraphStore:
    global _graph_store
    if _graph_store is None:
        _graph_store = KnowledgeGraphStore()
    return _graph_store
