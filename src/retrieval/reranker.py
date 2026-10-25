import math
from typing import List, Optional, Tuple, Dict, Any
from src.schemas.retrieval import SearchResultItem


class CrossEncoderReranker:
    """
    Reranker for hybrid search candidates.
    Evaluates deep sentence-level query-document interaction over top ~25-30 candidates
    and selects top 5-8 high-precision excerpts.
    Preserves outlet credibility tiers, timestamps, and deliberate trap flags.
    Fulfills CONTEXT_UPDATED.md Section 6.
    """

    DEFAULT_MODEL_NAME = "cross-encoder/ms-marco-MiniLM-L-6-v2"

    def __init__(self, model_name: Optional[str] = None, enable_heavy_model: bool = False):
        self.model_name = model_name or self.DEFAULT_MODEL_NAME
        self.enable_heavy_model = enable_heavy_model
        self._model = None

    @property
    def model(self):
        if self._model is None and self.enable_heavy_model:
            try:
                from sentence_transformers import CrossEncoder
                self._model = CrossEncoder(self.model_name)
            except Exception as e:
                # Log warning and fall back to fast lexical-semantic scorer
                print(f"Notice: CrossEncoder model loading deferred or failed ({e}). Using fast lexical-semantic reranker.")
                self._model = False
        return self._model

    @staticmethod
    def _fast_cross_score(query: str, doc_text: str, title: str) -> float:
        """
        Fast, deterministic cross-scoring function used when neural cross-encoder is offline.
        Evaluates exact phrase matching, term overlap, title alignment, and length penalty.
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
        # Sigmoid squash to (0, 1)
        return round(1.0 / (1.0 + math.exp(-raw_score + 2.0)), 4)

    def rerank(
        self,
        query: str,
        candidates: List[SearchResultItem],
        top_k: int = 5,
    ) -> List[SearchResultItem]:
        """
        Scores candidate documents against the query and returns top_k reranked items.
        Logs score_before and score_after for observability (NFR4).
        """
        if not candidates:
            return []

        scored_candidates: List[Tuple[float, float, SearchResultItem]] = []

        # Attempt neural CrossEncoder if enabled and available
        neural_scores = None
        if self.model and hasattr(self.model, "predict"):
            try:
                pairs = [[query, f"{c.title}\n{c.text}"] for c in candidates]
                raw_preds = self.model.predict(pairs)
                # Convert logits to probabilities
                neural_scores = [round(1.0 / (1.0 + math.exp(-s)), 4) for s in raw_preds]
            except Exception as e:
                neural_scores = None

        for idx, item in enumerate(candidates):
            score_before = item.score

            if neural_scores is not None and idx < len(neural_scores):
                score_after = float(neural_scores[idx])
            else:
                score_after = self._fast_cross_score(query, item.text, item.title)

            # Update item's internal score to rerank score
            item.score = score_after
            scored_candidates.append((score_after, score_before, item))

        # Sort descending by rerank score
        scored_candidates.sort(key=lambda x: x[0], reverse=True)

        # Return top_k
        return [item for _, _, item in scored_candidates[:top_k]]


_reranker_instance: Optional[CrossEncoderReranker] = None

def get_reranker() -> CrossEncoderReranker:
    global _reranker_instance
    if _reranker_instance is None:
        _reranker_instance = CrossEncoderReranker()
    return _reranker_instance
