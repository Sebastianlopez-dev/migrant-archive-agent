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

# Must be before langchain_classic: stubs out a heavy optional dependency that
# triggers a pre-existing torch/numpy incompatibility when langchain-classic is
# imported. We do not use the sentence-transformer text splitter.
import _compat  # noqa: F401, E402

from langchain_classic.agents import AgentExecutor, create_react_agent
from langchain_classic.memory import ConversationBufferMemory
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_google_genai import ChatGoogleGenerativeAI

from tools import make_search_transcripts
from core.embedding_gemini import GeminiEmbeddingProvider
from core.vector_store import VectorStore


SYSTEM_PROMPT = (
    "Eres Cero, un asistente que responde en español sobre testimonios "
    "migratorios archivados. Usa la herramienta search_transcripts para "
    "buscar fragmentos relevantes. Responde en español, cita el video y "
    "el rango de tiempo cuando sea posible, y no inventes información."
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
        handle_parsing_errors=True,
    )
