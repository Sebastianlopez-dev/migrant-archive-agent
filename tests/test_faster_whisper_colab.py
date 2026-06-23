"""Notebook-level validation for the faster-whisper Colab migration."""

import json
from pathlib import Path

import pytest


@pytest.fixture
def notebook():
    """Load the Colab notebook as a dict."""
    notebook_path = Path(__file__).resolve().parent.parent / "notebooks" / "transcribe_video_colab.ipynb"
    return json.loads(notebook_path.read_text(encoding="utf-8"))


def _cell_sources(notebook):
    """Yield (cell_index, source_string) for every cell."""
    for idx, cell in enumerate(notebook["cells"]):
        source = "".join(cell["source"])
        yield idx, source


def _find_cell_by_heading(notebook, heading):
    """Return the index of the markdown cell whose first line starts with heading."""
    for idx, cell in enumerate(notebook["cells"]):
        if cell["cell_type"] != "markdown":
            continue
        source = "".join(cell["source"]).strip()
        if source.startswith(heading):
            return idx
    raise ValueError(f"Heading not found: {heading}")


class TestSectionOneDependencies:
    """Section 1 installs faster-whisper and keeps required tooling."""

    def test_installs_faster_whisper_not_whisperx(self, notebook):
        section1_idx = _find_cell_by_heading(notebook, "## 1. Install Dependencies")
        code_idx = section1_idx + 1
        source = "".join(notebook["cells"][code_idx]["source"])

        assert "faster-whisper" in source
        assert "whisperx" not in source
        assert 'transformers==4.48.3' not in source
        assert "--force-reinstall numpy" not in source
        assert "--force-reinstall scipy" not in source

    def test_keeps_required_tooling(self, notebook):
        section1_idx = _find_cell_by_heading(notebook, "## 1. Install Dependencies")
        code_idx = section1_idx + 1
        source = "".join(notebook["cells"][code_idx]["source"])

        assert "yt-dlp" in source
        assert "ffmpeg" in source
        assert "curl" in source
        assert "nodesource" in source.lower()


class TestSectionFiveHuggingFaceToken:
    """Section 5 no longer requires an HF token."""

    def test_section_notes_token_not_needed(self, notebook):
        section5_idx = _find_cell_by_heading(notebook, "## 5.")
        source = "".join(notebook["cells"][section5_idx]["source"])

        assert "not needed" in source.lower() or "skip" in source.lower()


class TestSectionSevenTranscription:
    """Section 7 imports faster-whisper and drops HF token plumbing."""

    def test_imports_faster_whisper_not_whisperx(self, notebook):
        section7_idx = _find_cell_by_heading(notebook, "## 7. Run Transcription")
        code_idx = section7_idx + 1
        source = "".join(notebook["cells"][code_idx]["source"])

        assert "from faster_whisper import WhisperModel" in source
        assert "whisperx" not in source

    def test_no_hf_token_environment_read(self, notebook):
        section7_idx = _find_cell_by_heading(notebook, "## 7. Run Transcription")
        code_idx = section7_idx + 1
        source = "".join(notebook["cells"][code_idx]["source"])

        assert 'os.environ.get("HF_TOKEN")' not in source
        assert "hf_token" not in source

    def test_keeps_audio_verification_and_videodata_output(self, notebook):
        section7_idx = _find_cell_by_heading(notebook, "## 7. Run Transcription")
        code_idx = section7_idx + 1
        source = "".join(notebook["cells"][code_idx]["source"])

        assert "audio_path.exists()" in source
        assert "_build_videodata" in source
        assert "save_json" in source


class TestNotebookJsonValidity:
    """Basic structural guarantees."""

    def test_valid_nbformat(self, notebook):
        assert notebook["nbformat"] == 4
        assert "cells" in notebook
        assert len(notebook["cells"]) > 0
