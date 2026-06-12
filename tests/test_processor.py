"""Unit tests for processor.py — chunking + embedding orchestration."""

import sys
from pathlib import Path

import pytest

# Allow importing from tests/ (for FakeEmbeddingProvider) and backend/core/
sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(0, str(Path(__file__).parent.parent / "backend" / "core"))

from ingestion import VideoData  # noqa: E402


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_videodata(
    full_text: str,
    video_id: str = "test_vid",
    title: str = "Test Video",
    transcript_segments: list[dict] | None = None,
) -> VideoData:
    """Factory for test VideoData objects."""
    if transcript_segments is None:
        # Build simple segments: one per sentence
        sentences = [s.strip() for s in full_text.split(".") if s.strip()]
        transcript_segments = [
            {"text": s + ".", "start": i * 5.0, "duration": 4.5}
            for i, s in enumerate(sentences)
        ]
    return VideoData(
        video_id=video_id,
        title=title,
        description="Test description",
        transcript_segments=transcript_segments,
        full_text=full_text,
        metadata={"duration": len(transcript_segments) * 5},
    )


# ---------------------------------------------------------------------------
# Chunking tests
# ---------------------------------------------------------------------------

class TestChunking:
    """Chunking logic: token estimation, overlap, metadata."""

    def test_short_text_single_chunk(self):
        """Text shorter than chunk_size produces exactly one chunk."""
        from processor import Processor
        from test_embedding import FakeEmbeddingProvider

        provider = FakeEmbeddingProvider()
        processor = Processor(provider, chunk_size=1000, overlap=200)
        vd = make_videodata("Hola mundo.")
        chunks = processor.chunk(vd)
        assert len(chunks) == 1
        assert chunks[0].text == "Hola mundo."

    def test_long_text_multiple_chunks(self):
        """Text longer than chunk_size produces multiple chunks."""
        from processor import Processor
        from test_embedding import FakeEmbeddingProvider

        provider = FakeEmbeddingProvider()
        processor = Processor(provider, chunk_size=100, overlap=20)
        # ~2000 chars → should produce multiple chunks with chunk_size=100
        vd = make_videodata("palabra " * 300)
        chunks = processor.chunk(vd)
        assert len(chunks) > 1

    def test_overlap_preserves_context(self):
        """Words near chunk boundaries appear in adjacent chunks."""
        from processor import Processor
        from test_embedding import FakeEmbeddingProvider

        provider = FakeEmbeddingProvider()
        processor = Processor(provider, chunk_size=200, overlap=50)
        vd = make_videodata("one two three four five six seven eight nine ten")
        chunks = processor.chunk(vd)

        if len(chunks) < 2:
            pytest.skip("Text too short for overlap test with these params")

        # Last few words of chunk 0 should appear in chunk 1
        words0 = set(chunks[0].text.split()[-3:])
        words1 = set(chunks[1].text.split()[:6])
        assert words0 & words1, f"No overlap found between chunks"

    def test_chunk_metadata(self):
        """Each chunk carries video_id and chunk_index in metadata."""
        from processor import Processor
        from test_embedding import FakeEmbeddingProvider

        provider = FakeEmbeddingProvider()
        processor = Processor(provider, chunk_size=100, overlap=20)
        vd = make_videodata("test " * 60, video_id="abc123", title="Mi Video")
        chunks = processor.chunk(vd)

        for i, chunk in enumerate(chunks):
            assert chunk.metadata["video_id"] == "abc123"
            assert chunk.metadata["title"] == "Mi Video"
            assert chunk.metadata["chunk_index"] == i
            assert "start_time" in chunk.metadata
            assert "end_time" in chunk.metadata

    def test_chunk_indexes_are_sequential(self):
        """Chunk indexes go 0, 1, 2, ..."""
        from processor import Processor
        from test_embedding import FakeEmbeddingProvider

        provider = FakeEmbeddingProvider()
        processor = Processor(provider, chunk_size=100, overlap=20)
        vd = make_videodata("word " * 200)
        chunks = processor.chunk(vd)

        indexes = [c.metadata["chunk_index"] for c in chunks]
        assert indexes == list(range(len(chunks)))

    def test_empty_text_handled(self):
        """Empty or whitespace-only text should not crash."""
        from processor import Processor
        from test_embedding import FakeEmbeddingProvider

        provider = FakeEmbeddingProvider()
        processor = Processor(provider)
        vd = make_videodata("")
        chunks = processor.chunk(vd)
        assert isinstance(chunks, list)


# ---------------------------------------------------------------------------
# Embedding orchestration tests
# ---------------------------------------------------------------------------

class TestEmbeddingOrchestration:
    """Processor correctly delegates to EmbeddingProvider."""

    def test_embed_chunks_calls_provider(self):
        """embed_chunks returns embeddings matching chunk count."""
        from processor import Processor
        from test_embedding import FakeEmbeddingProvider

        provider = FakeEmbeddingProvider(dimension=256)
        processor = Processor(provider, chunk_size=100, overlap=20)
        vd = make_videodata("test " * 100)
        chunks = processor.chunk(vd)
        embeddings = processor.embed_chunks(chunks)

        assert len(embeddings) == len(chunks)
        for emb in embeddings:
            assert len(emb) == 256

    def test_process_returns_chunks_and_embeddings(self):
        """process() returns both chunks and embeddings in one call."""
        from processor import Processor
        from test_embedding import FakeEmbeddingProvider

        provider = FakeEmbeddingProvider(dimension=128)
        processor = Processor(provider)
        vd = make_videodata("contenido " * 50)
        chunks, embeddings = processor.process(vd)

        assert len(chunks) == len(embeddings)
        assert all(len(e) == 128 for e in embeddings)
