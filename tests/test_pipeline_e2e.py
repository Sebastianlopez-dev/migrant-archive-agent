"""E2E test: full pipeline with Gemini API + ChromaDB + real video data.

Requires GEMINI_API_KEY in environment or .env file.
Skipped gracefully if key is missing or no cached video data exists.
"""

import os
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "backend" / "core"))

from ingestion import VideoData  # noqa: E402


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def has_gemini_key() -> bool:
    """Check if Gemini API key is available."""
    return bool(os.getenv("GEMINI_API_KEY"))


def find_cached_video() -> Path | None:
    """Find a cached VideoData JSON to use for testing."""
    for raw_dir in ["data/raw/whisper", "data/raw/captions"]:
        raw_path = Path(raw_dir)
        if raw_path.exists():
            json_files = list(raw_path.glob("*.json"))
            if json_files:
                return json_files[0]
    return None


# ---------------------------------------------------------------------------
# E2E tests
# ---------------------------------------------------------------------------

@pytest.mark.skipif(
    not has_gemini_key(),
    reason="GEMINI_API_KEY not set — skipping E2E test",
)
class TestPipelineE2E:
    """Full pipeline: VideoData → chunks → Gemini embeddings → ChromaDB → search."""

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

    def test_full_pipeline_cached_video(self, gemini_provider, store):
        """Process a cached video through the entire pipeline."""
        video_path = find_cached_video()
        if video_path is None:
            pytest.skip("No cached VideoData JSON found in data/raw/")

        from processor import Processor

        # Load real video data
        video_data = VideoData.load_json(str(video_path))

        # Process
        processor = Processor(gemini_provider, chunk_size=1000, overlap=200)
        chunks = processor.chunk(video_data)
        embeddings = processor.embed_chunks(chunks)

        assert len(chunks) > 0
        assert len(embeddings) == len(chunks)
        assert len(embeddings[0]) == gemini_provider.dimension

        # Store
        store.add(
            ids=[f"{video_data.video_id}_chunk_{c.metadata['chunk_index']}"
                 for c in chunks],
            documents=[c.text for c in chunks],
            metadatas=[c.metadata for c in chunks],
            embeddings=embeddings,
        )

        # Search
        query_emb = gemini_provider.embed_query(video_data.title)
        results = store.search(query_emb, top_k=3)

        assert len(results) > 0
        assert all(
            r["metadata"]["video_id"] == video_data.video_id for r in results
        )

    def test_embedding_dimensions_consistent(self, gemini_provider):
        """Gemini provider returns consistent dimensions."""
        embeddings = gemini_provider.embed(["Hola", "Mundo"])
        assert len(embeddings) == 2
        assert len(embeddings[0]) == gemini_provider.dimension
        assert len(embeddings[0]) == len(embeddings[1])
