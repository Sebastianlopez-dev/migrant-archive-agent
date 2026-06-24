"""Chat endpoint for the migrant-archive conversational API."""

from __future__ import annotations

import re

from fastapi import APIRouter, Depends, HTTPException
from starlette.concurrency import run_in_threadpool

from backend.api.dependencies import get_agent
from backend.api.models import AskRequest, AskResponse, Source

router = APIRouter()

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
        result = await run_in_threadpool(agent.invoke, {"input": request.question})
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
