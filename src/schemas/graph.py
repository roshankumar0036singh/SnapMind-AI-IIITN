from enum import Enum
from typing import List, Dict, Any, Optional
from datetime import date
from pydantic import BaseModel, Field


class EntityType(str, Enum):
    NATION = "nation"
    COMMODITY = "commodity"
    CHOKEPOINT = "chokepoint"
    ORGANIZATION = "organization"
    AGREEMENT = "agreement"
    DISRUPTION_EVENT = "disruption_event"
    INFRASTRUCTURE = "infrastructure"
    ROUTE = "route"


class RelationType(str, Enum):
    EXPORTS_TO = "exports_to"
    IMPORTS_FROM = "imports_from"
    TRANSITS_THROUGH = "transits_through"
    SUBSTITUTES_WITH = "substitutes_with"
    BOTTLENECKED_AT = "bottlenecked_at"
    GOVERNED_BY = "governed_by"
    DISRUPTED_BY = "disrupted_by"
    HAS_STOCKPILE = "has_stockpile"
    PRODUCES = "produces"
    CONSUMES = "consumes"
    RETRACTS = "retracts"
    CORRECTS = "corrects"


class GraphNode(BaseModel):
    node_id: str = Field(..., description="Unique node ID, e.g. nation:midgard or chokepoint:orvan_grain_port")
    name: str = Field(..., description="Human-readable entity name, e.g. Midgard")
    entity_type: EntityType = Field(..., description="Entity taxonomy classification")
    country: Optional[str] = Field(None, description="Associated country name if applicable")
    sector: Optional[str] = Field(None, description="Associated sector/commodity if applicable")
    description: str = Field("", description="Entity profile and role summary")
    source_doc_id: Optional[str] = Field(None, description="Primary doc_id introducing entity")
    pub_date: date = Field(..., description="Earliest known date of entity recognition")
    reliability_tier: int = Field(1, description="Reliability tier (1-4) of introducing source")
    properties: Dict[str, Any] = Field(default_factory=dict, description="Arbitrary attributes (e.g. capacity_pct, coordinates)")


class GraphEdge(BaseModel):
    edge_id: str = Field(..., description="Unique edge identifier")
    source_id: str = Field(..., description="Source node_id")
    target_id: str = Field(..., description="Target node_id")
    relation_type: RelationType = Field(..., description="Typed relationship")
    weight: float = Field(1.0, description="Confidence or magnitude weight")
    description: str = Field("", description="Explanation of relationship")
    citation: str = Field(..., description="Strict grounding citation, e.g. ORV-0018#P3")
    pub_date: date = Field(..., description="Date document containing relationship was published")
    as_of_limit: date = Field(..., description="Temporal boundary for simulated clock")
    reliability_tier: int = Field(1, description="Source reliability tier (1-4)")
    is_retracted: bool = Field(False, description="Flag indicating if relationship is retracted")
    properties: Dict[str, Any] = Field(default_factory=dict, description="Quantitative values (e.g. drop_pct, volume)")


class GraphTriplet(BaseModel):
    source_name: str
    relation_type: str
    target_name: str
    citation: str
    description: str
    properties: Dict[str, Any] = Field(default_factory=dict)


class GraphPath(BaseModel):
    path_nodes: List[str] = Field(..., description="Ordered list of node names")
    path_edges: List[str] = Field(..., description="Ordered list of relation descriptions")
    citations: List[str] = Field(default_factory=list, description="Grounding citations across the path")
    is_bottleneck: bool = Field(False, description="True if path passes through a capacity bottleneck")
    is_substitution: bool = Field(False, description="True if path represents an alternative trade flow")
    summary: str = Field(..., description="Human-readable synthesis of causal link")


class SubgraphResult(BaseModel):
    nodes: List[GraphNode] = Field(default_factory=list)
    edges: List[GraphEdge] = Field(default_factory=list)
    triplets: List[GraphTriplet] = Field(default_factory=list)
    paths: List[GraphPath] = Field(default_factory=list)
    citations: List[str] = Field(default_factory=list)
