#!/usr/bin/env python3
import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from langchain_chroma import Chroma
from langchain_classic.agents import AgentExecutor, create_tool_calling_agent
from langchain_core.chat_history import InMemoryChatMessageHistory
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.runnables.history import RunnableWithMessageHistory
from langchain_google_genai import ChatGoogleGenerativeAI, GoogleGenerativeAIEmbeddings

from tools_01 import make_search_transcripts, make_list_videos, make_get_video_info

load_dotenv()

GEMINI_CHAT_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")

CHROMA_DIR = os.getenv("CHROMA_PERSIST_DIR", "data/chroma")
CHROMA_COLLECTION = "migrant_archive"

TOP_K = 3
MAX_TURNS = 5
SESSION_ID = "cli-session"

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

def _ensure_api_key() -> str:
    key = os.getenv("GEMINI_API_KEY")
    if not key:
        print("ERROR: GEMINI_API_KEY not set. Copy .env.example to .env and fill it in.")
        sys.exit(1)
    return key

_ensure_api_key()

_store = Chroma(
    collection_name=CHROMA_COLLECTION,
    embedding_function=GoogleGenerativeAIEmbeddings(model="gemini-embedding-2"),
    persist_directory=CHROMA_DIR,
)

_llm = ChatGoogleGenerativeAI(
    model=GEMINI_CHAT_MODEL,
    temperature=0.2,
    model_kwargs={"tool_config": {"function_calling_config": {"mode": "ANY"}}},
)

# ── Agent setup ──────────────────────────────────────────

_prompt = ChatPromptTemplate.from_messages([
    ("system", SYSTEM_PROMPT),
    MessagesPlaceholder("chat_history"),
    ("human", "{input}"),
    MessagesPlaceholder("agent_scratchpad"),
])

_tools = [
    make_search_transcripts(_store, top_k=TOP_K),
    make_list_videos(_store),
    make_get_video_info(_store),
]

_agent_core = create_tool_calling_agent(_llm, _tools, _prompt)
_executor = AgentExecutor(
    agent=_agent_core,
    tools=_tools,
    max_iterations=10,
)

class BoundedChatMessageHistory(InMemoryChatMessageHistory):
    def __init__(self, max_messages: int = 10):
        super().__init__()
        self._max_messages = max_messages

    def add_message(self, message):
        super().add_message(message)
        if len(self.messages) > self._max_messages:
            self.messages = self.messages[-self._max_messages:]

_sessions: dict[str, BoundedChatMessageHistory] = {}

def _get_session(session_id: str) -> BoundedChatMessageHistory:
    if session_id not in _sessions:
        _sessions[session_id] = BoundedChatMessageHistory(
            max_messages=MAX_TURNS * 2
        )
    return _sessions[session_id]

def _normalize_output(result: dict) -> dict:
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

_agent = RunnableWithMessageHistory(
    _executor | _normalize_output,
    _get_session,
    input_messages_key="input",
    history_messages_key="chat_history",
    output_messages_key="output",
)

# ── UI helpers ───────────────────────────────────────────

def _show_history() -> None:
    messages = _get_session(SESSION_ID).messages
    if not messages:
        print("No history yet. Try later.")
        return
    for msg in messages:
        role = "user" if msg.type == "human" else "Cero"
        print(f"[{role}] {msg.content[:80]}...")
    print(f"  ({len(messages)} messages, {MAX_TURNS * 2} max)")

# ── Entry point ──────────────────────────────────────────

if __name__ == "__main__":
    args = sys.argv[1:]

    if args:
        question = " ".join(args)
        try:
            result = _agent.invoke(
                {"input": question},
                config={"configurable": {"session_id": SESSION_ID}},
            )
        except Exception as e:
            print(f"Error: {e}. Try again later.")
            sys.exit(1)
        print(result["output"])
    else:
        print("=" * 50)
        print("\nHi, I'm Cero \n- The Plataforma Cero's Youtube Q&A Agent.")
        print("=" * 50)
        print("\nHere some commands you can activate: \n'history' to check memory\n'q','quit','exit' to finish session.")
        print("=" * 50)
        print("\nAbove here you can insert a question for me")

        while True:
            try:
                question = input("> ").strip()
            except (EOFError, KeyboardInterrupt):
                print("\nAdios.")
                break

            if not question:
                continue
            if question.lower() in ("q", "quit", "salir", "exit"):
                print("Adios.")
                break
            if question.lower() == "history":
                _show_history()
                continue

            try:
                result = _agent.invoke(
                    {"input": question},
                    config={"configurable": {"session_id": SESSION_ID}},
                )
            except Exception as e:
                print(f"Error: {e}. Try again later.")
                continue
            print(result["output"])
            print()
