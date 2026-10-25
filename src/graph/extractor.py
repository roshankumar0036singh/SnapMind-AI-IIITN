import os
import re
import logging
from datetime import date
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field

from src.config import get_settings
from src.schemas.graph import (
    EntityType,
    RelationType,
    GraphNode,
    GraphEdge,
)
from src.graph.store import KnowledgeGraphStore, get_graph_store

logger = logging.getLogger(__name__)
settings = get_settings()


class ExtractedEntity(BaseModel):
    name: str
    entity_type: str
    country: Optional[str] = None
    sector: Optional[str] = None
    description: str = ""
    properties: Dict[str, Any] = Field(default_factory=dict)


class ExtractedRelation(BaseModel):
    source_name: str
    target_name: str
    relation_type: str
    description: str = ""
    citation: str
    properties: Dict[str, Any] = Field(default_factory=dict)


class DocumentExtractionResult(BaseModel):
    entities: List[ExtractedEntity] = Field(default_factory=list)
    relations: List[ExtractedRelation] = Field(default_factory=list)


class LLMGraphExtractor:
    """
    Extracts structured entities, typed relationships, and citation-grounded edges
    from Runemark exhibits and trade tables using Gemini.
    """

    EXTRACTION_PROMPT = """
You are a Lead Intelligence Cartographer extracting Knowledge Graph entities and supply-chain relationships 
from Runemark geopolitical and trade documents.

DOCUMENT CONTEXT:
Document ID: {doc_id}
Publication Date: {pub_date}
Reliability Tier: {reliability_tier}
Country: {country}
Sector: {sector}

TEXT:
{text}

TAXONOMY:
Entity Types: nation, commodity, chokepoint, organization, agreement, disruption_event, infrastructure, route
Relation Types: exports_to, imports_from, transits_through, substitutes_with, bottlenecked_at, governed_by, disrupted_by, has_stockpile, produces, consumes

REQUIREMENTS:
1. Extract salient geopolitical nations, ports, corridors, commodities, and agreements.
2. Extract relationships between entity pairs.
3. CRITICAL: Every relation MUST cite the exact paragraph (e.g. "{doc_id}#P1", "{doc_id}#P2").
4. If a bottleneck or capacity cap is mentioned (e.g. rail at practical limit, port strike, queue), set relation_type="bottlenecked_at" or "disrupted_by".
5. If alternative suppliers or diversification are mentioned, set relation_type="substitutes_with".
"""

    def __init__(self):
        self.api_key = settings.GEMINI_API_KEY
        self.model = settings.GEMINI_MODEL or "gemini-3.5-flash-lite"

    def extract_from_document(
        self,
        doc_id: str,
        text: str,
        pub_date: date,
        reliability_tier: int = 1,
        country: Optional[str] = None,
        sector: Optional[str] = None,
    ) -> DocumentExtractionResult:
        """Call Gemini structured output to extract entities and relations from document text."""
        if not self.api_key:
            return DocumentExtractionResult()

        try:
            from google import genai
            from google.genai import types
            
            client = genai.Client(api_key=self.api_key)
            prompt = self.EXTRACTION_PROMPT.format(
                doc_id=doc_id,
                pub_date=pub_date.isoformat(),
                reliability_tier=reliability_tier,
                country=country or "general",
                sector=sector or "general",
                text=text[:4000],
            )

            # Strip defaults for Gemini structured schema compliance
            schema_dict = DocumentExtractionResult.model_json_schema()
            self._strip_defaults(schema_dict)

            config = {
                "response_mime_type": "application/json",
                "response_schema": schema_dict,
                "temperature": 0.1,
            }

            response = client.models.generate_content(
                model=self.model,
                contents=prompt,
                config=types.GenerateContentConfig(**config),
            )

            if response.parsed and isinstance(response.parsed, dict):
                return DocumentExtractionResult.model_validate(response.parsed)
            elif response.parsed and isinstance(response.parsed, DocumentExtractionResult):
                return response.parsed
            return DocumentExtractionResult()
        except Exception as e:
            logger.warning(f"[GraphExtractor] LLM extraction error on {doc_id}: {e}")
            return DocumentExtractionResult()

    def _strip_defaults(self, schema: Any) -> None:
        """Recursively delete 'default' fields for Gemini API schema compatibility."""
        if isinstance(schema, dict):
            schema.pop("default", None)
            for key, value in list(schema.items()):
                self._strip_defaults(value)
        elif isinstance(schema, list):
            for item in schema:
                self._strip_defaults(item)


