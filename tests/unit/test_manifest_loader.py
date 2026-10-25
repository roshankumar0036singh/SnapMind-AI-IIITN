from pathlib import Path
import pytest

from src.ingestion.manifest_loader import ManifestLoader

PACK_DIR = Path("data/test_packs/dev_pack_E5")


@pytest.mark.skipif(not PACK_DIR.exists(), reason="dev_pack_E5 not found")
def test_manifest_loader_real_e5_pack():
    loader = ManifestLoader()
    result = loader.load_pack(PACK_DIR)

    assert result.pack_name == "dev_pack_E5"
    assert result.event_id == "E5"
    assert result.ingest_report.total_files == 76

    # Verify that valid documents generated paragraph chunks
    assert result.ingest_report.files_ok > 60
    assert len(result.chunks) > 100

    # Verify that the 0-byte damaged file (ORV-0023) was caught and recorded
    damaged_doc_ids = [d["doc_id"] for d in result.ingest_report.files_damaged]
    assert "ORV-0023" in damaged_doc_ids

    # Verify chunk structure
    first_chunk = result.chunks[0]
    assert "#P" in first_chunk.chunk_id
    assert first_chunk.doc_id != ""
    assert len(first_chunk.text) > 0
    assert first_chunk.metadata.reliability_tier in [1, 2, 3, 4]


def test_manifest_missing_directory(tmp_path):
    loader = ManifestLoader()
    with pytest.raises(FileNotFoundError, match="manifest.json not found"):
        loader.load_pack(tmp_path)
