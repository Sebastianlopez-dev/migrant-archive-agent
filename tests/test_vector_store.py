"""Integration tests for vector_store.py with ChromaDB.

Uses Gemini embedding (project default) for semantic tests.
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

    def test_get_video_metadata_returns_fields_from_first_chunk(
        self, provider, store
    ):
        store.add(
            ids=["v1_chunk_0", "v1_chunk_1"],
            documents=["uno", "dos"],
            metadatas=[
                {
                    "video_id": "v1",
                    "title": "Test Video",
                    "chunk_index": 0,
                    "channel": "Canal 1",
                    "year": 2024,
                    "speaker": "Lina",
                    "duration": 125,
                },
                {
                    "video_id": "v1",
                    "title": "Test Video",
                    "chunk_index": 1,
                    "channel": "Canal 1",
                    "year": 2024,
                    "speaker": "Lina",
                    "duration": 125,
                },
            ],
            embeddings=provider.embed(["uno", "dos"]),
        )

        metadata = store.get_video_metadata("v1")

        assert metadata["video_id"] == "v1"
        assert metadata["title"] == "Test Video"
        assert metadata["year"] == 2024
        assert metadata["channel"] == "Canal 1"
        assert metadata["speaker"] == "Lina"
        assert metadata["duration"] == 125
        assert metadata["chunk_count"] == 2

    def test_get_video_metadata_returns_none_for_missing_video(
        self, provider, store
    ):
        assert store.get_video_metadata("missing") is None

    def test_search_with_year_and_channel_filters(self, provider, store):
        docs = ["Texto del canal 1 2024.", "Texto del canal 2 2024.", "Texto del canal 1 2023."]
        store.add(
            ids=["v1_chunk_0", "v2_chunk_0", "v3_chunk_0"],
            documents=docs,
            metadatas=[
                {"video_id": "v1", "chunk_index": 0, "channel": "Canal 1", "year": 2024},
                {"video_id": "v2", "chunk_index": 0, "channel": "Canal 2", "year": 2024},
                {"video_id": "v3", "chunk_index": 0, "channel": "Canal 1", "year": 2023},
            ],
            embeddings=provider.embed(docs),
        )

        results = store.search(
            provider.embed_query("texto"),
            top_k=5,
            year=2024,
            channel="Canal 1",
        )

        assert len(results) == 1
        assert results[0]["metadata"]["video_id"] == "v1"

    def test_search_with_video_id_and_year_filters(self, provider, store):
        docs = ["Texto 2024.", "Texto 2023."]
        store.add(
            ids=["v1_chunk_0", "v1_chunk_1"],
            documents=docs,
            metadatas=[
                {"video_id": "v1", "chunk_index": 0, "channel": "Canal 1", "year": 2024},
                {"video_id": "v1", "chunk_index": 1, "channel": "Canal 1", "year": 2023},
            ],
            embeddings=provider.embed(docs),
        )

        results = store.search(
            provider.embed_query("texto"),
            top_k=5,
            video_id="v1",
            year=2024,
        )

        assert len(results) == 1
        assert results[0]["metadata"]["chunk_index"] == 0

    def test_search_with_or_filter_on_speaker_or_channel(self, provider, store):
        docs = ["Texto de Lina.", "Texto de Canal 2."]
        store.add(
            ids=["v1_chunk_0", "v2_chunk_0"],
            documents=docs,
            metadatas=[
                {"video_id": "v1", "chunk_index": 0, "channel": "Canal 1", "year": 2024, "speaker": "Lina"},
                {"video_id": "v2", "chunk_index": 0, "channel": "Canal 2", "year": 2024, "speaker": "Ana"},
            ],
            embeddings=provider.embed(docs),
        )

        results = store.search(
            provider.embed_query("texto"),
            top_k=5,
            filters={"$or": [{"speaker": "Lina"}, {"channel": "Canal 2"}]},
        )

        assert len(results) == 2
        video_ids = {r["metadata"]["video_id"] for r in results}
        assert video_ids == {"v1", "v2"}


class TestVectorStoreWhereBuilder:
    """Direct tests for the static where-clause helper."""

    def test_build_where_combines_simple_filters_with_and(self):
        from vector_store import VectorStore
        where = VectorStore._build_where(video_id="v1", year=2024, channel="Canal 1")
        assert where == {
            "$and": [
                {"video_id": "v1"},
                {"year": 2024},
                {"channel": "Canal 1"},
            ]
        }

    def test_build_where_merges_raw_filters_with_and(self):
        from vector_store import VectorStore
        raw = {"$or": [{"speaker": "Lina"}, {"channel": "Canal 2"}]}
        where = VectorStore._build_where(video_id="v1", filters=raw)
        assert where == {
            "$and": [
                {"video_id": "v1"},
                {"$or": [{"speaker": "Lina"}, {"channel": "Canal 2"}]},
            ]
        }


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



