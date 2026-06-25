"""Native tool-calling agent factory for the migrant-archive assistant.

`create_agent()` builds a Spanish-speaking agent backed by
`create_tool_calling_agent`, `AgentExecutor`, and per-session message history
via `RunnableWithMessageHistory` + `InMemoryChatMessageHistory`.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

# Allow imports from backend/ and backend/core/ when this module is imported
# directly (e.g. from tests or scripts).
_BACKEND_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_BACKEND_DIR))
sys.path.insert(0, str(_BACKEND_DIR / "core"))

from langchain_classic.agents import AgentExecutor, create_tool_calling_agent
from langchain_core.chat_history import InMemoryChatMessageHistory
from langchain_core.messages import BaseMessage
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.runnables.history import RunnableWithMessageHistory
from langchain_google_genai import ChatGoogleGenerativeAI

from tools import make_get_video_info, make_list_videos, make_search_transcripts
from core.embedding_gemini import GeminiEmbeddingProvider
from core.vector_store import VectorStore


SYSTEM_PROMPT = (
    "You are Cero, an assistant that answers questions in Spanish about archived "
    "migrant testimonies. You have three tools: list_videos, get_video_info, "
    "and search_transcripts. "
    "If a query is vague or a bare proper name (e.g. 'Lina'), use list_videos "
    "or get_video_info to disambiguate, or rewrite the query into a descriptive "
    "English sentence of at least 3-5 words before calling search_transcripts. "
    "search_transcripts supports optional year and channel filters when the user "
    "wants to narrow results by upload year or source channel. "
    "When presenting multiple results, steps, or examples, always use a numbered "
    "or bulleted list. Always respond in Spanish, cite the video and time range "
    "when possible, and do not invent information. "
    "When a tool returns a 'channel' field, always include it (e.g. 'Canal: "
    "Plataforma Cero'). When a tool returns a 'speakers' field, always list the "
    "speakers as 'Ponentes:' in the response. Use the structured fields directly "
    "— do not re-parse the description text to find names that are already "
    "provided in the 'speakers' field."
)

# Maximum number of messages to keep in the sliding window.
# 10 messages = 5 complete Q&A exchanges (user + assistant).
MAX_HISTORY_MESSAGES: int = 10


class BoundedChatMessageHistory(InMemoryChatMessageHistory):
    """Chat history that keeps only the last `max_messages` messages.

    When the buffer exceeds `max_messages`, the oldest messages are dropped
    silently — a sliding window. Inherits all other behaviour from
    InMemoryChatMessageHistory.
    """

    def __init__(self, max_messages: int = 10) -> None:
        super().__init__()
        self._max_messages = max_messages

    def add_message(self, message: BaseMessage) -> None:
        super().add_message(message)
        self._trim()

    def _trim(self) -> None:
        if len(self.messages) > self._max_messages:
            self.messages = self.messages[-self._max_messages:]


DEFAULT_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
DEFAULT_CHROMA_DIR = os.getenv("CHROMA_PERSIST_DIR", "data/chroma")
DEFAULT_VIDEO_DATA_DIR = Path(os.getenv("VIDEO_DATA_DIR", "data/raw/whisper"))

# Per-session message history store. In production this can be swapped for a
# Redis/SQL backend without changing the agent factory interface.
_sessions: dict[str, BoundedChatMessageHistory] = {}


def get_session_history(session_id: str) -> BoundedChatMessageHistory:
    """Return (creating if needed) the chat history for a session."""
    if session_id not in _sessions:
        _sessions[session_id] = BoundedChatMessageHistory(
            max_messages=MAX_HISTORY_MESSAGES
        )
    return _sessions[session_id]


def clear_session(session_id: str) -> bool:
    """Delete the chat history for a session, freeing memory.

    Returns True if the session existed and was cleared, False otherwise.
    """
    if session_id in _sessions:
        del _sessions[session_id]
        return True
    return False


def create_agent(
    llm: ChatGoogleGenerativeAI | None = None,
    tools: list | None = None,
    verbose: bool = False,
) -> RunnableWithMessageHistory:
    """Create the migrant-archive conversational agent.

    Args:
        llm: LangChain chat model. Defaults to ChatGoogleGenerativeAI.
        tools: List of LangChain tools. Defaults to [list_videos, get_video_info, search_transcripts].
        verbose: Whether to enable AgentExecutor verbose logging.

    Returns:
        A RunnableWithMessageHistory wrapping an AgentExecutor. Invoke with:
            agent.invoke(
                {"input": question},
                config={"configurable": {"session_id": ...}},
            )
    """
    if llm is None:
        llm = ChatGoogleGenerativeAI(
            model=DEFAULT_MODEL,
            temperature=0.2,
        )

    if tools is None:
        provider = GeminiEmbeddingProvider()
        store = VectorStore(persist_dir=DEFAULT_CHROMA_DIR)
        tools = [
            make_list_videos(DEFAULT_VIDEO_DATA_DIR, store),
            make_get_video_info(DEFAULT_VIDEO_DATA_DIR, store),
            make_search_transcripts(provider, store, top_k=3),
        ]

    prompt = ChatPromptTemplate.from_messages([
        ("system", SYSTEM_PROMPT),
        MessagesPlaceholder(variable_name="chat_history", optional=True),
        ("human", "{input}"),
        MessagesPlaceholder(variable_name="agent_scratchpad"),
    ])

    agent = create_tool_calling_agent(llm, tools, prompt)
    executor = AgentExecutor(
        agent=agent,
        tools=tools,
        verbose=verbose,
        max_iterations=10,
        return_intermediate_steps=True,
    )

    def _normalize_output(result: dict) -> dict:
        """Ensure the agent answer is a plain string.

        Some models (e.g. Gemini via native tool calling) return the final
        message content as a list of parts; downstream callers expect a string.
        """
        output = result.get("output")
        if isinstance(output, list):
            parts: list[str] = []
            for part in output:
                if isinstance(part, dict):
                    parts.append(str(part.get("text", "")))
                else:
                    parts.append(str(part))
            result = dict(result)
            result["output"] = " ".join(parts).strip()
        return result

    return RunnableWithMessageHistory(
        executor | _normalize_output,
        get_session_history,
        input_messages_key="input",
        history_messages_key="chat_history",
    )
