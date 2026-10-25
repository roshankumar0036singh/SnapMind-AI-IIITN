import os
from typing import List, Optional
from google import genai
from google.genai import types

from src.config import get_settings


class GeminiEmbeddingClient:
    """
    Client for generating 768-dimensional dense vectors using Gemini embedding models.
    Matches Supabase vector(768) column specification in supabase_schema.sql.
    """
    DEFAULT_MODEL = "gemini-embedding-2"
    MODEL_NAME = "gemini-embedding-2"
    DIMENSION = 768

    def __init__(self, api_key: Optional[str] = None, model_name: Optional[str] = None):
        settings = get_settings()
        self.api_key = api_key or settings.GEMINI_API_KEY or os.getenv("GEMINI_API_KEY")
        self.model_name = model_name or os.getenv("GEMINI_EMBEDDING_MODEL", self.DEFAULT_MODEL)
        if not self.api_key:
            self._client = None
        else:
            self._client = genai.Client(api_key=self.api_key)

    @property
    def client(self) -> genai.Client:
        if self._client is None:
            settings = get_settings()
            self.api_key = self.api_key or settings.GEMINI_API_KEY or os.getenv("GEMINI_API_KEY")
            if not self.api_key:
                raise ValueError("GEMINI_API_KEY is not set in environment or .env file.")
            self._client = genai.Client(api_key=self.api_key)
        return self._client

    def get_embedding(self, text: str) -> List[float]:
        """
        Generates a 768-dim float vector for a single string.
        """
        cleaned = text.strip()
        if not cleaned:
            return [0.0] * self.DIMENSION

        response = self.client.models.embed_content(
            model=self.model_name,
            contents=cleaned,
            config=types.EmbedContentConfig(output_dimensionality=self.DIMENSION),
        )
        if response.embeddings and len(response.embeddings) > 0:
            return response.embeddings[0].values
        raise RuntimeError("Failed to retrieve embedding from Gemini API.")

    def get_embeddings_batch(self, texts: List[str], batch_size: int = 20) -> List[List[float]]:
        """
        Embeds a list of texts in chunks to respect rate limits and payload sizes.
        """
        all_embeddings: List[List[float]] = []
        for i in range(0, len(texts), batch_size):
            chunk = texts[i : i + batch_size]
            cleaned_chunk = [t.strip() if t.strip() else " " for t in chunk]
            response = self.client.models.embed_content(
                model=self.model_name,
                contents=cleaned_chunk,
                config=types.EmbedContentConfig(output_dimensionality=self.DIMENSION),
            )
            if response.embeddings:
                all_embeddings.extend([e.values for e in response.embeddings])
            else:
                raise RuntimeError(f"Batch embedding failed for batch starting at index {i}")
        return all_embeddings


_embedding_client: Optional[GeminiEmbeddingClient] = None

def get_embedding_client() -> GeminiEmbeddingClient:
    global _embedding_client
    if _embedding_client is None:
        _embedding_client = GeminiEmbeddingClient()
    return _embedding_client
