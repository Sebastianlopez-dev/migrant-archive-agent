"""Request-scoped dependencies for the chat API."""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from langchain_classic.agents import AgentExecutor


# The agent module expects `tools` and `core` to be on sys.path.  Insert the
# backend sub-directories before importing so the dependency works regardless
# of how the API process is started.
_BACKEND_DIR = Path(__file__).resolve().parent.parent
for _sub in ("agents", "core"):
    _path = str(_BACKEND_DIR / _sub)
    if _path not in sys.path:
        sys.path.insert(0, _path)

from agent import create_agent  # noqa: E402


def get_agent() -> AgentExecutor:
    """Return a fresh AgentExecutor for the current request.

    A new instance is created every time so that VectorStore and Gemini
    clients are not shared across concurrent requests.

    Raises:
        fastapi.HTTPException: 503 Service Unavailable if ``GEMINI_API_KEY``
            is not configured.
    """
    if not os.getenv("GEMINI_API_KEY"):
        from fastapi import HTTPException

        raise HTTPException(
            status_code=503,
            detail="Service unavailable: GEMINI_API_KEY not configured.",
        )
    return create_agent()
