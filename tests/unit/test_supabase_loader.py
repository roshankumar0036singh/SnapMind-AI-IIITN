from pathlib import Path
from unittest.mock import MagicMock, patch
import pytest

from src.ingestion.supabase_loader import SupabaseDocumentLoader

PACK_DIR = Path("data/test_packs/dev_pack_E5")


@pytest.mark.skipif(not PACK_DIR.exists(), reason="dev_pack_E5 not found")
def test_supabase_loader_preparation():
    loader = SupabaseDocumentLoader(use_embeddings=False)
    
    # Mock the admin client and table upsert
    mock_admin = MagicMock()
    mock_table = MagicMock()
    mock_upsert = MagicMock()
    mock_execute = MagicMock()
    
    mock_admin.table.return_value = mock_table
    mock_table.upsert.return_value = mock_upsert
    mock_upsert.execute.return_value = mock_execute
    loader._admin = mock_admin

    report = loader.load_pack_to_supabase(PACK_DIR, generate_embeddings=False)
    assert report.pack_name == "dev_pack_E5"
    assert report.total_files == 76
    assert report.files_ok > 60

    # Verify that upsert was called with batches of records
    assert mock_admin.table.called
    assert mock_table.upsert.called
