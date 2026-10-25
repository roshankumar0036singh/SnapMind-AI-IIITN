from typing import List, Dict, Any, Optional
from src.tools.retrieval_tools import RetrievalTools
from src.tools.trade_tools import TradeTools
from src.schemas.case_file import CaseFile

class LokiToolsBinding:
    """
    Loki-specific tool binding and autonomous lookup engine:
    Focuses on: commercial resilience, overland rail substitution, secondary ports,
    inventory reserves, and supplier diversification.
    """
    def __init__(self):
        self.retrieval = RetrievalTools()
        self.trade = TradeTools()

    def gather_round1_evidence(self, case: CaseFile, max_tier: int = 4) -> Dict[str, Any]:
        """
        Loki's Round 1 lookup sweep:
        1. Searches hybrid index for resilience, substitution, rail rerouting, and inventory buffers.
        2. Queries trade tables to identify overland spikes or alternative route volume.
        """
        as_of = case.as_of
        countries = case.scope.countries if case.scope else []
        sectors = case.scope.sectors if case.scope else []

        # Formulate Loki-oriented search queries
        query = f"alternative route rail substitution stockpile inventory recovery reserve {case.question}"
        sector_filter = sectors[0] if sectors else None

        docs = self.retrieval.search_docs(
            query=query,
            as_of_date=as_of,
            country=None,  # Intentionally broad to catch alternative neighboring suppliers
            sector=sector_filter,
            max_tier=max_tier,
            match_count=10,
            rerank_top_k=5
        )

        # Formulate trade table lookups (searching for replacement route traffic)
        tables = self.trade.find_tables(sector=sector_filter)
        trade_calculations = []

        for tbl in tables[:2]:
            calc = self.trade.compute_change(
                table_id=tbl["table_id"],
                baseline_start="2025-01-01",
                baseline_end="2025-12-31",
                comparison_start="2026-01-01",
                comparison_end=as_of,
                as_of_date=as_of,
                metric="volume"
            )
            if "error" not in calc:
                trade_calculations.append(calc)

        return {
            "documents": docs,
            "trade_calculations": trade_calculations
        }

    def gather_defence_evidence(self, case: CaseFile, attacked_topic: str, max_tier: int = 3) -> List[Dict[str, Any]]:
        """
        Loki searches for NEW evidence to counter Thor's attacks during Round 2.
        """
        query = f"overland capacity expansion tariff waiver domestic stockpile {attacked_topic}"
        return self.retrieval.search_docs(
            query=query,
            as_of_date=case.as_of,
            max_tier=max_tier,
            match_count=6,
            rerank_top_k=3
        )
