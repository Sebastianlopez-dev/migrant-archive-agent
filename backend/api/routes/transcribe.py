"""Voice transcription endpoint using faster-whisper on-device.

Accepts an audio blob from the browser (via MediaRecorder), runs local
faster-whisper transcription, and returns the text.  No cloud APIs are
involved — works in every browser including Brave and Firefox.

The whisper model is loaded once on first use.  For production, call
``_preload_model()`` at server startup so the first request is fast.
"""

from __future__ import annotations

import logging
import tempfile
from pathlib import Path

from fastapi import APIRouter, File, HTTPException, UploadFile

from backend.api.models import TranscribeResponse

logger = logging.getLogger(__name__)

router = APIRouter()

_MODEL_SIZE = "tiny"
_MODEL_DEVICE = "cpu"
_MODEL_COMPUTE = "int8"

_whisper_model = None


def _get_whisper():
    """Load the faster-whisper model once and reuse it across requests."""
    global _whisper_model
    if _whisper_model is None:
        from faster_whisper import WhisperModel

        _whisper_model = WhisperModel(
            _MODEL_SIZE, device=_MODEL_DEVICE, compute_type=_MODEL_COMPUTE
        )
        logger.info("faster-whisper model loaded (size=%s)", _MODEL_SIZE)
    return _whisper_model


def preload_model() -> bool:
    """Preload the whisper model synchronously.  Call at server startup.

    Returns True if the model loaded, False otherwise.
    """
    try:
        _get_whisper()
        return True
    except Exception as exc:
        logger.warning("faster-whisper model could not be preloaded: %s", exc)
        return False


@router.post("/transcribe", response_model=TranscribeResponse)
async def transcribe(audio: UploadFile = File(...)) -> TranscribeResponse:
    """Transcribe an audio recording to text.

    The audio is expected as a multipart file upload (typically webm or
    wav from MediaRecorder).  faster-whisper runs locally — no cloud
    dependency.
    """
    try:
        _get_whisper()
    except Exception as exc:
        logger.warning("faster-whisper model could not be loaded: %s", exc)
        raise HTTPException(
            status_code=503,
            detail="Transcription service unavailable — model failed to load.",
        ) from exc

    if not audio.filename:
        raise HTTPException(status_code=400, detail="No audio file provided.")

    suffix = Path(audio.filename).suffix or ".webm"

    try:
        contents = await audio.read()
    except Exception:
        raise HTTPException(status_code=400, detail="Could not read audio file.") from None

    if not contents:
        raise HTTPException(status_code=400, detail="Empty audio file.")

    tmp = tempfile.NamedTemporaryFile(suffix=suffix, delete=False)
    try:
        tmp.write(contents)
        tmp.close()

        model = _get_whisper()
        segments, _info = model.transcribe(
            tmp.name, language="es", beam_size=5
        )
        text = " ".join(seg.text.strip() for seg in segments)

    except Exception as exc:
        logger.exception("Transcription failed")
        raise HTTPException(
            status_code=500,
            detail=f"Transcription failed: {exc}",
        ) from exc
    finally:
        Path(tmp.name).unlink(missing_ok=True)

    if not text:
        raise HTTPException(
            status_code=422, detail="No speech detected in the recording."
        )

    return TranscribeResponse(text=text)
