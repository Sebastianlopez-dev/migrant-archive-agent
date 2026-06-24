"""ReAct agent factory for the migrant-archive conversational assistant.

`create_agent()` builds a Spanish-speaking AgentExecutor backed by
`ConversationBufferMemory` and the `search_transcripts` tool.
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

from langchain_classic.agents import AgentExecutor, create_react_agent
from langchain_classic.memory import ConversationBufferMemory
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_google_genai import ChatGoogleGenerativeAI

from tools import make_search_transcripts
from core.embedding_gemini import GeminiEmbeddingProvider
from core.vector_store import VectorStore


SYSTEM_PROMPT = (
    "You are Cero, an assistant that answers questions in Spanish about archived "
    "migrant testimonies. Use the search_transcripts tool to find relevant "
    "transcript fragments. Always respond in Spanish, cite the video and "
    "time range when possible, and do not invent information.\n\n"
    "You MUST use EXACTLY this format in English (do not translate it):\n"
    "Thought: reason about what to do next\n"
    "Action: search_transcripts\n"
    "Action Input: the search query in Spanish\n"
    "Observation: tool result\n"
    "... (you may repeat Thought/Action/Action Input/Observation)\n"
    "Thought: I have the final answer\n"
    "Final Answer: respond to the user in Spanish"
)

DEFAULT_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
DEFAULT_CHROMA_DIR = os.getenv("CHROMA_PERSIST_DIR", "data/chroma")


def create_agent(
    llm: ChatGoogleGenerativeAI | None = None,
    tools: list | None = None,
    memory: ConversationBufferMemory | None = None,
    verbose: bool = False,
) -> AgentExecutor:
    """Create the migrant-archive conversational agent.

    Args:
        llm: LangChain chat model. Defaults to ChatGoogleGenerativeAI.
        tools: List of LangChain tools. Defaults to [search_transcripts].
        memory: ConversationBufferMemory instance. Defaults to a fresh
            ConversationBufferMemory with memory_key="chat_history".
        verbose: Whether to enable AgentExecutor verbose logging.

    Returns:
        Configured AgentExecutor ready to invoke with {"input": ...}.
    """
    if llm is None:
        llm = ChatGoogleGenerativeAI(
            model=DEFAULT_MODEL,
            temperature=0.2,
        )

    if tools is None:
        provider = GeminiEmbeddingProvider()
        store = VectorStore(persist_dir=DEFAULT_CHROMA_DIR)
        tools = [make_search_transcripts(provider, store, top_k=3)]

    if memory is None:
        memory = ConversationBufferMemory(
            return_messages=True,
            memory_key="chat_history",
        )

    prompt = ChatPromptTemplate.from_messages([
        (
            "system",
            SYSTEM_PROMPT
            + "\n\nHerramientas disponibles:\n{tools}\n"
            "Nombres de herramientas: {tool_names}",
        ),
        MessagesPlaceholder(variable_name="chat_history"),
        ("human", "{input}"),
        ("human", "{agent_scratchpad}"),
    ])

    agent = create_react_agent(llm, tools, prompt)
    return AgentExecutor(
        agent=agent,
        tools=tools,
        memory=memory,
        verbose=verbose,
        max_iterations=3,
        handle_parsing_errors=True,
    )
