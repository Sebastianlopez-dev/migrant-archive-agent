"""Chat endpoint for the migrant-archive conversational API."""

from __future__ import annotations

import asyncio
import re
import sys
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from starlette.concurrency import run_in_threadpool

from backend.api.dependencies import get_agent
from backend.api.models import AskRequest, AskResponse, Source

# Ensure backend/agents/ is on sys.path so the agent module is importable
# without a pip-installed package (same pattern used in dependencies.py).
_AGENTS_DIR = str(Path(__file__).resolve().parent.parent.parent / "agents")
if _AGENTS_DIR not in sys.path:
    sys.path.insert(0, _AGENTS_DIR)

from agent import clear_session  # noqa: E402

router = APIRouter()


class SessionClearResponse(BaseModel):
    """Response for DELETE /api/session/{session_id}."""

    session_id: str = Field(..., description="The session that was cleared")
    cleared: bool = Field(..., description="Whether the session existed and was cleared")

# Matches an observation block produced by the search_transcripts tool:
#   [1] VIDEO_ID | Title (start–end)
#   Text content
_SOURCE_BLOCK_RE = re.compile(
    r"\[(\d+)\]\s+"                # [1]
    r"([^\n|]+?)\s*\|\s*"          # VIDEO_ID |
    r"([^(\n]+?)\s*\("             # Title (
    r"([^–)]+?)\s*–\s*"            # start –
    r"([^)]+?)\)\n"                # end )
    r"(.*?)"                        # text body
    r"(?=\n\n\[|\Z)",
    re.DOTALL,
)


def parse_sources(intermediate_steps: list) -> list[Source]:
    """Extract structured sources from agent intermediate steps.

    The agent returns ``intermediate_steps`` as a list of
    ``(action, observation)`` tuples.  Each observation string may contain
    one or more transcript blocks formatted by ``search_transcripts``.
    """
    sources: list[Source] = []
    if not intermediate_steps:
        return sources

    for step in intermediate_steps:
        if not step:
            continue

        observation = step[1] if isinstance(step, (list, tuple)) and len(step) > 1 else None
        if not isinstance(observation, str):
            continue

        for match in _SOURCE_BLOCK_RE.finditer(observation):
            _, video_id, title, start_time, end_time, text = match.groups()
            sources.append(
                Source(
                    video_id=video_id.strip(),
                    title=title.strip(),
                    start_time=start_time.strip(),
                    end_time=end_time.strip(),
                    text=text.strip(),
                )
            )

    return sources


@router.post("/ask", response_model=AskResponse)
async def ask(request: AskRequest, agent=Depends(get_agent)) -> AskResponse:
    """Answer a question using the migrant-archive agent."""
    try:
        result = await asyncio.wait_for(
            run_in_threadpool(
                agent.invoke,
                {"input": request.question},
                {"configurable": {"session_id": request.session_id}},
            ),
            timeout=90.0,
        )
    except asyncio.TimeoutError:
        raise HTTPException(
            status_code=504,
            detail="The agent took too long to respond. Try again with a simpler question.",
        ) from None
    except ValueError as exc:
        if "GEMINI_API_KEY" in str(exc):
            raise HTTPException(
                status_code=503,
                detail="Service unavailable: GEMINI_API_KEY not configured.",
            ) from exc
        raise

    answer = result.get("output", "")
    sources = parse_sources(result.get("intermediate_steps", []))
    return AskResponse(answer=answer, sources=sources)


@router.delete("/session/{session_id}", response_model=SessionClearResponse)
async def delete_session(session_id: str) -> SessionClearResponse:
    """Clear the chat history for a session, freeing memory."""
    was_cleared = clear_session(session_id)
    return SessionClearResponse(session_id=session_id, cleared=was_cleared)
