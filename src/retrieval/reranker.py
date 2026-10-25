import os
import math
from typing import List, Optional, Tuple, Dict, Any

from src.schemas.retrieval import SearchResultItem
from src.config import get_settings


class CrossEncoderReranker:
    """
    Reranker for hybrid search candidates using Cohere's state-of-the-art Reranker (rerank-v3.5).
    Evaluates deep sentence-level query-document interaction over top ~25-30 candidates
    and selects top 5-8 high-precision excerpts.
    Preserves outlet credibility tiers, timestamps, and deliberate trap flags.
    Fulfills CONTEXT_UPDATED.md Section 6.
    """

    DEFAULT_MODEL_NAME = "rerank-v3.5"

    def __init__(
        self,
        api_key: Optional[str] = None,
        model_name: Optional[str] = None,
        enable_heavy_model: bool = False,
    ):
        settings = get_settings()
        self.api_key = api_key or settings.COHERE_API_KEY or os.getenv("COHERE_API_KEY")
        self.model_name = model_name or os.getenv("COHERE_RERANK_MODEL", self.DEFAULT_MODEL_NAME)
        self.enable_heavy_model = enable_heavy_model
        self._cohere_client = None

    @property
    def cohere_client(self):
        if self._cohere_client is None and self.api_key:
            try:
                import cohere
                self._cohere_client = cohere.Client(api_key=self.api_key)
            except Exception as e:
                print(f"Notice: Cohere client initialization failed ({e}). Using fast cross-scoring fallback.")
                self._cohere_client = False
        return self._cohere_client

    @staticmethod
    def _fast_cross_score(query: str, doc_text: str, title: str) -> float:
        """
        Fast, deterministic cross-scoring function used when Cohere API is offline or unconfigured.
        Evaluates exact phrase matching, term overlap, title alignment, and frequency density.
        """
        q_tokens = [t.lower() for t in query.strip().split() if len(t) > 1]
        if not q_tokens:
            return 0.0

        full_doc = f"{title} {doc_text}".lower()
        title_lower = title.lower()

        # 1. Exact phrase match bonus
        q_clean = query.strip().lower()
        exact_bonus = 2.0 if q_clean in full_doc else 0.0

        # 2. Token overlap score
        matches = 0
        title_matches = 0
        for token in q_tokens:
            if token in full_doc:
                matches += 1
            if token in title_lower:
                title_matches += 1

        overlap_ratio = matches / len(q_tokens)
        title_ratio = title_matches / len(q_tokens)

        # 3. Frequency density
        token_freq_score = 0.0
        words = full_doc.split()
        total_words = max(len(words), 1)
        for token in set(q_tokens):
            count = words.count(token)
            if count > 0:
                token_freq_score += math.log(1 + count)

        density = min(token_freq_score / math.log(1 + total_words), 2.0)

        # Combined normalized score
        raw_score = (overlap_ratio * 3.0) + (title_ratio * 2.0) + exact_bonus + density
        return round(1.0 / (1.0 + math.exp(-raw_score + 2.0)), 4)

    def rerank(
        self,
        query: str,
        candidates: List[SearchResultItem],
        top_k: int = 5,
    ) -> List[SearchResultItem]:
        """
        Reranks candidate documents against the query using Cohere Rerank API (with deterministic fallback).
        Preserves all metadata, trap flags, and credibility tiers.
        """
        if not candidates:
            return []

        # 1. Try Cohere Rerank if client is available
        if self.cohere_client and hasattr(self.cohere_client, "rerank"):
            try:
                documents = [f"{c.title}\n\n{c.text}" for c in candidates]
                response = self.cohere_client.rerank(
                    model=self.model_name,
                    query=query,
                    documents=documents,
                    top_n=min(top_k, len(candidates)),
                )
                
                reranked_results: List[SearchResultItem] = []
                for item in response.results:
                    cand = candidates[item.index]
                    cand.score = round(float(item.relevance_score), 4)
                    reranked_results.append(cand)
                return reranked_results
            except Exception as e:
                print(f"Notice: Cohere rerank API call failed ({e}). Falling back to fast cross-scorer.")

        # 2. Fallback: Fast deterministic lexical-semantic cross-scoring
        scored_candidates: List[Tuple[float, float, SearchResultItem]] = []
        for cand in candidates:
            score_before = cand.score
            score_after = self._fast_cross_score(query, cand.text, cand.title)
            cand.score = score_after
            scored_candidates.append((score_after, score_before, cand))

        scored_candidates.sort(key=lambda x: x[0], reverse=True)
        return [cand for _, _, cand in scored_candidates[:top_k]]


_reranker_instance: Optional[CrossEncoderReranker] = None

def get_reranker() -> CrossEncoderReranker:
    global _reranker_instance
    if _reranker_instance is None:
        _reranker_instance = CrossEncoderReranker()
    return _reranker_instance
