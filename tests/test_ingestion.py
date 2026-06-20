"""Unit tests for ingestion.py — VideoData, enrichment, and ingestion helpers."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "backend" / "core"))

from ingestion import _format_timestamp  # noqa: E402


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
