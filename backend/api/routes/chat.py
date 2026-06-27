"""Chat endpoint for the migrant-archive conversational API."""

from __future__ import annotations

import asyncio
import re

from fastapi import APIRouter, Depends, HTTPException
from starlette.concurrency import run_in_threadpool

from backend.api.dependencies import get_agent
from backend.api.models import AskRequest, AskResponse, SessionClearResponse, Source

# dependencies.py already configures sys.path for backend/agents/ so bare
# imports from the agent module work without repeating the path setup here.
from agent import clear_session  # noqa: E402

router = APIRouter()


# Matches an observation block produced by the search_transcripts tool:
#   [1] Title [Speaker] (start–end) | VIDEO_ID
#   Text content
_SOURCE_BLOCK_RE = re.compile(
    r"\[(\d+)\]\s+"                # [1]
    r"([^\n]+?)\s*\("              # Title [Speaker] (
    r"([^–)]+?)\s*–\s*"            # start –
    r"([^)]+?)\)\s*\|\s*"           # end ) |
    r"([^\n]+?)\n"                  # VIDEO_ID
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
            _, title, start_time, end_time, video_id, text = match.groups()
            # Strip trailing [Speaker] tag that tools.py appends to the header.
            title = re.sub(r"\s*\[[^\]]+\]$", "", title.strip())
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
