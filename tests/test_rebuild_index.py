"""Tests for rebuild_index.py — vector index builder.

Validates the standalone index builder that chunks, embeds, and stores
whisper JSON files into a fresh ChromaDB collection.
"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend" / "core"))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend" / "scripts"))

from tests.test_embedding import FakeEmbeddingProvider


class TestFindVideoFiles:
    """Video file discovery helper."""

    def test_returns_sorted_json_files(self, tmp_path):
        """Find all .json files in raw_dir and return them sorted."""
        from rebuild_index import find_video_files

        (tmp_path / "z_video.json").write_text("{}")
        (tmp_path / "a_video.json").write_text("{}")

        result = find_video_files(tmp_path)

        assert len(result) == 2
        assert [p.name for p in result] == ["a_video.json", "z_video.json"]

    def test_empty_dir_returns_empty_list(self, tmp_path):
        """An empty directory returns no files."""
        from rebuild_index import find_video_files

        assert find_video_files(tmp_path) == []

    def test_missing_dir_returns_empty_list(self):
        """A non-existent directory returns no files instead of crashing."""
        from rebuild_index import find_video_files

        assert find_video_files(Path("/does/not/exist")) == []


class TestBuildIndex:
    """Core index builder logic with a fake embedding provider."""

    def _make_video(self, video_id: str, raw_dir: Path) -> None:
        """Create a minimal VideoData JSON file for testing."""
        from ingestion import VideoData

        video = VideoData(
            video_id=video_id,
            title=f"Video {video_id}",
            description="Test description",
            transcript_segments=[
                {"text": "This is segment one.", "start": 0.0, "duration": 5.0},
                {"text": "This is segment two.", "start": 5.0, "duration": 5.0},
            ],
            full_text="This is segment one. This is segment two.",
            metadata={
                "id": video_id,
                "title": f"Video {video_id}",
                "upload_date": "20260101",
                "channel": "Test Channel",
            },
        )
        video.save_json(str(raw_dir))

    def test_build_index_creates_chunks(self, tmp_path):
        """Index builder stores chunks and returns a populated VectorStore."""
        from rebuild_index import build_index
        from core.vector_store import VectorStore

        raw_dir = tmp_path / "raw" / "whisper"
        chroma_dir = tmp_path / "chroma"
        raw_dir.mkdir(parents=True)

        self._make_video("vid_001", raw_dir)

        provider = FakeEmbeddingProvider(dimension=128)
        store = build_index(provider, raw_dir, chroma_dir)

        assert isinstance(store, VectorStore)
        assert store.count > 0

    def test_build_index_deletes_existing_collection(self, tmp_path):
        """Rebuilding wipes any previous collection."""
        from rebuild_index import build_index
        from core.vector_store import VectorStore

        raw_dir = tmp_path / "raw" / "whisper"
        chroma_dir = tmp_path / "chroma"
        raw_dir.mkdir(parents=True)

        self._make_video("vid_001", raw_dir)

        provider = FakeEmbeddingProvider(dimension=128)

        # First build
        build_index(provider, raw_dir, chroma_dir)

        # Add a second video and rebuild
        self._make_video("vid_002", raw_dir)
        store = build_index(provider, raw_dir, chroma_dir)

        # Both videos should be present in the fresh collection
        assert store.count > 0

    def test_build_index_no_videos_exits(self, tmp_path, capsys):
        """Missing video files triggers a helpful error and sys.exit(1)."""
        from rebuild_index import build_index

        raw_dir = tmp_path / "empty"
        chroma_dir = tmp_path / "chroma"
        raw_dir.mkdir()

        provider = FakeEmbeddingProvider(dimension=128)

        with pytest.raises(SystemExit) as exc_info:
            build_index(provider, raw_dir, chroma_dir)

        assert exc_info.value.code == 1
        captured = capsys.readouterr()
        assert "No whisper JSON files found" in captured.out
        assert "python backend/core/ingestion_audio.py" in captured.out


class TestCLI:
    """Command-line interface for rebuild_index.py."""

    def test_argparse_defaults(self):
        """Default directories point to the standard project layout."""
        from rebuild_index import parse_args

        args = parse_args([])

        assert args.raw_dir.endswith("data/raw/whisper")
        assert args.chroma_dir.endswith("data/chroma")

    def test_argparse_custom_dirs(self):
        """CLI overrides accept custom raw and chroma directories."""
        from rebuild_index import parse_args

        args = parse_args([
            "--raw-dir", "/custom/raw",
            "--chroma-dir", "/custom/chroma",
        ])

        assert args.raw_dir == "/custom/raw"
        assert args.chroma_dir == "/custom/chroma"
