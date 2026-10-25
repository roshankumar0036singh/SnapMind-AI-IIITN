from typing import List, Dict, Any, Optional
from src.tools.retrieval_tools import RetrievalTools
from src.tools.trade_tools import TradeTools
from src.schemas.case_file import CaseFile

class ThorToolsBinding:
    """
    Thor-specific tool binding and autonomous lookup engine:
    Focuses on: severe bottlenecks, naval blockades, port closures, trade volume drops.
    """
    def __init__(self):
        self.retrieval = RetrievalTools()
        self.trade = TradeTools()

    def gather_round1_evidence(self, case: CaseFile, max_tier: int = 4) -> Dict[str, Any]:
        """
        Thor's Round 1 lookup sweep:
        1. Searches hybrid index for severe disruption, closures, and bottlenecks.
        2. Queries trade tables to identify maximum drop / trough percentage.
        """
        as_of = case.as_of
        countries = case.scope.countries if case.scope else []
        sectors = case.scope.sectors if case.scope else []

        # Formulate Thor-oriented search queries
        query = f"blockade shutdown capacity loss disruption bottleneck {case.question}"
        country_filter = countries[0] if countries else None
        sector_filter = sectors[0] if sectors else None

        docs = self.retrieval.search_docs(
            query=query,
            as_of_date=as_of,
            country=country_filter,
            sector=sector_filter,
            max_tier=max_tier,
            match_count=10,
            rerank_top_k=5
        )

        # Formulate trade table lookups (searching for lowest drop)
        tables = self.trade.find_tables(country=country_filter, sector=sector_filter)
        trade_calculations = []

        for tbl in tables[:2]:  # Check first 2 matching tables
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
        Thor searches for NEW evidence to counter Loki's attacks during Round 2.
        """
        query = f"congestion freight cost physical damage persistent decline {attacked_topic}"
        return self.retrieval.search_docs(
            query=query,
            as_of_date=case.as_of,
            max_tier=max_tier,
            match_count=6,
            rerank_top_k=3
        )
