"""Unit tests for processor.py — chunking + embedding orchestration."""

import re
import sys
from pathlib import Path

import pytest

# Allow importing from tests/ (for FakeEmbeddingProvider) and backend/core/
sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(0, str(Path(__file__).parent.parent / "backend" / "core"))

from ingestion import VideoData  # noqa: E402
from processor import _parse_timestamp  # noqa: E402


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
        """Text shorter than chunk_size produces exactly one enriched chunk."""
        from processor import Processor
        from test_embedding import FakeEmbeddingProvider

        provider = FakeEmbeddingProvider()
        processor = Processor(provider, chunk_size=1000, overlap=200)
        vd = make_videodata("Hola mundo.")
        chunks = processor.chunk(vd)
        assert len(chunks) == 1
        assert "Title: Test Video" in chunks[0].text
        assert "Description: Test description" in chunks[0].text
        assert "[00:00] Hola mundo." in chunks[0].text

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

    def test_chunk_metadata_includes_channel_and_year(self):
        """Each chunk carries channel and year from VideoData.metadata."""
        from processor import Processor
        from test_embedding import FakeEmbeddingProvider

        provider = FakeEmbeddingProvider()
        processor = Processor(provider, chunk_size=100, overlap=20)
        vd = make_videodata(
            "test " * 60,
            video_id="abc123",
            title="Mi Video",
        )
        vd.metadata["channel"] = "Canal 1"
        vd.metadata["upload_date"] = "20240515"
        chunks = processor.chunk(vd)

        assert chunks
        for chunk in chunks:
            assert chunk.metadata["channel"] == "Canal 1"
            assert chunk.metadata["year"] == 2024

    @pytest.mark.parametrize("metadata,expected_channel,expected_year", [
        ({}, "unknown", None),
        ({"uploader": "Plataforma Cero", "upload_date": "20231201"}, "Plataforma Cero", 2023),
    ])
    def test_chunk_metadata_falls_back_when_keys_missing(
        self, metadata, expected_channel, expected_year
    ):
        """Channel/uploader and year fall back gracefully when metadata is sparse."""
        from processor import Processor
        from test_embedding import FakeEmbeddingProvider

        provider = FakeEmbeddingProvider()
        processor = Processor(provider, chunk_size=100, overlap=20)
        vd = make_videodata("test " * 60)
        vd.metadata = metadata
        chunks = processor.chunk(vd)

        assert chunks
        for chunk in chunks:
            assert chunk.metadata["channel"] == expected_channel
            assert chunk.metadata["year"] == expected_year

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
# Timestamp marker parsing
# ---------------------------------------------------------------------------

class TestTimestampParsing:
    """Module-private helper for parsing [MM:SS] / [HH:MM:SS] markers."""

    def test_parses_sub_hour_first_marker(self):
        """Returns seconds for the first [MM:SS] marker."""
        assert _parse_timestamp("[00:00] Hello [01:05] World") == 0

    def test_parses_sub_hour_last_marker(self):
        """Returns seconds for the last [MM:SS] marker."""
        assert _parse_timestamp("[00:00] Hello [01:05] World", last=True) == 65

    def test_parses_hour_plus_marker(self):
        """Returns seconds for an [HH:MM:SS] marker."""
        assert _parse_timestamp("[01:01:01] Late") == 3661

    def test_returns_none_when_no_marker(self):
        """Returns None if the text contains no timestamp marker."""
        assert _parse_timestamp("plain text") is None


# ---------------------------------------------------------------------------
# Enriched chunking fallback
# ---------------------------------------------------------------------------

class TestEnrichedChunking:
    """Processor.chunk() uses enriched text when transcript segments exist."""

    def test_legacy_segments_use_enriched_text(self):
        """Legacy VideoData with segments gets title/description/timestamps."""
        from processor import Processor
        from test_embedding import FakeEmbeddingProvider

        provider = FakeEmbeddingProvider()
        processor = Processor(provider, chunk_size=1000, overlap=200)
        vd = VideoData(
            video_id="legacy",
            title="Legacy Title",
            description="Legacy description",
            transcript_segments=[
                {"text": "Hello", "start": 0, "duration": 1},
                {"text": "World", "start": 65, "duration": 1},
            ],
            full_text="plain legacy text",  # legacy plain text
            metadata={"duration": 70},
        )
        chunks = processor.chunk(vd)
        assert chunks
        assert "Title: Legacy Title" in chunks[0].text
        assert "Description: Legacy description" in chunks[0].text
        assert "[00:00] Hello" in chunks[0].text
        assert "[01:05] World" in chunks[0].text

    def test_empty_segments_keep_plain_full_text(self):
        """VideoData without segments falls back to plain full_text."""
        from processor import Processor
        from test_embedding import FakeEmbeddingProvider

        provider = FakeEmbeddingProvider()
        processor = Processor(provider, chunk_size=1000, overlap=200)
        vd = VideoData(
            video_id="plain",
            title="Plain Title",
            description="Plain description",
            transcript_segments=[],
            full_text="plain text only",
            metadata={"duration": 0},
        )
        chunks = processor.chunk(vd)
        assert len(chunks) == 1
        assert chunks[0].text == "plain text only"

    def test_chunk_metadata_uses_first_and_last_markers(self):
        """Chunk start_time / end_time come from first/last markers."""
        from processor import Processor
        from test_embedding import FakeEmbeddingProvider

        provider = FakeEmbeddingProvider()
        processor = Processor(provider, chunk_size=15, overlap=5)
        # 10 sentences → segments at 0s, 5s, 10s, ... 45s
        sentences = " ".join(f"Sentence number {i}." for i in range(10))
        vd = make_videodata(sentences, title="Marker Test")
        chunks = processor.chunk(vd)

        spanning = [
            c
            for c in chunks
            if len(re.findall(r"\[\d{2}:\d{2}\]", c.text)) >= 2
        ]
        assert spanning, "Expected at least one chunk with multiple markers"
        chunk = spanning[0]
        assert chunk.metadata["start_time"] < chunk.metadata["end_time"]

    def test_chunk_metadata_falls_back_to_zero_without_markers(self):
        """Chunks without timestamp markers get 0.0 for start/end time."""
        from processor import Processor
        from test_embedding import FakeEmbeddingProvider

        provider = FakeEmbeddingProvider()
        # Small chunks split the header away from the single segment marker.
        processor = Processor(provider, chunk_size=4, overlap=2)
        vd = VideoData(
            video_id="header_only",
            title="T",
            description="D",
            transcript_segments=[{"text": "x", "start": 999, "duration": 1}],
            full_text="x",
            metadata={"duration": 1000},
        )
        chunks = processor.chunk(vd)
        header_chunk = [c for c in chunks if "[" not in c.text]
        assert header_chunk
        assert header_chunk[0].metadata["start_time"] == 0.0
        assert header_chunk[0].metadata["end_time"] == 0.0


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
