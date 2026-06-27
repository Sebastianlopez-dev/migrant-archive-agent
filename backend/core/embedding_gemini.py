"""Gemini embedding provider.

Cloud-based embeddings via Google GenAI API.  Uses the
`gemini-embedding-2` model with 3072-dim Matryoshka-capable output.

Requires GEMINI_API_KEY in environment.
"""

import os

from google import genai

from core.embedding import EmbeddingProvider


GEMINI_MODEL = "models/gemini-embedding-2"
GEMINI_DIMENSION = 3072


class GeminiEmbeddingProvider(EmbeddingProvider):
    """EmbeddingProvider backed by Google Gemini API.

    Dimensions: 3072 (Matryoshka-capable — can truncate to smaller dims).
    """

    def __init__(self, api_key: str | None = None):
        """Initialise the Gemini client.

        Args:
            api_key: Optional API key.  If omitted, reads from
                     GEMINI_API_KEY environment variable.
        """
        key = api_key or os.getenv("GEMINI_API_KEY")
        if not key:
            raise ValueError(
                "GEMINI_API_KEY is required. Set it as an env var or pass api_key=."
            )
        self._client = genai.Client(api_key=key)

    def embed(self, texts: list[str]) -> list[list[float]]:
        """Embed a batch of texts via the Gemini API.

        gemini-embedding-2 does NOT support batching in the genai SDK —
        a list of strings is treated as one interleaved multimodal input.
        Each text is embedded individually.

        Returns one 3072-dim vector per input string.
        """
        if not texts:
            return []

        embeddings: list[list[float]] = []
        for text in texts:
            response = self._client.models.embed_content(
                model=GEMINI_MODEL,
                contents=text,
            )
            embeddings.append(response.embeddings[0].values)
        return embeddings

    def embed_query(self, text: str) -> list[float]:
        """Embed a single query string."""
        if not text:
            return [0.0] * self.dimension
        result = self.embed([text])
        return result[0] if result else [0.0] * self.dimension

    @property
    def dimension(self) -> int:
        return GEMINI_DIMENSION
