"""
src/agents/loki/loki_tools.py
=============================
Loki-specific autonomous search and trade math pipeline.
Focuses on: commercial resilience, alternative routes, rail substitution,
inventory buffers, recovery trends, and supplier diversification.
"""

from datetime import date
from typing import Any, Dict, List, Optional

from src.schemas.retrieval import SearchFilters, SearchResultItem
from src.schemas.trade import MetricCalculationResult
from src.tools.registry import AgentToolRegistry


class LokiToolsBinding:
    """
    Autonomous evidence gatherer for Loki (The Trickster).
    Executes hybrid search and trade math via the AgentToolRegistry.
    """

    def __init__(self, registry: AgentToolRegistry):
        self.registry = registry

    def gather_resilience_evidence(
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
        Executes hybrid document search focusing on limited-exposure and resilience angles:
        alternative rail routes, secondary ports, emergency stockpiles, inventory buffers,
        tariffs waived, commercial substitution.
        """
        terms = [question]
        if country:
            terms.append(country)
        if sector:
            terms.append(sector)
        if event_id:
            terms.append(event_id)

        query_text = (
            f"alternative route rail substitution stockpile inventory reserve recovery buffer {' '.join(terms)}"
        )
        # Broaden country/sector filters to catch bilateral corridor agreements
        filters = SearchFilters(
            as_of_date=as_of_date,
            country=None,
            sector=None,
            event_id=None,
            tier_max=max_tier,
            exclude_retracted=True,
            exclude_damaged=True,
            exclude_injections=True,
        )

        try:
            results = self.registry.execute_tool(
                "loki",
                "search_docs",
                query_text=query_text,
                filters=filters,
                top_k=top_k,
            )
            return results or []
        except Exception as e:
            print(f"[LokiTools] search_docs error: {e}")
            return []

    def compute_substitution_or_recovery(
        self,
        sector: Optional[str] = None,
        country_pair: Optional[str] = None,
        as_of_date: Optional[date] = None,
    ) -> List[Dict[str, Any]]:
        """
        Queries trade tables to find recovery signals or volume increases along replacement corridors.
        """
        calculations: List[Dict[str, Any]] = []
        try:
            tables = self.registry.execute_tool(
                "loki",
                "find_tables",
                sector=sector,
                country_pair=country_pair,
            )

            if not tables:
                return []

            for tbl in tables[:2]:
                table_id = tbl.get("table_id")
                if not table_id:
                    continue

                res: MetricCalculationResult = self.registry.execute_tool(
                    "loki",
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
            print(f"[LokiTools] compute_substitution_or_recovery error: {e}")

        return calculations

    def search_counter_evidence(
        self,
        dispute_topic: str,
        as_of_date: date,
        max_tier: int = 3,
        top_k: int = 4,
    ) -> List[SearchResultItem]:
        """
        Retrieves fresh counter-evidence for Round 2 attacks on Thor's alarmist claims.
        """
        query_text = (
            f"overland expansion inventory release domestic reserve partial recovery {dispute_topic}"
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
                "loki",
                "search_docs",
                query_text=query_text,
                filters=filters,
                top_k=top_k,
            ) or []
        except Exception as e:
            print(f"[LokiTools] search_counter_evidence error: {e}")
            return []
