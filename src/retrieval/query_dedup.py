import hashlib
import json
from typing import Dict, List, Callable, Optional

from src.schemas.retrieval import SearchQuery, SearchResultItem, SearchResponse


class QueryDeduplicationCache:
    """
    Query deduplication cache.
    Prevents repeated queries or tool calls across agent rounds (NFR5 & Acceptance Check 10).
    """

    def __init__(self, max_size: int = 500):
        self._cache: Dict[str, List[SearchResultItem]] = {}
        self.max_size = max_size

    def compute_query_hash(self, query: SearchQuery) -> str:
        """
        Computes a stable SHA-256 hash of (agent_id, normalized_query, sorted_filters).
        """
        norm_text = query.query_text.strip().lower()
        filter_dict = query.filters.model_dump(mode="json")
        sorted_filter_str = json.dumps(filter_dict, sort_keys=True)

        payload = f"{query.agent_id}:{norm_text}:{sorted_filter_str}:{query.top_k}"
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()

    def get(self, query_hash: str) -> Optional[List[SearchResultItem]]:
        return self._cache.get(query_hash)

    def put(self, query_hash: str, results: List[SearchResultItem]) -> None:
        if len(self._cache) >= self.max_size:
            # Evict first key
            first_key = next(iter(self._cache))
            del self._cache[first_key]
        self._cache[query_hash] = results

    def execute_with_cache(
        self,
        query: SearchQuery,
        search_fn: Callable[[SearchQuery], List[SearchResultItem]],
    ) -> SearchResponse:
        """
        Checks cache before running query; stores and returns formatted SearchResponse.
        """
        query_hash = self.compute_query_hash(query)
        cached_results = self.get(query_hash)

        if cached_results is not None:
            return SearchResponse(
                query_hash=query_hash,
                from_cache=True,
                total_candidates=len(cached_results),
                results=cached_results,
            )

        fresh_results = search_fn(query)
        self.put(query_hash, fresh_results)

        return SearchResponse(
            query_hash=query_hash,
            from_cache=False,
            total_candidates=len(fresh_results),
            results=fresh_results,
        )


_dedup_cache = QueryDeduplicationCache()

def get_dedup_cache() -> QueryDeduplicationCache:
    return _dedup_cache
