from typing import List
from src.schemas.retrieval import SearchResultItem, SearchFilters


class RetrievalSecurityGates:
    """
    Hard security gates and policy enforcers for retrieval results.
    Guarantees agents cannot bypass simulated clock rules or cite adversarial traps.
    """

    @staticmethod
    def enforce_gates(
        results: List[SearchResultItem],
        filters: SearchFilters,
    ) -> List[SearchResultItem]:
        """
        Filters and validates candidates:
        1. Simulated Clock: pub_date <= as_of_date
        2. Trap gate: excludes retracted sources if exclude_retracted is True
        3. Reliability ceiling: reliability_tier <= tier_max
        4. Metadata matching: country and sector matching if specified
        """
        gated_results: List[SearchResultItem] = []

        for item in results:
            # 1. As-Of Date Gate
            if item.pub_date > filters.as_of_date:
                # Clock violation - strictly exclude
                continue

            # 2. Retraction Gate
            if filters.exclude_retracted and item.is_retracted:
                continue

            # 3. Credibility Tier Ceiling
            if filters.tier_max and item.reliability_tier > filters.tier_max:
                continue

            # 4. Scope Alignment (defence against look-alike documents)
            if filters.country and item.country.lower() != "general":
                if item.country.lower() != filters.country.lower():
                    continue

            if filters.sector and item.sector.lower() != "general":
                if item.sector.lower() != filters.sector.lower():
                    continue

            gated_results.append(item)

        return gated_results
