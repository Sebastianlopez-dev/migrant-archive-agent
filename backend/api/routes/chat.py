"""Chat endpoint for the migrant-archive conversational API."""

from __future__ import annotations

import asyncio
import html as _html
import re

from fastapi import APIRouter, Depends, HTTPException
from starlette.concurrency import run_in_threadpool

from backend.api.dependencies import get_agent
from backend.api.models import AskRequest, AskResponse, SessionClearResponse, Source

# dependencies.py already configures sys.path for backend/agents/ so bare
# imports from the agent module work without repeating the path setup here.
from agent import clear_session  # noqa: E402

router = APIRouter()


def _build_youtube_url(video_id: str, start_time: str) -> str:
    """Build a YouTube watch URL with an optional timestamp.

    ``start_time`` may be ``"HH:MM:SS"``, ``"MM:SS"``, or bare seconds.
    """
    base = f"https://www.youtube.com/watch?v={video_id}"
    seconds = _parse_time_to_seconds(start_time)
    return f"{base}&t={seconds}" if seconds > 0 else base


def _parse_time_to_seconds(time_str: str) -> int:
    parts = time_str.strip().split(":")
    try:
        nums = [int(p) for p in parts]
    except ValueError:
        return 0
    if len(nums) == 3:
        return nums[0] * 3600 + nums[1] * 60 + nums[2]
    if len(nums) == 2:
        return nums[0] * 60 + nums[1]
    return nums[0] if nums else 0


def linkify_answer(answer: str, sources: list[Source]) -> str:
    """Replace video-id references in the answer with clickable YouTube links.

    The link text is the full URL so the user sees exactly where they are
    going.  The surrounding text is HTML-escaped; only the generated
    ``<a>`` tags are injected as raw HTML.
    """
    escaped = _html.escape(answer)
    seen: set[str] = set()
    for source in sources:
        if source.video_id in seen:
            continue
        seen.add(source.video_id)
        vid = re.escape(source.video_id)
        url = _build_youtube_url(source.video_id, source.start_time)
        link_html = (
            f'<a href="{url}" target="_blank" '
            f'rel="noopener noreferrer">{url}</a>'
        )
        # Match video_id (optionally followed by &amp;t=N) but NOT when
        # it already sits inside an injected YouTube URL (watch?v= or /).
        escaped = re.sub(
            rf"(?<!v=)(?<!/)\b{vid}(?:&amp;t=\d+)?\b",
            link_html,
            escaped,
        )
    return escaped


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
    answer = linkify_answer(answer, sources)
    return AskResponse(answer=answer, sources=sources)


@router.delete("/session/{session_id}", response_model=SessionClearResponse)
async def delete_session(session_id: str) -> SessionClearResponse:
    """Clear the chat history for a session, freeing memory."""
    was_cleared = clear_session(session_id)
    return SessionClearResponse(session_id=session_id, cleared=was_cleared)
