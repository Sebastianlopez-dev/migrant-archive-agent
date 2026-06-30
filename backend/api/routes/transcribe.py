"""Voice transcription endpoint using Groq Whisper API.

Accepts an audio blob from the browser (via MediaRecorder) and forwards it
directly to Groq's hosted whisper-large-v3-turbo model. No filesystem writes
or temporary files are used. This is the sole voice transcription path for
the chat widget (replaces the former dual-path Web Speech API + MediaRecorder approach).
"""

from __future__ import annotations

import asyncio
import logging
import os

from fastapi import APIRouter, File, HTTPException, UploadFile
from groq import AsyncGroq, AuthenticationError, BadRequestError, RateLimitError

from backend.api.models import ALLOWED_LANGUAGES, TranscribeResponse

logger = logging.getLogger(__name__)

router = APIRouter()

_client: AsyncGroq | None = None


def _get_client() -> AsyncGroq:
    """Return a cached Groq client, creating one on first call."""
    global _client
    if _client is None:
        _client = AsyncGroq(api_key=os.getenv("GROQ_API_KEY"))
    return _client


_GROQ_MODEL = "whisper-large-v3-turbo"
_GROQ_RESPONSE_FORMAT = "json"


@router.post("/transcribe", response_model=TranscribeResponse)
async def transcribe(audio: UploadFile = File(...), language: str | None = None) -> TranscribeResponse:
    """Transcribe an audio recording to text.

    The audio is expected as a multipart file upload (webm from Chrome/Firefox
    or mp4 from Safari). Audio bytes are forwarded to Groq without writing to
    disk.
    """
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        logger.warning("GROQ_API_KEY not configured")
        raise HTTPException(
            status_code=503,
            detail="Transcription service unavailable — GROQ_API_KEY not configured.",
        )

    if not audio.filename:
        raise HTTPException(status_code=400, detail="No audio file provided.")

    try:
        contents = await audio.read()
    except Exception as exc:
        raise HTTPException(status_code=400, detail="Could not read audio file.") from exc

    if not contents:
        raise HTTPException(status_code=400, detail="Empty audio file.")

    if language is not None and language not in ALLOWED_LANGUAGES:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported language code: {language}. Supported: {', '.join(sorted(ALLOWED_LANGUAGES))}.",
        )

    _MAX_AUDIO_BYTES = 25 * 1024 * 1024  # 25 MB
    if len(contents) > _MAX_AUDIO_BYTES:
        raise HTTPException(
            status_code=413,
            detail="Audio file too large (max 25 MB).",
        )

    try:
        client = _get_client()
        transcription_kwargs = {
            "file": (audio.filename, contents),
            "model": _GROQ_MODEL,
            "response_format": _GROQ_RESPONSE_FORMAT,
        }
        if language:
            transcription_kwargs["language"] = language
        transcription = await asyncio.wait_for(
            client.audio.transcriptions.create(**transcription_kwargs),
            timeout=30.0,
        )
        text = transcription.text.strip() if transcription.text else ""
    except asyncio.TimeoutError as exc:
        logger.warning("Groq transcription request timed out")
        raise HTTPException(
            status_code=504,
            detail="Transcription service timed out — please try again.",
        ) from exc
    except RateLimitError as exc:
        logger.warning("Groq rate limit exceeded: %s", exc)
        raise HTTPException(
            status_code=429,
            detail="Transcription rate limit exceeded — try again later.",
        ) from exc
    except AuthenticationError as exc:
        logger.warning("Groq authentication failed: %s", exc)
        raise HTTPException(
            status_code=503,
            detail="Transcription service unavailable — GROQ_API_KEY invalid.",
        ) from exc
    except BadRequestError as exc:
        logger.warning("Groq bad request: %s", exc)
        raise HTTPException(
            status_code=400,
            detail=f"Transcription request invalid: {exc}",
        ) from exc
    except Exception as exc:
        logger.warning("Groq transcription request failed: %s", exc)
        raise HTTPException(
            status_code=503,
            detail="Transcription service unavailable — Groq request failed.",
        ) from exc

    if not text:
        raise HTTPException(
            status_code=422, detail="No speech detected in the recording."
        )

    return TranscribeResponse(text=text)
