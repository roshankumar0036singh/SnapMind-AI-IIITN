import os
from datetime import date
from typing import List, Optional, Dict, Any

from src.supabase_client import get_supabase_client, get_supabase_admin
from src.llm.embeddings import get_embedding_client
from src.schemas.retrieval import SearchQuery, SearchResultItem, SearchResponse


class HybridSearcher:
    """
    Hybrid RAG retrieval engine combining Gemini 768-dim vectors + PostgreSQL BM25 FTS.
    Enforces Simulated Clock (as-of date) and metadata filtering via Supabase RPC.
    Fulfills Phase 7 and Acceptance Check 2.
    """

    def __init__(self):
        self.embedding_client = get_embedding_client()
        self._client = None

    @property
    def client(self):
        if self._client is None:
            self._client = get_supabase_admin()
        return self._client

    def search(self, query: SearchQuery) -> List[SearchResultItem]:
        """
        Executes hybrid search against Supabase runemark_documents.
        """
        # 1. Generate 768-dim embedding for query text
        query_embedding: List[float] = [0.0] * 768
        if self.embedding_client and self.embedding_client.api_key:
            try:
                query_embedding = self.embedding_client.get_embedding(query.query_text)
            except Exception as e:
                # Fallback to zero vector so text/BM25 search proceeds
                print(f"Warning: Failed to generate query embedding ({e}). Proceeding with FTS only.")

        # 2. Call Supabase RPC stored procedure 'hybrid_search_docs'
        candidate_count = query.top_k * 4 if query.use_reranker else query.top_k
        rpc_params = {
            "query_text": query.query_text,
            "query_embedding": query_embedding,
            "as_of_limit": query.filters.as_of_date.isoformat(),
            "match_count": candidate_count,
            "full_text_weight": 1.0,
            "vector_weight": 1.0,
            "filter_country": query.filters.country,
            "filter_sector": query.filters.sector,
            "max_tier": query.filters.tier_max or 4,
        }

        try:
            res = self.client.rpc("hybrid_search_docs", rpc_params).execute()
            rows = res.data or []
        except Exception as e:
            raise RuntimeError(f"Supabase hybrid_search_docs RPC failed: {e}")

        # 3. Format into typed SearchResultItems
        results: List[SearchResultItem] = []
        for row in rows:
            doc_id = row.get("doc_id", "")
            content = row.get("content", "")
            
            # Select relevant paragraph or first 400 characters as excerpt
            excerpt = content[:400] + ("..." if len(content) > 400 else "")
            
            item = SearchResultItem(
                chunk_id=f"{doc_id}#P1",
                doc_id=doc_id,
                paragraph_no=1,
                text=excerpt,
                title=row.get("title", ""),
                country=row.get("country", ""),
                sector=row.get("sector", ""),
                pub_date=date.fromisoformat(row.get("pub_date")),
                reliability_tier=row.get("reliability_tier", 4),
                source_name=row.get("source_name", "Unknown"),
                source_type=row.get("source_type", "news"),
                score=float(row.get("combined_score", 0.0)),
                is_corrected=row.get("is_corrected", False),
                corrected_by=row.get("corrected_by"),
                is_retracted=row.get("is_retracted", False),
            )
            results.append(item)

        # 4. Apply Cross-Encoder Reranker if requested
        if query.use_reranker and results:
            from src.retrieval.reranker import get_reranker
            results = get_reranker().rerank(query.query_text, results, top_k=query.top_k)

        return results


_hybrid_searcher: Optional[HybridSearcher] = None

def get_hybrid_searcher() -> HybridSearcher:
    global _hybrid_searcher
    if _hybrid_searcher is None:
        _hybrid_searcher = HybridSearcher()
    return _hybrid_searcher
