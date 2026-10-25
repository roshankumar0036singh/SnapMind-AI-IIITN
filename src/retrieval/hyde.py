from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field

from src.llm.embeddings import get_embedding_client
from src.config import get_settings


class HyDEResult(BaseModel):
    """
    Result of selective Hypothetical Document Embedding expansion.
    Enforces CONTEXT_UPDATED.md Section 6 constraints:
    - Hypothetical text is an intermediate retrieval probe, NEVER citable evidence.
    - BM25 keyword matching remains anchored to the original query.
    """
    original_query: str
    hypothetical_text: str
    embedding: List[float]
    is_hyde: bool = True
    trigger_reason: str = "gap_filling"


class SelectiveHyDE:
    """
    Selective Hypothetical Document Embedding (HyDE) engine.
    Activated selectively for:
    1. Heimdall's initial exploratory sweep on broad disruption queries.
    2. Run 2 gap-filling when Odin issues a send-back with specific 'missing' items.
    3. Thor/Loki adversarial hypothesis generation.
    """

    def __init__(self):
        self.embedding_client = get_embedding_client()

    @staticmethod
    def generate_hypothetical_document(
        query_text: str,
        agent_id: str = "general",
        scope: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        Synthesizes a concise hypothetical document snippet strictly anchored in Runemark vocabulary.
        """
        scope = scope or {}
        countries = ", ".join(scope.get("countries", [])) or "the region"
        sectors = ", ".join(scope.get("sectors", [])) or "commercial commodities"
        event_id = scope.get("event_id", "the disruption event")

        agent_norm = agent_id.lower().strip()

        if agent_norm == "thor":
            # High-exposure perspective: bottlenecks, severe deficits, price surges
            return (
                f"Official bulletin: Following {event_id}, freight logistics across {countries} face "
                f"critical bottlenecks. In {sectors}, shipments experienced unprecedented volume drops, "
                f"forcing immediate port rationing and surging spot commodity prices."
            )
        elif agent_norm == "loki":
            # Limited-exposure perspective: rerouting, strategic reserves, substitute suppliers
            return (
                f"Industry report: In response to {event_id}, importers across {countries} successfully "
                f"activated contingency inventory and overland rerouting. In {sectors}, alternative suppliers "
                f"and reserve drawdowns maintained market stability without catastrophic commercial failure."
            )
        elif agent_norm == "heimdall":
            # Regulatory verification perspective: customs records, corridor status notices
            return (
                f"Customs and maritime gazette: Formal notice regarding {event_id}. Port authorities across "
                f"{countries} have updated operational transit schedules and customs clearance data for {sectors}."
            )
        else:
            return (
                f"Dispatch regarding {query_text}. Regulatory authorities in {countries} report updated commercial "
                f"trade flow statistics and logistical status for {sectors}."
            )

    def generate_hyde_embedding(
        self,
        query_text: str,
        agent_id: str = "general",
        scope: Optional[Dict[str, Any]] = None,
        trigger_reason: str = "run_2_gap_filling",
    ) -> HyDEResult:
        """
        Generates a hypothetical document snippet and computes its 768-dim dense embedding.
        """
        hypo_text = self.generate_hypothetical_document(query_text, agent_id=agent_id, scope=scope)
        embedding = self.embedding_client.get_embedding(hypo_text)

        return HyDEResult(
            original_query=query_text,
            hypothetical_text=hypo_text,
            embedding=embedding,
            is_hyde=True,
            trigger_reason=trigger_reason,
        )


_hyde_engine: Optional[SelectiveHyDE] = None

def get_hyde_engine() -> SelectiveHyDE:
    global _hyde_engine
    if _hyde_engine is None:
        _hyde_engine = SelectiveHyDE()
    return _hyde_engine
