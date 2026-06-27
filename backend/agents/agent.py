"""Native tool-calling agent factory for the migrant-archive assistant.

`create_agent()` builds a Spanish-speaking agent backed by
`create_tool_calling_agent`, `AgentExecutor`, and per-session message history
via `RunnableWithMessageHistory` + `InMemoryChatMessageHistory`.
"""

from __future__ import annotations

import os

from dotenv import load_dotenv
from langchain_chroma import Chroma
from langchain_classic.agents import AgentExecutor, create_tool_calling_agent
from langchain_core.chat_history import InMemoryChatMessageHistory
from langchain_core.messages import BaseMessage
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.runnables.history import RunnableWithMessageHistory
from langchain_google_genai import ChatGoogleGenerativeAI, GoogleGenerativeAIEmbeddings

from tools import make_get_video_info, make_list_videos, make_search_transcripts


load_dotenv()

GEMINI_CHAT_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
DEFAULT_CHROMA_DIR = os.getenv("CHROMA_PERSIST_DIR", "data/chroma")

SYSTEM_PROMPT = """\
You are Cero, an assistant that answers questions about
the videos in the Plataforma Cero's YouTube channel that contain
archived migrant discussions and testimonies.

You MUST always use your tools to find information before answering.
Never answer from your own knowledge. Always respond in Spanish.

Search strategy:
- When the user asks about a topic, event, person, or concept (like FILMIG,
  an author, a specific event), first use list_videos to find which videos
  mention it, then use get_video_info for those videos. This gives you the
  full picture before diving into transcript search.
- After getting the video list and info, use search_transcripts scoped to
  the most relevant video_id to find specific quotes and details.
- If a broad search returns vague results, scope it to a specific video_id.
- If a scoped search returns nothing, remove the video_id filter and try
  broader keywords.

Specific knowledge:
- When asked about FILMIG, use get_video_info for this video first.
  The video "Presentacion FILMIG 2024 (Feria Itinerante del Libro Migrante)"
  (APgxfNssxGQ) contains the official definition and purpose of FILMIG.

When to use tools:
- list_videos: to discover what videos exist, find videos by year or speaker,
  and see which videos have identified speakers/participants.
- get_video_info: to get title, description, channel, year, speakers, and
  chunk count for a specific video. Use the video_id from list_videos.
- search_transcripts: to find what was SAID inside videos. Always call this
  after identifying the relevant video. Supports video_id, year, and channel
  filters for scoped searches.

Formatting rules:
- Do NOT use markdown (no **bold**, no *italics*, no bullet marks).
- Use plain text with dashes for lists when needed.
- When citing, include title and video ID.
    Example: "Video: Mujeres del Maiz (mY1hw79ydY0), 07:50".
- If the tools do not return enough information, say so honestly.
- Keep responses concise and well organized.
- End every response with a natural follow-up question that invites the
  user to continue exploring the topic or related themes.
"""

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
            model=GEMINI_CHAT_MODEL,
            temperature=0.2,
            model_kwargs={"tool_config": {"function_calling_config": {"mode": "ANY"}}},
        )

    if tools is None:
        store = Chroma(
            collection_name="migrant_archive",
            embedding_function=GoogleGenerativeAIEmbeddings(model="models/gemini-embedding-001"),
            persist_directory=DEFAULT_CHROMA_DIR,
        )
        tools = [
            make_list_videos(store),
            make_get_video_info(store),
            make_search_transcripts(store, top_k=3),
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
        max_iterations=5,
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
        output_messages_key="output",
    )
