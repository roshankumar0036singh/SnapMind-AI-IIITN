from datetime import date
from unittest.mock import MagicMock
import pytest

from src.schemas.retrieval import SearchFilters, SearchQuery, SearchResultItem
from src.retrieval.gates import RetrievalSecurityGates
from src.retrieval.query_dedup import QueryDeduplicationCache


def test_as_of_clock_gate():
    as_of = date(2027, 1, 25)
    filters = SearchFilters(as_of_date=as_of)

    valid_item = SearchResultItem(
        chunk_id="VALID-001#P1",
        doc_id="VALID-001",
        paragraph_no=1,
        text="Valid pre-cutoff news",
        title="Title",
        country="Midgard",
        sector="wheat",
        pub_date=date(2027, 1, 20),
        reliability_tier=2,
        source_name="Wire",
        source_type="news",
        score=0.9,
    )
    future_item = SearchResultItem(
        chunk_id="FUTURE-001#P1",
        doc_id="FUTURE-001",
        paragraph_no=1,
        text="Future post-cutoff news (Clock violation)",
        title="Title",
        country="Midgard",
        sector="wheat",
        pub_date=date(2027, 2, 10),
        reliability_tier=2,
        source_name="Wire",
        source_type="news",
        score=0.95,
    )

    gated = RetrievalSecurityGates.enforce_gates([valid_item, future_item], filters)
    assert len(gated) == 1
    assert gated[0].doc_id == "VALID-001"


def test_retraction_gate():
    filters = SearchFilters(as_of_date=date(2027, 1, 25), exclude_retracted=True)

    normal_item = SearchResultItem(
        chunk_id="DOC-001#P1",
        doc_id="DOC-001",
        paragraph_no=1,
        text="Normal news",
        title="Title",
        country="Midgard",
        sector="wheat",
        pub_date=date(2027, 1, 15),
        reliability_tier=2,
        source_name="Wire",
        source_type="news",
        score=0.8,
        is_retracted=False,
    )
    retracted_item = SearchResultItem(
        chunk_id="DOC-002#P1",
        doc_id="DOC-002",
        paragraph_no=1,
        text="Retracted false report",
        title="Title",
        country="Midgard",
        sector="wheat",
        pub_date=date(2027, 1, 15),
        reliability_tier=2,
        source_name="Wire",
        source_type="news",
        score=0.85,
        is_retracted=True,
    )

    gated = RetrievalSecurityGates.enforce_gates([normal_item, retracted_item], filters)
    assert len(gated) == 1
    assert gated[0].doc_id == "DOC-001"


def test_query_deduplication_cache():
    cache = QueryDeduplicationCache()
    filters = SearchFilters(as_of_date=date(2027, 1, 25), country="Midgard")
    query = SearchQuery(
        agent_id="thor",
        query_text="grain export stoppage",
        filters=filters,
        top_k=5,
    )

    mock_search_fn = MagicMock()
    mock_item = SearchResultItem(
        chunk_id="RES-001#P1",
        doc_id="RES-001",
        paragraph_no=1,
        text="Result excerpt",
        title="Title",
        country="Midgard",
        sector="wheat",
        pub_date=date(2027, 1, 10),
        reliability_tier=1,
        source_name="Wire",
        source_type="news",
        score=0.88,
    )
    mock_search_fn.return_value = [mock_item]

    # First call: executes search_fn
    resp1 = cache.execute_with_cache(query, mock_search_fn)
    assert resp1.from_cache is False
    assert len(resp1.results) == 1
    assert mock_search_fn.call_count == 1

    # Second call: served from cache without invoking search_fn
    resp2 = cache.execute_with_cache(query, mock_search_fn)
    assert resp2.from_cache is True
    assert resp2.query_hash == resp1.query_hash
    assert len(resp2.results) == 1
    assert mock_search_fn.call_count == 1  # Unchanged
