import os
from pathlib import Path
import pytest

from src.ingestion.parsers import parse_document, TxtParser, PdfParser, DocxParser
from src.schemas.ingest import DocumentMetadata

CORPUS_DIR = Path("data/test_packs/dev_pack_E5/docs")


@pytest.mark.skipif(not CORPUS_DIR.exists(), reason="Corpus dev_pack_E5 not found")
def test_parse_real_txt_document():
    txt_path = CORPUS_DIR / "ATL-0002.txt"
    metadata, body = parse_document(txt_path)

    assert isinstance(metadata, DocumentMetadata)
    assert metadata.doc_id == "ATL-0002"
    assert metadata.country == "Asgard"
    assert metadata.sector == "general"
    assert metadata.reliability_tier == 1
    assert metadata.format == "TXT"
    assert metadata.source_name == "Realm Trade Ministry"
    assert "[P1]" in body
    assert "[P2]" in body
    assert "Asgard Port" in body


@pytest.mark.skipif(not CORPUS_DIR.exists(), reason="Corpus dev_pack_E5 not found")
def test_parse_real_pdf_document():
    pdf_path = CORPUS_DIR / "ATL-0001.pdf"
    metadata, body = parse_document(pdf_path)

    assert isinstance(metadata, DocumentMetadata)
    assert metadata.doc_id == "ATL-0001"
    assert metadata.country == "Utgard"
    assert metadata.reliability_tier == 1
    assert metadata.format == "PDF"
    assert "[P1]" in body
    assert "East Sea" in body


@pytest.mark.skipif(not CORPUS_DIR.exists(), reason="Corpus dev_pack_E5 not found")
def test_parse_real_docx_document():
    docx_path = CORPUS_DIR / "ATL-0003.docx"
    metadata, body = parse_document(docx_path)

    assert isinstance(metadata, DocumentMetadata)
    assert metadata.doc_id == "ATL-0003"
    assert metadata.country == "Valhalla"
    assert metadata.reliability_tier == 1
    assert metadata.format == "DOCX"
    assert "[P1]" in body
    assert "rice exporter" in body


def test_missing_header_separator(tmp_path):
    bad_file = tmp_path / "bad.txt"
    bad_file.write_text("DOC_ID: BAD-001\nTITLE: No separator here\nBody text without dash separator.")

    with pytest.raises(ValueError, match="missing the mandatory '---'"):
        parse_document(bad_file)


def test_missing_required_fields(tmp_path):
    bad_file = tmp_path / "missing_fields.txt"
    bad_file.write_text("DOC_ID: BAD-002\nTITLE: Incomplete Header\n---\nBody text.")

    with pytest.raises(ValueError, match="missing required fields"):
        parse_document(bad_file)


def test_unsupported_format(tmp_path):
    bad_file = tmp_path / "unsupported.xyz"
    bad_file.write_text("data")

    with pytest.raises(ValueError, match="Unsupported document format"):
        parse_document(bad_file)
