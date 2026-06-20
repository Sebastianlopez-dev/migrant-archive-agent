"""BGE-M3 embedding provider.

Local CPU embeddings via sentence-transformers. Uses the BAAI/bge-m3
model with 1024-dim dense output. Model is loaded lazily and cached as a
singleton (like _get_model() in ingestion_audio.py).

Requires: pip install sentence-transformers  (or conda equivalent)
The torch/transformers imports are deferred until first use.
"""

from core.embedding import EmbeddingProvider


BGE_M3_MODEL = "BAAI/bge-m3"
BGE_M3_DIMENSION = 1024

# Singleton cache: model_name → loaded model instance
_model_cache: dict[str, any] = {}


def _get_model(model_name: str = BGE_M3_MODEL):
    """Return a cached BGE-M3 model, loading it only on first call.

    Uses sentence-transformers (more stable pip wheels than FlagEmbedding).
    """
    if model_name not in _model_cache:
        from sentence_transformers import SentenceTransformer

        _model_cache[model_name] = SentenceTransformer(
            model_name,
            device="cpu",
        )
    return _model_cache[model_name]


class BGEM3EmbeddingProvider(EmbeddingProvider):
    """EmbeddingProvider backed by local BGE-M3 model.

    Dimensions: 1024 (dense output). Device: CPU.
    """

    def embed(self, texts: list[str]) -> list[list[float]]:
        """Embed a batch of texts via BGE-M3.

        Returns one 1024-dim vector per input string.
        """
        if not texts:
            return []

        model = _get_model()
        embeddings = model.encode(texts)
        return embeddings.tolist()

    def embed_query(self, text: str) -> list[float]:
        """Embed a single query string."""
        if not text:
            return [0.0] * self.dimension
        result = self.embed([text])
        return result[0] if result else [0.0] * self.dimension

    @property
    def dimension(self) -> int:
        return BGE_M3_DIMENSION
