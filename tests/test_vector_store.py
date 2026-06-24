"""Integration tests for vector_store.py with ChromaDB.

Uses Gemini embedding (project default) for semantic tests.
BGE-M3 tests require a conda environment — skipped in uv/pip.
"""

import os
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(0, str(Path(__file__).parent.parent / "backend" / "core"))

from test_embedding import FakeEmbeddingProvider  # noqa: E402


def has_gemini() -> bool:
    return bool(os.getenv("GEMINI_API_KEY"))


class TestVectorStoreCRUD:
    """Core CRUD operations — uses FakeEmbeddingProvider (no API calls)."""

    @pytest.fixture
    def provider(self):
        return FakeEmbeddingProvider(dimension=128)

    @pytest.fixture
    def store(self):
        from vector_store import VectorStore
        store = VectorStore(persist_dir=":memory:")
        yield store
        try:
            store.delete_collection()
        except Exception:
            pass

    def test_add_and_search_single_document(self, provider, store):
        store.add(
            ids=["doc_1"],
            documents=["La migración es un derecho humano fundamental."],
            metadatas=[{"video_id": "v001", "chunk_index": 0}],
            embeddings=provider.embed(
                ["La migración es un derecho humano fundamental."]
            ),
        )
        results = store.search(provider.embed_query("derecho humano"), top_k=3)
        assert len(results) > 0
        assert results[0]["metadata"]["video_id"] == "v001"

    def test_add_multiple_documents(self, provider, store):
        docs = ["Documento uno.", "Documento dos.", "Documento tres."]
        store.add(
            ids=[f"doc_{i}" for i in range(3)],
            documents=docs,
            metadatas=[{"video_id": "v002", "chunk_index": i} for i in range(3)],
            embeddings=provider.embed(docs),
        )
        results = store.search(provider.embed_query("documento"), top_k=5)
        assert len(results) == 3

    def test_search_top_k_limits_results(self, provider, store):
        docs = [f"Documento número {i}." for i in range(10)]
        store.add(
            ids=[f"d_{i}" for i in range(10)],
            documents=docs,
            metadatas=[{"video_id": "v004", "chunk_index": i} for i in range(10)],
            embeddings=provider.embed(docs),
        )
        results = store.search(provider.embed_query("documento"), top_k=3)
        assert len(results) <= 3

    def test_delete_collection(self, provider, store):
        store.add(
            ids=["x"],
            documents=["Texto de prueba."],
            metadatas=[{"video_id": "v005", "chunk_index": 0}],
            embeddings=provider.embed(["Texto de prueba."]),
        )
        assert store.count > 0
        store.delete_collection()
        assert store.count == 0

    def test_count_reflects_documents(self, provider, store):
        assert store.count == 0
        store.add(
            ids=["a", "b", "c"],
            documents=["uno", "dos", "tres"],
            metadatas=[
                {"video_id": "v", "chunk_index": 0},
                {"video_id": "v", "chunk_index": 1},
                {"video_id": "v", "chunk_index": 2},
            ],
            embeddings=provider.embed(["uno", "dos", "tres"]),
        )
        assert store.count == 3


class TestVectorStoreVideoScoping:
    """Scoped search and video catalog aggregation."""

    @pytest.fixture
    def provider(self):
        return FakeEmbeddingProvider(dimension=128)

    @pytest.fixture
    def store(self):
        from vector_store import VectorStore
        store = VectorStore(persist_dir=":memory:")
        yield store
        try:
            store.delete_collection()
        except Exception:
            pass

    def test_search_with_video_id_filter_returns_only_matching_video(
        self, provider, store
    ):
        docs = ["Texto del video A.", "Texto del video B."]
        store.add(
            ids=["vA_chunk_0", "vB_chunk_0"],
            documents=docs,
            metadatas=[
                {"video_id": "vA", "chunk_index": 0},
                {"video_id": "vB", "chunk_index": 0},
            ],
            embeddings=provider.embed(docs),
        )

        results = store.search(
            provider.embed_query("texto"), top_k=5, video_id="vA"
        )

        assert len(results) == 1
        assert results[0]["metadata"]["video_id"] == "vA"

    def test_search_with_video_id_filter_no_match_returns_empty(
        self, provider, store
    ):
        docs = ["Texto del video A."]
        store.add(
            ids=["vA_chunk_0"],
            documents=docs,
            metadatas=[{"video_id": "vA", "chunk_index": 0}],
            embeddings=provider.embed(docs),
        )

        results = store.search(
            provider.embed_query("texto"), top_k=5, video_id="missing"
        )

        assert results == []

    def test_get_unique_videos_returns_ids_and_chunk_counts(
        self, provider, store
    ):
        store.add(
            ids=["vA_chunk_0", "vA_chunk_1", "vB_chunk_0"],
            documents=["uno", "dos", "tres"],
            metadatas=[
                {"video_id": "vA", "chunk_index": 0},
                {"video_id": "vA", "chunk_index": 1},
                {"video_id": "vB", "chunk_index": 0},
            ],
            embeddings=provider.embed(["uno", "dos", "tres"]),
        )

        videos = store.get_unique_videos()

        assert len(videos) == 2
        by_id = {v["video_id"]: v for v in videos}
        assert by_id["vA"]["chunk_count"] == 2
        assert by_id["vB"]["chunk_count"] == 1

    def test_get_unique_videos_is_empty_for_empty_collection(
        self, provider, store
    ):
        assert store.get_unique_videos() == []


@pytest.mark.skipif(not has_gemini(), reason="GEMINI_API_KEY not set")
class TestVectorStoreGemini:
    """Semantic relevance tests — uses Gemini embedding (project default)."""

    @pytest.fixture(scope="class")
    def gemini_provider(self):
        from embedding_gemini import GeminiEmbeddingProvider
        return GeminiEmbeddingProvider()

    @pytest.fixture
    def store(self):
        from vector_store import VectorStore
        store = VectorStore(persist_dir=":memory:")
        yield store
        try:
            store.delete_collection()
        except Exception:
            pass

    def test_search_returns_ordered_by_relevance(self, gemini_provider, store):
        store.add(
            ids=["a", "b"],
            documents=[
                "Python es un lenguaje de programación.",
                "La migración en el mediterráneo es un tema complejo.",
            ],
            metadatas=[
                {"video_id": "v003", "chunk_index": 0},
                {"video_id": "v003", "chunk_index": 1},
            ],
            embeddings=gemini_provider.embed([
                "Python es un lenguaje de programación.",
                "La migración en el mediterráneo es un tema complejo.",
            ]),
        )
        results = store.search(
            gemini_provider.embed_query("migración mediterráneo"), top_k=2
        )
        assert "migración" in results[0]["document"].lower()


@pytest.mark.skip(reason="BGE-M3 requires conda environment (torch/numpy compat)")
class TestVectorStoreBGE_M3:
    """BGE-M3 integration tests — requires conda env with torch >= 2.4."""
    pass
