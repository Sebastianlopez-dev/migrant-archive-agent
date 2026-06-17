"""RED tests for WhisperX migration (PR 1).

These tests define the expected behaviour after the faster-whisper → WhisperX
migration.  They WILL FAIL until PR 2 implements the production code.
"""

import inspect
import json
import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest

# ── path setup ───────────────────────────────────────────────────────────────
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend/core"))

# ── fake missing deps so ingestion_audio can be imported ─────────────────────
if "whisperx" not in sys.modules:
    _fake_wx = type(sys)("whisperx")
    _fake_wx.load_model = MagicMock()
    _fake_wx.load_align_model = MagicMock()
    _fake_wx.align = MagicMock()
    _fake_wx.DiarizationPipeline = MagicMock()
    _fake_wx.load_audio = MagicMock()
    _fake_wx.assign_word_speakers = MagicMock()
    sys.modules["whisperx"] = _fake_wx

if "yt_dlp" not in sys.modules:
    sys.modules["yt_dlp"] = MagicMock()

# ── imports ──────────────────────────────────────────────────────────────────
from core.ingestion import VideoData
from core.ingestion_audio import _transcribe_audio, extract_single_video
from core.ingestion_colab import extract_single_video_colab


# ── helpers ──────────────────────────────────────────────────────────────────


def _fake_wx_pipeline(*args, **kwargs):
    """Mock the WhisperX 3-step pipeline (load_model, align, diarise)."""
    # Step 1: transcribe returns a mock model
    fake_model = MagicMock()
    fake_model.transcribe.return_value = {
        "segments": [
            {"text": "hola mundo", "start": 0.0, "end": 1.5}
        ]
    }
    return fake_model


def _fake_align_model(*args, **kwargs):
    """Mock whisperx.load_align_model — returns (model, metadata)."""
    return (MagicMock(), MagicMock())


def _fake_align(segments, *args, **kwargs):
    """Mock whisperx.align — returns dict with same segments."""
    return {"segments": segments}


def _fake_diarize_pipeline(*args, **kwargs):
    """Mock DiarizationPipeline — returns segments with speaker labels."""
    fake_pipeline = MagicMock()
    fake_pipeline.__call__ = MagicMock(return_value=[
        {"speaker": "SPEAKER_00", "start": 0.0, "end": 1.5}
    ])
    return fake_pipeline


def _fake_assign_word_speakers(diarize_segments, result, *args, **kwargs):
    """Mock assign_word_speakers — inject speaker into segments."""
    result["segments"][0]["speaker"] = "SPEAKER_00"
    return result


# ── 1.2: _transcribe_audio returns segments with speaker field ───────────────


class TestTranscribeAudioShape:
    """WhisperX segments must include a 'speaker' key."""

    def test_segment_includes_speaker(self, monkeypatch):
        """GREEN: each segment dict must contain 'speaker'."""
        monkeypatch.setattr(
            "core.ingestion_audio.whisperx.load_model",
            _fake_wx_pipeline,
        )
        monkeypatch.setattr(
            "core.ingestion_audio.whisperx.load_align_model",
            _fake_align_model,
        )
        monkeypatch.setattr(
            "core.ingestion_audio.whisperx.align",
            _fake_align,
        )

        segments = _transcribe_audio("dummy.mp3", language="es")

        assert len(segments) == 1
        assert "speaker" in segments[0], "Segment missing 'speaker' field"


# ── 1.3: hf_token=None → speaker == UNKNOWN ─────────────────────────────────


class TestSpeakerDefault:
    """Without an HF token, speaker diarisation is skipped."""

    def test_no_token_speakers_are_unknown(self, monkeypatch):
        """GREEN: every segment speaker must be 'UNKNOWN' when hf_token is None."""
        monkeypatch.setattr(
            "core.ingestion_audio.whisperx.load_model",
            _fake_wx_pipeline,
        )
        monkeypatch.setattr(
            "core.ingestion_audio.whisperx.load_align_model",
            _fake_align_model,
        )
        monkeypatch.setattr(
            "core.ingestion_audio.whisperx.align",
            _fake_align,
        )

        # PR 2 added the hf_token parameter; calling it now should be GREEN.
        segments = _transcribe_audio("dummy.mp3", language="es", hf_token=None)

        assert all(seg.get("speaker") == "UNKNOWN" for seg in segments)


# ── 1.4: extract_single_video accepts hf_token ───────────────────────────────


class TestExtractSingleVideoSignature:
    """extract_single_video must accept an optional hf_token parameter."""

    def test_accepts_hf_token(self):
        """RED: signature must include hf_token: str | None = None."""
        sig = inspect.signature(extract_single_video)
        assert "hf_token" in sig.parameters, "Missing hf_token parameter"


# ── 1.5: backward compat — old JSON without speaker loads cleanly ────────────


class TestLoadPreMigrationJSON:
    """Pre-migration JSON (no speaker key) must still load."""

    def test_loads_old_format(self, tmp_path):
        """Approval test: old-format JSON loads into VideoData without error."""
        old_data = {
            "video_id": "old_vid_001",
            "title": "Old Video",
            "description": "Before speaker diarisation",
            "transcript_segments": [
                {"text": "segment one", "start": 0.0, "duration": 5.0},
                {"text": "segment two", "start": 5.0, "duration": 3.5},
            ],
            "full_text": "segment one segment two",
            "metadata": {"id": "old_vid_001"},
        }
        filepath = tmp_path / "old_vid_001.json"
        filepath.write_text(json.dumps(old_data), encoding="utf-8")

        vd = VideoData.load_json(filepath)

        assert vd.video_id == "old_vid_001"
        assert len(vd.transcript_segments) == 2
        assert "speaker" not in vd.transcript_segments[0]


# ── 1.6: extract_single_video_colab accepts and forwards hf_token ────────────


class TestColabWrapperSignature:
    """extract_single_video_colab must accept and forward hf_token."""

    def test_accepts_hf_token(self):
        """RED: signature must include hf_token: str | None = None."""
        sig = inspect.signature(extract_single_video_colab)
        assert "hf_token" in sig.parameters, "Missing hf_token parameter"

    def test_forwards_hf_token(self, monkeypatch):
        """RED: hf_token must be passed through to extract_single_video."""
        captured = {}

        def mock_extract(*args, **kwargs):
            captured["hf_token"] = kwargs.get("hf_token")
            return MagicMock()

        monkeypatch.setattr(
            "core.ingestion_colab.extract_single_video",
            mock_extract,
        )

        extract_single_video_colab(
            "https://youtube.com/watch?v=dummy",
            hf_token="tok_123",
        )
        assert captured.get("hf_token") == "tok_123"
