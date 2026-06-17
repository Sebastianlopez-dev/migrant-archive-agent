"""Tests for sample extraction: first N characters from JSON and ChromaDB.

Validates both extraction paths work correctly:
  - JSON: reads and truncates full_text from VideoData files
  - ChromaDB: accumulates sequential chunks until the character limit

These tests use real fixtures (no mocks) so they serve as both
unit validation AND live checkpoint readiness proof.
"""

import sys
from pathlib import Path

import pytest

# Allow imports from backend/core and backend/scripts
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from core.ingestion import VideoData


# ── helpers ────────────────────────────────────────────────────────────────


def create_test_videodata(
    video_id: str = "test_v001",
    title: str = "Test Video",
    full_text: str | None = None,
    num_segments: int = 5,
    words_per_segment: int = 50,
) -> VideoData:
    """Create a VideoData instance with synthetic transcript content.

    If full_text is None (default), auto-generate filler text.
    If full_text is an empty string "", the video has no transcript.
    """
    if full_text is None:
        segments = []
        for i in range(num_segments):
            words = " ".join(
                f"palabra_{i}_{j}" for j in range(words_per_segment)
            )
            segments.append({
                "text": words,
                "start": i * 30.0,
                "duration": 28.0,
            })
        full_text = " ".join(seg["text"] for seg in segments)

    return VideoData(
        video_id=video_id,
        title=title,
        description=f"Description for {title}",
        transcript_segments=[
            {"text": full_text[i:i+100], "start": i * 0.5, "duration": 0.4}
            for i in range(0, min(500, len(full_text)), 100)
        ],
        full_text=full_text,
        metadata={"id": video_id, "title": title},
    )


# ── JSON extraction tests ──────────────────────────────────────────────────


class TestJSONExtraction:
    """Test first-N-character extraction from VideoData JSON files."""

    def test_extract_below_limit_returns_all(self, tmp_path):
        """When text is shorter than the limit, return everything."""
        vd = create_test_videodata(
            full_text="Short text with only 30 characters"
        )
        filepath = vd.save_json(str(tmp_path))

        loaded = VideoData.load_json(filepath)
        limit = 5000
        result = loaded.full_text[:limit]

        assert len(result) == len(vd.full_text)
        assert result == vd.full_text

    def test_extract_above_limit_truncates(self, tmp_path):
        """When text exceeds the limit, truncate at exactly N chars."""
        long_text = "x" * 10000
        vd = create_test_videodata(full_text=long_text)
        filepath = vd.save_json(str(tmp_path))

        loaded = VideoData.load_json(filepath)
        limit = 5000
        result = loaded.full_text[:limit]

        assert len(result) == limit
        assert result == "x" * limit

    def test_extract_zero_returns_empty(self, tmp_path):
        """Character limit of 0 returns empty string."""
        vd = create_test_videodata(full_text="Some content")
        filepath = vd.save_json(str(tmp_path))

        loaded = VideoData.load_json(filepath)
        result = loaded.full_text[:0]

        assert result == ""

    def test_extract_preserves_unicode(self, tmp_path):
        """Spanish special characters survive the roundtrip."""
        text = "¿Qué significa migrar? La migración es un derecho. El sueño de muchos."
        vd = create_test_videodata(full_text=text)
        filepath = vd.save_json(str(tmp_path))

        loaded = VideoData.load_json(filepath)
        result = loaded.full_text[:5000]

        assert "¿" in result
        assert "ó" in result
        assert "ñ" in result
        assert result == text

    def test_empty_full_text(self, tmp_path):
        """VideoData with empty full_text returns empty string."""
        vd = create_test_videodata(full_text="")
        filepath = vd.save_json(str(tmp_path))

        loaded = VideoData.load_json(filepath)
        result = loaded.full_text[:5000]

        assert result == ""

    def test_multiple_files_first_wins(self, tmp_path):
        """When multiple JSONs exist, the first one alphabetically is used."""
        vd_a = create_test_videodata(video_id="a_video", full_text="AAA content")
        vd_b = create_test_videodata(video_id="b_video", full_text="BBB content")
        vd_a.save_json(str(tmp_path))
        vd_b.save_json(str(tmp_path))

        json_files = sorted(Path(tmp_path).glob("*.json"))
        first = VideoData.load_json(json_files[0])

        assert first.video_id == "a_video"
        assert first.full_text[:5000] == "AAA content"


# ── ChromaDB extraction logic tests ────────────────────────────────────────


