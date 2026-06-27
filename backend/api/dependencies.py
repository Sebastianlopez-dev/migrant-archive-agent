"""Request-scoped dependencies for the chat API."""

from __future__ import annotations

import os
import sys
from pathlib import Path

from fastapi import HTTPException

if hasattr(sys, "_called_from_test"):
    # Allow test teardown to reset the cached agent.
    pass

# The agent module expects `tools` and `core` to be on sys.path.  Insert the
# backend sub-directories before importing so the dependency works regardless
# of how the API process is started.
_BACKEND_DIR = Path(__file__).resolve().parent.parent
for _sub in ("agents", "core"):
    _path = str(_BACKEND_DIR / _sub)
    if _path not in sys.path:
        sys.path.insert(0, _path)

from agent import create_agent  # noqa: E402


_agent = None


def get_agent():
    """Return the cached history-wrapped agent, creating it on first call.

    The agent (Chroma connection, LLM client, embedding function, and
    AgentExecutor) is created once and reused across requests.  Session
    isolation is handled by ``RunnableWithMessageHistory`` via the
    ``session_id`` config key — each caller receives its own conversation
    history automatically.

    Raises:
        fastapi.HTTPException: 503 if ``GEMINI_API_KEY`` is not configured.
    """
    global _agent

    if not os.getenv("GEMINI_API_KEY"):
        raise HTTPException(
            status_code=503,
            detail="Service unavailable: GEMINI_API_KEY not configured.",
        )

    if _agent is None:
        _agent = create_agent()
    return _agent
