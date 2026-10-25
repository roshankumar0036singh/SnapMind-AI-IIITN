from datetime import date
import pytest

from src.retrieval.reranker import CrossEncoderReranker
from src.schemas.retrieval import SearchResultItem


def _make_candidate(doc_id: str, title: str, text: str, tier: int = 1, score: float = 0.5) -> SearchResultItem:
    return SearchResultItem(
        chunk_id=f"{doc_id}#P1",
        doc_id=doc_id,
        paragraph_no=1,
        text=text,
        title=title,
        country="Orvan",
        sector="agriculture",
        pub_date=date(2026, 10, 15),
        reliability_tier=tier,
        source_name="Runemark Daily",
        source_type="news",
        score=score,
        is_corrected=False,
        corrected_by=None,
        is_retracted=False,
    )


def test_reranker_relevance_ranking():
    reranker = CrossEncoderReranker(enable_heavy_model=False)

    candidates = [
        _make_candidate(
            doc_id="DOC-IRRELEVANT",
            title="Music Festival in Alfheim",
            text="The annual flute and harp festival opened today in Alfheim.",
            score=0.70,  # Initially had high RRF score by accident
        ),
        _make_candidate(
            doc_id="DOC-RELEVANT",
            title="Orvan Grain Corridor Disruption",
            text="Commercial wheat transport through the Orvan corridor has halted, impacting grain exports.",
            score=0.45,  # Initially had lower RRF score
        ),
        _make_candidate(
            doc_id="DOC-PARTIAL",
            title="Maritime Ship Inspections",
            text="General naval patrols report routine maritime traffic across northern waters.",
            score=0.50,
        ),
    ]

    query = "Orvan grain corridor disruption"
    reranked = reranker.rerank(query, candidates, top_k=2)

    assert len(reranked) == 2
    # The relevant document must now be ranked #1
    assert reranked[0].doc_id == "DOC-RELEVANT"
    assert reranked[0].score > reranked[1].score


def test_reranker_preserves_metadata():
    reranker = CrossEncoderReranker(enable_heavy_model=False)

    item = _make_candidate(
        doc_id="ORV-0005",
        title="Orvan Agricultural Notice",
        text="Official yield figures for winter wheat in Orvan.",
        tier=1,
        score=0.03,
    )
    item.is_corrected = True
    item.corrected_by = "ORV-0006"

    reranked = reranker.rerank("winter wheat in Orvan", [item], top_k=1)

    assert len(reranked) == 1
    res = reranked[0]
    assert res.doc_id == "ORV-0005"
    assert res.reliability_tier == 1
    assert res.is_corrected is True
    assert res.corrected_by == "ORV-0006"
    assert res.pub_date == date(2026, 10, 15)


def test_reranker_empty_candidates():
    reranker = CrossEncoderReranker()
    res = reranker.rerank("empty query", [], top_k=5)
    assert res == []