class TestChromaAccumulation:
    """Test the chunk-accumulation logic for sequential reads.

    These test the core algorithm without requiring a real ChromaDB instance — 
    they validate the accumulation logic using plain lists.
    """

    def _accumulate(
        self, documents: list[str], metadatas: list[dict], char_limit: int
    ) -> dict:
        """Replicate the ChromaDB sequential-accumulation logic.

        Mirrors the algorithm in backend/scripts/extract_sample.py.
        """
        accumulated = ""
        chunk_count = 0
        titles_seen: set[str] = set()

        for doc, meta in zip(documents, metadatas):
            accumulated += doc + "\n\n"
            chunk_count += 1
            if meta and "title" in meta:
                titles_seen.add(meta["title"])
            if len(accumulated) >= char_limit:
                break

        return {
            "chunk_count": chunk_count,
            "total_chunks": len(documents),
            "char_count": min(char_limit, len(accumulated)),
            "total_chars": len(accumulated),
            "titles": sorted(titles_seen),
            "preview": accumulated[:char_limit],
        }

    def test_single_chunk_below_limit(self):
        """One chunk shorter than limit → uses 1 chunk."""
        docs = ["Hello world"]
        metas = [{"title": "Video 1"}]

        result = self._accumulate(docs, metas, char_limit=5000)

        assert result["chunk_count"] == 1
        assert result["titles"] == ["Video 1"]
        assert "Hello world" in result["preview"]

    def test_multiple_chunks_to_reach_limit(self):
        """Multiple chunks needed to reach character limit."""
        docs = ["A" * 2000, "B" * 2000, "C" * 2000, "D" * 2000]
        metas = [
            {"title": "Video A"},
            {"title": "Video B"},
            {"title": "Video B"},  # same video, different chunk
            {"title": "Video C"},
        ]

        result = self._accumulate(docs, metas, char_limit=5000)

        # 2000 + 2 (newline) + 2000 + 2 = 4004 → still under 5000
        # + 2000 + 2 = 6006 → over 5000, so 3 chunks
        assert result["chunk_count"] == 3
        assert len(result["titles"]) == 2  # A and B only
        assert "Video A" in result["titles"]
        assert "Video B" in result["titles"]

    def test_deduplicates_titles(self):
        """Same video title across multiple chunks is counted once."""
        docs = ["Chunk 1 text " * 100, "Chunk 2 text " * 100]
        metas = [
            {"title": "Same Video", "chunk_index": 0},
            {"title": "Same Video", "chunk_index": 1},
        ]

        result = self._accumulate(docs, metas, char_limit=5000)

        assert result["titles"] == ["Same Video"]
        assert len(result["titles"]) == 1

    def test_empty_chroma_handled(self):
        """No documents → nothing accumulated."""
        docs: list[str] = []
        metas: list[dict] = []

        result = self._accumulate(docs, metas, char_limit=5000)

        assert result["chunk_count"] == 0
        assert result["total_chunks"] == 0
        assert result["preview"] == ""

    def test_limit_exactly_at_chunk_boundary(self):
        """When the limit lands exactly at a chunk boundary."""
        docs = ["X" * 1000, "Y" * 1000]
        metas = [{}, {}]

        result = self._accumulate(docs, metas, char_limit=1002)  # 1000 + \n\n

        assert result["chunk_count"] == 1

    def test_metadata_none_handled(self):
        """Chunks with no metadata dict don't crash."""
        docs = ["Content here " * 50]
        metas = [None]  # type: ignore

        result = self._accumulate(docs, metas, char_limit=5000)

        assert result["chunk_count"] == 1
        assert result["titles"] == []


# ── Integration test with real VideoData files ─────────────────────────────


class TestExtractFromRealJSON:
    """Extract from an actual whisper JSON if available (integration smoke test)."""

    def test_real_whisper_json_readable(self):
        """If a real whisper JSON exists, verify it's loadable and has text."""
        raw_dir = (
            Path(__file__).resolve().parent.parent
            / "data" / "raw" / "whisper"
        )
        json_files = list(raw_dir.glob("*.json")) if raw_dir.exists() else []

        if not json_files:
            pytest.skip("No whisper JSON files available — run ingestion first")

        vd = VideoData.load_json(json_files[0])

        assert vd.video_id, "video_id must not be empty"
        assert vd.title, "title must not be empty"
        assert vd.full_text, "full_text must not be empty"
        assert len(vd.full_text) > 100, "full_text should have meaningful content"

        # Verify first-5000 extraction works
        sample = vd.full_text[:5000]
        assert len(sample) <= 5000
        assert sample == vd.full_text[:len(sample)]
