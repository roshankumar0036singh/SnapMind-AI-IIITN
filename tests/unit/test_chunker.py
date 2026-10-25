from datetime import date
import pytest

from src.ingestion.chunker import ParagraphChunker
from src.schemas.ingest import DocumentMetadata, DocumentDamageReport


def test_chunk_with_paragraph_tags():
    chunker = ParagraphChunker()
    meta = DocumentMetadata(
        doc_id="TEST-001",
        title="Test Document",
        source_name="Wire",
        source_type="wire",
        reliability_tier=2,
        pub_date=date(2027, 1, 10),
        country="Midgard",
        sector="wheat",
    )
    damage = DocumentDamageReport()
    body = (
        "Headline Preamble\n\n"
        "[P1] First paragraph discussing grain stocks.\n\n"
        "[P2] Second paragraph describing port congestion.\n\n"
        "[P3] Third paragraph quoting trade officials."
    )

    chunks = chunker.chunk_document(meta, body, damage)
    assert len(chunks) == 3
    assert chunks[0].chunk_id == "TEST-001#P1"
    assert chunks[0].paragraph_no == 1
    assert "Headline Preamble" in chunks[0].text
    assert "First paragraph" in chunks[0].text

    assert chunks[1].chunk_id == "TEST-001#P2"
    assert chunks[1].paragraph_no == 2
    assert "Second paragraph" in chunks[1].text

    assert chunks[2].chunk_id == "TEST-001#P3"
    assert chunks[2].paragraph_no == 3


def test_chunk_fallback_short():
    chunker = ParagraphChunker()
    meta = DocumentMetadata(
        doc_id="TEST-002",
        title="Short Notice",
        source_name="Official",
        source_type="official",
        reliability_tier=1,
        pub_date=date(2027, 1, 11),
        country="Tolan",
        sector="general",
    )
    body = "Short single announcement without any paragraph tags."
    chunks = chunker.chunk_document(meta, body, DocumentDamageReport())

    assert len(chunks) == 1
    assert chunks[0].chunk_id == "TEST-002#P1"
    assert chunks[0].text == body


def test_chunk_empty_body():
    chunker = ParagraphChunker()
    meta = DocumentMetadata(
        doc_id="TEST-003",
        title="Empty",
        source_name="Blog",
        source_type="blog",
        reliability_tier=4,
        pub_date=date(2027, 1, 12),
        country="Midgard",
        sector="general",
    )
    chunks = chunker.chunk_document(meta, "   ", DocumentDamageReport())
    assert len(chunks) == 0
