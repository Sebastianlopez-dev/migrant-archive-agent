"""Unit tests for EmbeddingProvider contract and implementations."""

import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "backend" / "core"))

from embedding import EmbeddingProvider  # noqa: E402


# ---------------------------------------------------------------------------
# FakeEmbeddingProvider — controlled mock for unit tests
# ---------------------------------------------------------------------------

class FakeEmbeddingProvider(EmbeddingProvider):
    """Returns fixed embeddings for deterministic testing."""

    def __init__(self, dimension: int = 768):
        self._dimension = dimension

    def embed(self, texts: list[str]) -> list[list[float]]:
        return [[0.1] * self._dimension for _ in texts]

    def embed_query(self, text: str) -> list[float]:
        return [0.1] * self._dimension

    @property
    def dimension(self) -> int:
        return self._dimension


# ---------------------------------------------------------------------------
# Contract tests
# ---------------------------------------------------------------------------

class TestEmbeddingProviderContract:
    """EmbeddingProvider ABC cannot be instantiated directly."""

    def test_cannot_instantiate_abc(self):
        with pytest.raises(TypeError):
            EmbeddingProvider()  # type: ignore[abstract]

    def test_subclass_must_implement_embed(self):
        class Incomplete(EmbeddingProvider):
            def embed_query(self, text: str) -> list[float]:
                return [0.0]

        with pytest.raises(TypeError):
            Incomplete()  # type: ignore[abstract]

    def test_subclass_must_implement_embed_query(self):
        class Incomplete(EmbeddingProvider):
            def embed(self, texts: list[str]) -> list[list[float]]:
                return [[0.0]]

        with pytest.raises(TypeError):
            Incomplete()  # type: ignore[abstract]

    def test_subclass_must_implement_dimension(self):
        class Incomplete(EmbeddingProvider):
            def embed(self, texts: list[str]) -> list[list[float]]:
                return [[0.0]]

            def embed_query(self, text: str) -> list[float]:
                return [0.0]

        with pytest.raises(TypeError):
            Incomplete()  # type: ignore[abstract]


class TestFakeEmbeddingProvider:
    """Fake provider behaves deterministically."""

    def test_embed_returns_correct_count(self):
        provider = FakeEmbeddingProvider(dimension=128)
        texts = ["hola", "mundo", "test"]
        result = provider.embed(texts)
        assert len(result) == 3

    def test_embed_returns_correct_dimension(self):
        provider = FakeEmbeddingProvider(dimension=256)
        result = provider.embed(["test"])
        assert len(result[0]) == 256

    def test_embed_query_dimension(self):
        provider = FakeEmbeddingProvider(dimension=128)
        result = provider.embed_query("test")
        assert len(result) == 128

    def test_dimension_property(self):
        provider = FakeEmbeddingProvider(dimension=42)
        assert provider.dimension == 42
