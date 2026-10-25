import pytest
from src.llm.embeddings import GeminiEmbeddingClient


def test_embedding_client_init():
    client = GeminiEmbeddingClient(api_key="mock_test_key")
    assert "embedding" in client.MODEL_NAME
    assert client.DIMENSION == 768
    assert client.api_key == "mock_test_key"


def test_embedding_client_missing_key():
    client = GeminiEmbeddingClient(api_key=None)
    # When api_key is None and environment has no key, accessing .client raises ValueError
    if not client.api_key:
        with pytest.raises(ValueError, match="GEMINI_API_KEY"):
            _ = client.client
