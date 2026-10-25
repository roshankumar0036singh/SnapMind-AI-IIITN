from datetime import date
from pathlib import Path
import pytest

from src.ingestion.damage_detector import DamageDetector
from src.schemas.ingest import DocumentMetadata


def test_empty_file_detection():
    detector = DamageDetector()
    empty_file = Path("tests/fixtures/damaged_pack/ORV-0023.txt")
    assert empty_file.exists(), "ORV-0023.txt fixture must exist"

    report = detector.inspect(empty_file, metadata=None, raw_text="")
    assert report.is_damaged is True
    assert report.damage_type == "empty"
    assert "empty file" in report.quarantine_reason.lower() or "0 bytes" in report.quarantine_reason.lower()


def test_corrupted_encoding_detection(tmp_path):
    detector = DamageDetector()
    corrupt_file = tmp_path / "corrupt.txt"
    corrupt_file.write_bytes(b"Header\n---\nSome text with bad \xef\xbf\xbd characters.")

    report = detector.inspect(
        corrupt_file,
        metadata=None,
        raw_text="Header\n---\nSome text with bad \ufffd characters.",
    )
    assert report.is_damaged is True
    assert report.damage_type == "encoding"


def test_truncated_text_detection(tmp_path):
    detector = DamageDetector()
    truncated_file = tmp_path / "truncated.txt"
    truncated_file.write_text("Header\n---\nThe shipment was diverted because of the")

    meta = DocumentMetadata(
        doc_id="TRUNC-001",
        title="Truncated Report",
        source_name="News",
        source_type="wire",
        reliability_tier=2,
        pub_date=date(2027, 1, 10),
        country="Midgard",
        sector="agriculture",
    )

    report = detector.inspect(
        truncated_file,
        metadata=meta,
        raw_text="The shipment was diverted because of the",
    )
    assert report.is_damaged is True
    assert report.damage_type == "truncated"


def test_duplicate_detection(tmp_path):
    detector = DamageDetector()
    text = (
        "Utgard grain deliveries have slowed significantly following regional border disputes. "
        "Authorities are advising commercial operators to seek alternative routing immediately."
    )

    file1 = tmp_path / "doc1.txt"
    file1.write_text(text)
    meta1 = DocumentMetadata(
        doc_id="DOC-001",
        title="Original",
        source_name="Wire",
        source_type="wire",
        reliability_tier=2,
        pub_date=date(2027, 1, 10),
        country="Utgard",
        sector="agriculture",
    )

    report1 = detector.inspect(file1, metadata=meta1, raw_text=text)
    assert report1.is_duplicate is False

    # Exact duplicate with different ID
    file2 = tmp_path / "doc2.txt"
    file2.write_text(text)
    meta2 = DocumentMetadata(
        doc_id="DOC-002",
        title="Copy",
        source_name="Blog",
        source_type="blog",
        reliability_tier=4,
        pub_date=date(2027, 1, 11),
        country="Utgard",
        sector="agriculture",
    )

    report2 = detector.inspect(file2, metadata=meta2, raw_text=text)
    assert report2.is_duplicate is True
    assert report2.duplicate_of == "DOC-001"


def test_retraction_relationship(tmp_path):
    detector = DamageDetector()

    # Original article
    meta_orig = DocumentMetadata(
        doc_id="ORV-0043",
        title="Orvan grain corridor renewed for a second year",
        source_name="Wire",
        source_type="news",
        reliability_tier=2,
        pub_date=date(2027, 1, 12),
        country="Orvan",
        sector="agriculture",
    )

    # Correction / Retraction notice referencing ORV-0043
    meta_corr = DocumentMetadata(
        doc_id="ORV-0013",
        title="Correction: ORV-0043 agreement was not renewed",
        source_name="Wire",
        source_type="correction",
        reliability_tier=1,
        pub_date=date(2027, 1, 13),
        country="Orvan",
        sector="agriculture",
    )

    f_corr = tmp_path / "corr.txt"
    f_corr.write_text("Notice text that exceeds minimum length threshold.")
    detector.inspect(f_corr, metadata=meta_corr, raw_text="Notice text that exceeds minimum length threshold.")

    f_orig = tmp_path / "orig.txt"
    f_orig.write_text("Original article text that is sufficiently long to pass length checks.")
    report_orig = detector.inspect(f_orig, metadata=meta_orig, raw_text="Original article text that is sufficiently long to pass length checks.")

    assert report_orig.is_corrected is True
    assert report_orig.corrected_by == "ORV-0013"
