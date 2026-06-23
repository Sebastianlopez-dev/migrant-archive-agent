"""Tests for faster-whisper backend in ingestion_audio.py.

Replaces the previous whisperx-based test suite.
"""

import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest

# ── path setup ───────────────────────────────────────────────────────────────
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend/core"))

# ── fake missing deps so ingestion_audio can be imported ─────────────────────
if "faster_whisper" not in sys.modules:
    _fake_fw = type(sys)("faster_whisper")
    _fake_fw.WhisperModel = MagicMock()
    sys.modules["faster_whisper"] = _fake_fw

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
from core.ingestion import _build_videodata  # noqa: E402
from core.ingestion_audio import _compute_type_for, _transcribe_audio  # noqa: E402


# ── helpers ──────────────────────────────────────────────────────────────────


class _FakeSegment:
    """Minimal faster-whisper Segment stand-in."""

    def __init__(self, text: str, start: float, end: float):
        self.text = text
        self.start = start
        self.end = end


def _fake_model_factory(segments):
    """Return a callable that builds a mocked WhisperModel."""

    def _factory(*args, **kwargs):
        model = MagicMock()
        info = MagicMock()
        model.transcribe.return_value = (segments, info)
        return model

    return _factory


# ── compute type selection ───────────────────────────────────────────────────


class TestComputeTypeFor:
    """Device → compute_type mapping."""

    def test_cuda_uses_float16(self):
        assert _compute_type_for("cuda") == "float16"

    def test_cpu_uses_int8(self):
        assert _compute_type_for("cpu") == "int8"


# ── transcription backend ────────────────────────────────────────────────────


class TestTranscribeAudio:
    """_transcribe_audio uses faster-whisper and returns standard segments."""

    def test_returns_expected_segment_shape(self, monkeypatch):
        """Each segment must contain text, start, duration, and speaker."""
        fake_segments = [_FakeSegment("hola mundo", 0.0, 1.5)]
        monkeypatch.setattr(
            "core.ingestion_audio.WhisperModel",
            _fake_model_factory(fake_segments),
        )

        segments = _transcribe_audio("dummy.mp3", language="es")

        assert len(segments) == 1
        seg = segments[0]
        assert seg["text"] == "hola mundo"
        assert seg["start"] == 0.0
        assert seg["duration"] == 1.5
        assert seg["speaker"] == "UNKNOWN"

    def test_passes_language_model_size_and_device(self, monkeypatch):
        """WhisperModel init and transcribe receive the right arguments."""
        fake_segments = [_FakeSegment("hello", 0.0, 1.0)]
        captured = {}

        def factory(*args, **kwargs):
            captured["model_init"] = (args, kwargs)
            model = MagicMock()
            info = MagicMock()

            def transcribe(audio, **t_kwargs):
                captured["transcribe"] = {"audio": audio, "kwargs": t_kwargs}
                return (fake_segments, info)

            model.transcribe.side_effect = transcribe
            return model

        monkeypatch.setattr("core.ingestion_audio.WhisperModel", factory)

        _transcribe_audio(
            "audio.mp3",
            language="es",
            model_size="large-v3",
            device="cuda",
        )

        assert captured["model_init"][0][0] == "large-v3"
        assert captured["model_init"][1]["device"] == "cuda"
        assert captured["model_init"][1]["compute_type"] == "float16"
        assert captured["transcribe"]["audio"] == "audio.mp3"
        assert captured["transcribe"]["kwargs"]["language"] == "es"

    def test_cpu_uses_int8_compute(self, monkeypatch):
        """CPU inference uses int8 quantization."""
        captured = {}

        def factory(*args, **kwargs):
            captured["kwargs"] = kwargs
            model = MagicMock()
            model.transcribe.return_value = ([], MagicMock())
            return model

        monkeypatch.setattr("core.ingestion_audio.WhisperModel", factory)
        _transcribe_audio("audio.mp3", language="en", device="cpu")

        assert captured["kwargs"]["compute_type"] == "int8"

    def test_auto_device_is_detected(self, monkeypatch):
        """device='auto' resolves via _detect_device before model init."""
        captured = {}

        def factory(*args, **kwargs):
            captured["kwargs"] = kwargs
            model = MagicMock()
            model.transcribe.return_value = ([], MagicMock())
            return model

        monkeypatch.setattr("core.ingestion_audio.WhisperModel", factory)
        monkeypatch.setattr("core.ingestion_audio._detect_device", lambda: "cuda")

        _transcribe_audio("audio.mp3", language="es", device="auto")

        assert captured["kwargs"]["device"] == "cuda"

    def test_text_is_stripped(self, monkeypatch):
        """Leading/trailing whitespace is removed from segment text."""
        fake_segments = [_FakeSegment("  spaced text  ", 0.0, 1.0)]
        monkeypatch.setattr(
            "core.ingestion_audio.WhisperModel",
            _fake_model_factory(fake_segments),
        )

        segments = _transcribe_audio("dummy.mp3", language="es")

        assert segments[0]["text"] == "spaced text"


# ── downstream compatibility ─────────────────────────────────────────────────


class TestVideoDataCompatibility:
    """faster-whisper segments must feed VideoData unchanged."""

    def test_videodata_json_shape_unchanged(self, monkeypatch):
        """Segment output still produces the same VideoData.to_dict() structure."""
        fake_segments = [_FakeSegment("hello world", 0.0, 1.2)]
        monkeypatch.setattr(
            "core.ingestion_audio.WhisperModel",
            _fake_model_factory(fake_segments),
        )

        segments = _transcribe_audio("audio.mp3", language="es")
        info = {"id": "vid1", "title": "Test", "description": "Desc"}
        vd = _build_videodata(info, segments)
        data = vd.to_dict()

        assert data["video_id"] == "vid1"
        assert data["title"] == "Test"
        assert data["transcript_segments"] == segments
        assert data["transcript_segments"][0]["speaker"] == "UNKNOWN"
