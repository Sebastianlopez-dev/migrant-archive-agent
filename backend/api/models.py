"""Pydantic models for the chat API."""

from __future__ import annotations

from pydantic import BaseModel, Field


class Source(BaseModel):
    """A single transcript source consumed by the agent."""

    video_id: str
    title: str
    start_time: str
    end_time: str
    text: str


class AskRequest(BaseModel):
    """Body schema for POST /api/ask."""

    question: str = Field(..., min_length=1)


class AskResponse(BaseModel):
    """Response schema for POST /api/ask."""

    answer: str
    sources: list[Source]
