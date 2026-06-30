"""Pydantic models for the chat API."""

from __future__ import annotations

from pydantic import BaseModel, Field, field_validator


class Source(BaseModel):
    """A single transcript source consumed by the agent."""

    video_id: str
    title: str
    start_time: str
    end_time: str
    text: str


ALLOWED_LANGUAGES = {"en", "es", "ca", "fr", "pt", "de"}


class AskRequest(BaseModel):
    """Body schema for POST /api/ask."""

    question: str = Field(..., min_length=1)
    session_id: str = Field(default="default", min_length=1)
    language: str = Field(default="en", min_length=2, max_length=5)

    @field_validator("language")
    @classmethod
    def validate_language(cls, v: str) -> str:
        if v not in ALLOWED_LANGUAGES:
            raise ValueError(
                f"Unsupported language code: {v}. Supported: {', '.join(sorted(ALLOWED_LANGUAGES))}."
            )
        return v


class AskResponse(BaseModel):
    """Response schema for POST /api/ask."""

    answer: str
    sources: list[Source]


class SessionClearResponse(BaseModel):
    """Response for DELETE /api/session/{session_id}."""

    session_id: str = Field(..., description="The session that was cleared")
    cleared: bool = Field(..., description="Whether the session existed and was cleared")


class TranscribeResponse(BaseModel):
    """Response for POST /api/transcribe."""

    text: str = Field(..., description="Transcribed text from the audio input")