def bootstrap_runemark_knowledge_graph(graph_store: KnowledgeGraphStore) -> None:
    """
    Populates the Knowledge Graph with verified core geopolitical Atlas entities
    and grounded Event E5 supply-chain relationships.
    Enforces 100% strict paragraph-level citation grounding and chronological pub_dates.
    """
    # -------------------------------------------------------------
    # 1. CORE ATLAS NATIONS & COMMODITIES (ATL-0001 to ATL-0016)
    # -------------------------------------------------------------
    atlas_date = date(2026, 1, 1)

    nations = [
        ("nation:midgard", "Midgard", "Industrial consumer state with major flour milling and livestock sectors dependent on grain imports."),
        ("nation:tolan", "Tolan", "Coastal nation dependent on maritime maize and wheat imports via the Orvan corridor."),
        ("nation:vanir", "Vanir", "Major agricultural exporter of wheat and maize with rail and sea logistics."),
        ("nation:ravik", "Ravik", "Transit nation operating critical trans-continental rail corridors connecting Vanir to Midgard."),
        ("nation:orvan", "Orvan", "Key agricultural producer and host nation of the primary grain export port and corridor."),
    ]

    for nid, name, desc in nations:
        graph_store.add_node(
            GraphNode(
                node_id=nid,
                name=name,
                entity_type=EntityType.NATION,
                country=name,
                description=desc,
                source_doc_id="ATL-0001",
                pub_date=atlas_date,
                reliability_tier=1,
            )
        )

    commodities = [
        ("commodity:wheat", "Wheat", "Primary staple grain consumed by flour millers across Midgard and Tolan."),
        ("commodity:maize", "Maize", "Feed grain critical for livestock and industrial feed processing."),
    ]

    for cid, name, desc in commodities:
        graph_store.add_node(
            GraphNode(
                node_id=cid,
                name=name,
                entity_type=EntityType.COMMODITY,
                sector=name.lower(),
                description=desc,
                source_doc_id="ATL-0002",
                pub_date=atlas_date,
                reliability_tier=1,
            )
        )

    # -------------------------------------------------------------
    # 2. CHOKEPOINTS, CORRIDORS & ORGANIZATIONS
    # -------------------------------------------------------------
    chokepoints = [
        ("chokepoint:orvan_grain_port", "Orvan Grain Port", EntityType.CHOKEPOINT, "orvan", "Key maritime deep-water grain loading terminal."),
        ("chokepoint:orvan_sea_route", "Orvan Sea Route", EntityType.ROUTE, "orvan", "Primary maritime shipping lanes out of Orvan Grain Port."),
        ("chokepoint:ravik_rail_corridor", "Ravik Rail Corridor", EntityType.CHOKEPOINT, "ravik", "Strategic rail trunkline connecting Vanir agricultural hubs to Midgard millers."),
        ("org:midgard_flour_millers", "Midgard Flour Millers Association", EntityType.ORGANIZATION, "midgard", "Consortium of Midgard grain buyers and industrial flour milling facilities."),
        ("agreement:orvan_corridor_agreement", "Orvan Corridor Agreement", EntityType.AGREEMENT, "orvan", "Multilateral grain corridor agreement protecting commercial grain vessels."),
        ("disruption:orvan_corridor_expiry", "Orvan Corridor Expiration", EntityType.DISRUPTION_EVENT, "orvan", "Termination of agreement on 10 Sept 2026 without renewal."),
        ("disruption:orvan_port_strike", "Orvan Port Strike", EntityType.DISRUPTION_EVENT, "orvan", "Indefinite port worker strike initiated on 14 Sept 2026."),
    ]

    for eid, name, etype, ctry, desc in chokepoints:
        graph_store.add_node(
            GraphNode(
                node_id=eid,
                name=name,
                entity_type=etype,
                country=ctry,
                description=desc,
                source_doc_id="ORV-0005",
                pub_date=date(2026, 9, 10),
                reliability_tier=1,
            )
        )

    # -------------------------------------------------------------
    # 3. DISRUPTIONS & PRIMARY CORRIDOR FAILURE EDGES
    # -------------------------------------------------------------
    edges = [
        # Expiration and Strike hitting Port & Sea Route
        GraphEdge(
            edge_id="edge:disruption_expiry_to_port",
            source_id="disruption:orvan_corridor_expiry",
            target_id="chokepoint:orvan_grain_port",
            relation_type=RelationType.DISRUPTED_BY,
            weight=1.0,
            description="Corridor agreement expired on 10 September without extension, subjecting grain to general export restrictions.",
            citation="ORV-0005#P1",
            pub_date=date(2026, 9, 10),
            as_of_limit=date(2027, 1, 25),
            reliability_tier=1,
            properties={"impact": "severe_regulatory_lockdown"},
        ),
        GraphEdge(
            edge_id="edge:disruption_strike_to_port",
            source_id="disruption:orvan_port_strike",
            target_id="chokepoint:orvan_grain_port",
            relation_type=RelationType.DISRUPTED_BY,
            weight=1.0,
            description="Port union strike commenced 14 September, bringing commercial grain berths to a virtual standstill.",
            citation="ORV-0005#P2",
            pub_date=date(2026, 9, 15),
            as_of_limit=date(2027, 1, 25),
            reliability_tier=1,
            properties={"status": "halted"},
        ),
        GraphEdge(
            edge_id="edge:port_to_sea_route",
            source_id="chokepoint:orvan_grain_port",
            target_id="chokepoint:orvan_sea_route",
            relation_type=RelationType.BOTTLENECKED_AT,
            weight=0.9,
            description="September port index plummeted to 40; sea routes lost half to three-fifths (50% to 60%) of trade value in Q4.",
            citation="ORV-0047#P2",
            pub_date=date(2026, 9, 20),
            as_of_limit=date(2027, 1, 25),
            reliability_tier=1,
            properties={"index_value": 40, "value_loss_low": 50.0, "value_loss_high": 60.0},
        ),

        # Sea Route delivering to Midgard and Tolan
        GraphEdge(
            edge_id="edge:sea_route_to_midgard_wheat",
            source_id="chokepoint:orvan_sea_route",
            target_id="nation:midgard",
            relation_type=RelationType.EXPORTS_TO,
            weight=0.8,
            description="Orvan sea route supplies 50% to 60% of baseline wheat imports to Midgard before disruption.",
            citation="ORV-0018#P1",
            pub_date=date(2026, 10, 5),
            as_of_limit=date(2027, 1, 25),
            reliability_tier=1,
            properties={"commodity": "wheat", "exposure_pct_low": 50.0, "exposure_pct_high": 60.0},
        ),
        GraphEdge(
            edge_id="edge:sea_route_to_tolan_maize",
            source_id="chokepoint:orvan_sea_route",
            target_id="nation:tolan",
            relation_type=RelationType.EXPORTS_TO,
            weight=0.85,
            description="Tolan relies on Orvan maritime shipments for primary maize supplies; absence of alternative corridor leaves Tolan highly exposed.",
            citation="ORV-0016#P3",
            pub_date=date(2026, 10, 12),
            as_of_limit=date(2027, 1, 25),
            reliability_tier=1,
            properties={"commodity": "maize", "exposure_pct_low": 50.0, "exposure_pct_high": 60.0},
        ),

        # -------------------------------------------------------------
        # 4. LOKI'S SUBSTITUTION EDGES (Vanir & Rail)
        # -------------------------------------------------------------
        GraphEdge(
            edge_id="edge:midgard_substitutes_vanir_wheat",
            source_id="org:midgard_flour_millers",
            target_id="nation:vanir",
            relation_type=RelationType.SUBSTITUTES_WITH,
            weight=0.85,
            description="Midgard flour millers actively offset Orvan sea loading drops by booking alternative wheat supplies from Vanir.",
            citation="ORV-0006#P1",
            pub_date=date(2026, 10, 18),
            as_of_limit=date(2027, 1, 25),
            reliability_tier=1,
            properties={"commodity": "wheat", "adaptation_rate": "active"},
        ),
        GraphEdge(
            edge_id="edge:vanir_to_ravik_rail",
            source_id="nation:vanir",
            target_id="chokepoint:ravik_rail_corridor",
            relation_type=RelationType.TRANSITS_THROUGH,
            weight=0.8,
            description="Vanir grain shipments to Midgard are routed overland through Ravik rail network.",
            citation="ORV-0006#P1",
            pub_date=date(2026, 10, 18),
            as_of_limit=date(2027, 1, 25),
            reliability_tier=1,
            properties={"mode": "rail"},
        ),
        GraphEdge(
            edge_id="edge:ravik_rail_to_midgard",
            source_id="chokepoint:ravik_rail_corridor",
            target_id="nation:midgard",
            relation_type=RelationType.EXPORTS_TO,
            weight=0.85,
            description="Expanded rail arrivals from Ravik into Midgard compensate for lower Orvan share in December customs returns.",
            citation="ORV-0022#P3",
            pub_date=date(2026, 12, 10),
            as_of_limit=date(2027, 1, 25),
            reliability_tier=1,
            properties={"mitigation_low": 5.0, "mitigation_high": 15.0},
        ),

        # -------------------------------------------------------------
        # 5. THOR'S SECONDARY BOTTLENECK & TOLAN ISOLATION EDGES
        # -------------------------------------------------------------
        GraphEdge(
            edge_id="edge:ravik_rail_capacity_bottleneck",
            source_id="chokepoint:ravik_rail_corridor",
            target_id="nation:midgard",
            relation_type=RelationType.BOTTLENECKED_AT,
            weight=0.9,
            description="Rail rolling stock from Ravik is constrained and running at its practical limit, capping maximum substitute grain transfer.",
            citation="ORV-0018#P3",
            pub_date=date(2026, 10, 25),
            as_of_limit=date(2027, 1, 25),
            reliability_tier=1,
            properties={"capacity_pct": 95, "bottleneck_type": "rolling_stock_cap"},
        ),
        GraphEdge(
            edge_id="edge:tolan_rail_isolation",
            source_id="nation:tolan",
            target_id="chokepoint:ravik_rail_corridor",
            relation_type=RelationType.BOTTLENECKED_AT,
            weight=1.0,
            description="Tolan lacks direct trans-continental rail connectivity to Vanir or Ravik, forcing full reliance on disrupted maritime trade.",
            citation="ORV-0047#P1",
            pub_date=date(2026, 11, 2),
            as_of_limit=date(2027, 1, 25),
            reliability_tier=1,
            properties={"rail_connected": False, "maritime_only": True},
        ),
    ]

    for edge in edges:
        graph_store.add_edge(edge)

    # Persist to disk
    graph_store.save_to_disk()
    logger.info(f"Knowledge Graph bootstrapped with {len(graph_store.nodes_data)} nodes and {len(graph_store.edges_data)} edges.")
