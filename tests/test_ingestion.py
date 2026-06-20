"""Unit tests for ingestion.py — VideoData, enrichment, and ingestion helpers."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "backend" / "core"))

from ingestion import _format_timestamp, VideoData  # noqa: E402


# ---------------------------------------------------------------------------
# Timestamp formatting
# ---------------------------------------------------------------------------

class TestFormatTimestamp:
    """Module-private timestamp helper."""

    def test_sub_hour_format(self):
        """Returns [MM:SS] when use_hours=False."""
        assert _format_timestamp(65, False) == "[01:05]"

    def test_hour_plus_format(self):
        """Returns [HH:MM:SS] when use_hours=True."""
        assert _format_timestamp(3661, True) == "[01:01:01]"

    def test_zero_seconds(self):
        """Zero seconds formats cleanly."""
        assert _format_timestamp(0, False) == "[00:00]"

    def test_fractional_seconds_truncated(self):
        """Fractional seconds are truncated, not rounded."""
        assert _format_timestamp(65.9, False) == "[01:05]"


# ---------------------------------------------------------------------------
# VideoData enriched text
# ---------------------------------------------------------------------------

class TestVideoDataEnrichedText:
    """VideoData.enriched_text() formatting."""

    def test_sub_hour_format(self):
        """Segments under one hour use [MM:SS]."""
        vd = VideoData(
            video_id="vid1",
            title="Interview",
            description="Migration story",
            transcript_segments=[
                {"text": "Hello", "start": 0, "duration": 1},
                {"text": "World", "start": 65, "duration": 1},
            ],
            full_text="Hello World",
            metadata={"duration": 70},
        )
        result = vd.enriched_text()
        assert "Title: Interview" in result
        assert "Description: Migration story" in result
        assert "[00:00] Hello" in result
        assert "[01:05] World" in result

    def test_hour_plus_format(self):
        """Segments one hour or longer use [HH:MM:SS]."""
        vd = VideoData(
            video_id="vid2",
            title="Long Interview",
            description="Long migration story",
            transcript_segments=[
                {"text": "Start", "start": 0, "duration": 1},
                {"text": "Late", "start": 3661, "duration": 1},
            ],
            full_text="Start Late",
            metadata={"duration": 3700},
        )
        result = vd.enriched_text()
        assert "[00:00:00] Start" in result
        assert "[01:01:01] Late" in result

    def test_empty_segments(self):
        """Empty segments still include title and description."""
        vd = VideoData(
            video_id="vid3",
            title="Empty",
            description="No segments",
            transcript_segments=[],
            full_text="",
            metadata={"duration": 0},
        )
        result = vd.enriched_text()
        assert "Title: Empty" in result
        assert "Description: No segments" in result
        assert "[" not in result  # no timestamp markers when there are no segments
