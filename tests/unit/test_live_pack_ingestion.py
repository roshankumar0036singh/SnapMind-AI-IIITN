from pathlib import Path
import json
from unittest.mock import patch, MagicMock
import pytest

from src.cli.ingest_pack import ingest_event_pack

PACK_DIR = Path("data/test_packs/dev_pack_E5")


def test_live_pack_ingestion_with_damage_detection(tmp_path: Path):
    # Create a realistic test pack directory mimicking the Final Round pack
    pack_dir = tmp_path / "final_pack_test"
    docs_dir = pack_dir / "docs"
    docs_dir.mkdir(parents=True)

    # 1. manifest.json
    manifest = {
        "pack": "final_round_pack_test",
        "event_id": "EVT-TEST-01",
        "name": "Test Disruption Event",
        "as_of": "2027-01-25",
        "documents": [
            {
                "DOC_ID": "DOC-VALID-01",
                "EVENT_ID": "EVT-TEST-01",
                "TITLE": "Valid Agricultural Bulletin",
                "SOURCE_NAME": "Ministry",
                "SOURCE_TYPE": "official",
                "RELIABILITY": "1",
                "PUB_DATE": "2026-09-15",
                "COUNTRY": "Midgard",
                "SECTOR": "wheat",
                "file": "DOC-VALID-01.txt",
                "FORMAT": "TXT",
            },
            {
                "DOC_ID": "DOC-EMPTY-02",
                "EVENT_ID": "EVT-TEST-01",
                "TITLE": "Damaged Empty File",
                "SOURCE_NAME": "Tabloid",
                "SOURCE_TYPE": "social",
                "RELIABILITY": "4",
                "PUB_DATE": "2026-09-16",
                "COUNTRY": "Midgard",
                "SECTOR": "wheat",
                "file": "DOC-EMPTY-02.txt",
                "FORMAT": "TXT",
            },
        ],
    }
    (pack_dir / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")

    # 2. Documents
    (docs_dir / "DOC-VALID-01.txt").write_text(
        "DOC_ID: DOC-VALID-01\nTITLE: Valid Agricultural Bulletin\nSOURCE_NAME: Ministry\nCOUNTRY: Midgard\nSECTOR: wheat\nPUB_DATE: 2026-09-15\nSOURCE_TYPE: official\nEVENT_ID: EVT-TEST-01\nRELIABILITY: 1\n---\nOfficial grain report confirming valid status.",
        encoding="utf-8",
    )
    # Empty 0-byte file trap (NFR3)
    (docs_dir / "DOC-EMPTY-02.txt").write_text("", encoding="utf-8")

    # 3. Fixed-layout Trade Table with Damaged Rows (Section 4.5)
    trade_table_content = """TABLE_ID: TRD-TEST-01
COUNTRY_PAIR: Orvan-Midgard
SECTOR: wheat
UNIT: thousand_metric_tons
PERIOD: 2025-01_to_2026-04
EVENT_ID: EVT-TEST-01
---
row_no | month | volume | value
1 | 2025-01-01 | 100.0 | 30.0
2 | 2025-02-01 | 110.0 | 33.0
3 | 2025-03-01 | N/A | 31.0
4 | 2025-03-01 | 105.0 | 31.5
5 | 2025-04-01 | 95.0x | 28.0
6 | 2025-05-01 | 90.0
"""
    (docs_dir / "TRD-TEST-01.txt").write_text(trade_table_content, encoding="utf-8")

    # Mock Supabase table upserts so test executes offline
    with patch("src.ingestion.supabase_loader.get_supabase_admin") as mock_admin, \
         patch("src.cli.ingest_pack.get_supabase_admin") as mock_cli_admin:

        mock_table = MagicMock()
        mock_admin.return_value.table.return_value = mock_table
        mock_cli_admin.return_value.table.return_value = mock_table
        mock_table.upsert.return_value.execute.return_value = MagicMock(data=[])

        summary = ingest_event_pack(
            pack_dir=pack_dir,
            use_embeddings=False,
            extract_graph=False,
        )

        assert summary["pack_name"] == "final_round_pack_test"
        assert summary["as_of"] == "2027-01-25"
        assert summary["files_ok"] == 1
        assert summary["files_damaged"] == 1  # 0-byte file caught (NFR3)
        assert summary["tables_registered"] == 1
        assert summary["valid_trade_rows"] == 2
        # Damaged rows caught: row 3 (missing N/A), row 4 (repeated month), row 5 (bad_number 95.0x), row 6 (cut_off missing value)
        assert summary["damaged_trade_rows"] >= 3
