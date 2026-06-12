"""Tests for BGE-M3 embedding provider.

Tests the real model (no mocks) since we are in a conda environment
with sentence-transformers + torch installed.
"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "backend" / "core"))


def _clear_cache():
    import embedding_bge_m3 as mod
    mod._model_cache.clear()


class TestBGEM3EmbeddingProvider:
    """Tests with the real BGE-M3 model via sentence-transformers."""

    @pytest.fixture(autouse=True)
    def setup(self):
        _clear_cache()
        yield
        _clear_cache()

    def test_dimension_is_1024(self):
        from embedding_bge_m3 import BGEM3EmbeddingProvider
        provider = BGEM3EmbeddingProvider()
        assert provider.dimension == 1024

    def test_embed_empty_list(self):
        from embedding_bge_m3 import BGEM3EmbeddingProvider
        provider = BGEM3EmbeddingProvider()
        result = provider.embed([])
        assert result == []

    def test_embed_batch(self):
        from embedding_bge_m3 import BGEM3EmbeddingProvider
        provider = BGEM3EmbeddingProvider()
        texts = ["Hola mundo", "La migración es un derecho humano"]
        result = provider.embed(texts)
        assert len(result) == 2
        assert len(result[0]) == 1024
        assert len(result[1]) == 1024
        # Real embeddings should have non-zero values
        assert any(v != 0.0 for v in result[0])

    def test_embed_query(self):
        from embedding_bge_m3 import BGEM3EmbeddingProvider
        provider = BGEM3EmbeddingProvider()
        result = provider.embed_query("¿Qué es la migración?")
        assert len(result) == 1024

    def test_embed_query_empty_string(self):
        from embedding_bge_m3 import BGEM3EmbeddingProvider
        provider = BGEM3EmbeddingProvider()
        result = provider.embed_query("")
        assert len(result) == 1024
        assert all(v == 0.0 for v in result)

    def test_singleton_caches_model(self):
        """Multiple provider instances reuse the same loaded model."""
        from embedding_bge_m3 import BGEM3EmbeddingProvider, _model_cache

        provider1 = BGEM3EmbeddingProvider()
        _ = provider1.embed(["test"])  # triggers model load

        cache_size_after_first = len(_model_cache)
        assert cache_size_after_first == 1

        provider2 = BGEM3EmbeddingProvider()
        _ = provider2.embed(["test"])

        # Cache should still have only one entry
        assert len(_model_cache) == 1
