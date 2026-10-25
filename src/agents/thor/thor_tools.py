"""
src/agents/thor/thor_tools.py
=============================
Thor-specific autonomous search and trade math pipeline.
Focuses on: severe bottlenecks, port shutdowns, blockades, capacity drops, and trade troughs.
"""

from datetime import date
from typing import Any, Dict, List, Optional

from src.schemas.retrieval import SearchFilters, SearchResultItem
from src.schemas.trade import MetricCalculationResult
from src.tools.registry import AgentToolRegistry


class ThorToolsBinding:
    """
    Autonomous evidence gatherer for Thor (The Alarm).
    Executes hybrid search and trade math via the AgentToolRegistry.
    """

    def __init__(self, registry: AgentToolRegistry):
        self.registry = registry

    def gather_high_exposure_evidence(
        self,
        question: str,
        as_of_date: date,
        country: Optional[str] = None,
        sector: Optional[str] = None,
        event_id: Optional[str] = None,
        max_tier: int = 4,
        top_k: int = 6,
    ) -> List[SearchResultItem]:
        """
        Executes hybrid document search focusing on high-exposure angles:
        port closures, structural damage, capacity loss, supply shortages, price surges.
        """
        # Embed target countries, sectors, and question into query text for hybrid BM25 + Vector ranking
        terms = [question]
        if country:
            terms.append(country)
        if sector:
            terms.append(sector)
        if event_id:
            terms.append(event_id)

        query_text = (
            f"closure shutdown blockade damage capacity loss crisis drop bottleneck {' '.join(terms)}"
        )
        # We enforce hard as_of_date, reliability tier, and quarantine gates.
        # Country/sector are ranked by vector & BM25 to avoid excluding exporting origin nations (e.g. Orvan to Midgard).
        filters = SearchFilters(
            as_of_date=as_of_date,
            country=None,  # Handled via BM25/Vector query to capture bilateral flows
            sector=None,
            event_id=None,
            tier_max=max_tier,
            exclude_retracted=True,
            exclude_damaged=True,
            exclude_injections=True,
        )

        try:
            results = self.registry.execute_tool(
                "thor",
                "search_docs",
                query_text=query_text,
                filters=filters,
                top_k=top_k,
            )
            return results or []
        except Exception as e:
            print(f"[ThorTools] search_docs error: {e}")
            return []

    def compute_worst_case_trade_decline(
        self,
        sector: Optional[str] = None,
        country_pair: Optional[str] = None,
        as_of_date: Optional[date] = None,
    ) -> List[Dict[str, Any]]:
        """
        Queries trade tables and executes compute_change to locate the steepest drop.
        """
        calculations: List[Dict[str, Any]] = []
        try:
            tables = self.registry.execute_tool(
                "thor",
                "find_tables",
                sector=sector,
                country_pair=country_pair,
            )

            if not tables:
                return []

            # Examine candidate tables (up to 2)
            for tbl in tables[:2]:
                table_id = tbl.get("table_id")
                if not table_id:
                    continue

                # Compute baseline (prior 12 months) vs post-event drop
                res: MetricCalculationResult = self.registry.execute_tool(
                    "thor",
                    "compute_change",
                    table_id=table_id,
                    baseline_window=("2025-01", "2025-12"),
                    comparison_window=("2026-01", "2026-06"),
                    metric="volume",
                    as_of_date=as_of_date,
                )

                if res and res.status == "success":
                    calculations.append({
                        "table_id": table_id,
                        "metric": res.metric,
                        "percentage_change": res.percentage_change,
                        "baseline_average": res.baseline_average,
                        "comparison_average": res.comparison_average,
                        "citations": res.citations,
                        "rows_used": res.rows_used,
                        "rows_excluded": res.rows_excluded,
                    })

        except Exception as e:
            print(f"[ThorTools] compute_worst_case_trade_decline error: {e}")

        return calculations

    def search_counter_evidence(
        self,
        dispute_topic: str,
        as_of_date: date,
        max_tier: int = 3,
        top_k: int = 4,
    ) -> List[SearchResultItem]:
        """
        Retrieves fresh counter-evidence for Round 2 attacks on Loki's resilience claims.
        """
        query_text = (
            f"congested overwhelmed rail capacity limitation transit cost physical bottleneck {dispute_topic}"
        )
        filters = SearchFilters(
            as_of_date=as_of_date,
            tier_max=max_tier,
            exclude_retracted=True,
            exclude_damaged=True,
            exclude_injections=True,
        )

        try:
            return self.registry.execute_tool(
                "thor",
                "search_docs",
                query_text=query_text,
                filters=filters,
                top_k=top_k,
            ) or []
        except Exception as e:
            print(f"[ThorTools] search_counter_evidence error: {e}")
            return []
