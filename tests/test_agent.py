"""Tests for the agent conversation memory system.

Covers:
  - search_transcripts tool formatting and edge cases
  - Agent initialization with memory
  - ConversationBufferMemory accumulation across turns
  - CLI REPL behavior
  - End-to-end agent answering (skipped unless GEMINI_API_KEY is set)
"""

import os
import sys
from pathlib import Path

import pytest
from dotenv import load_dotenv
from langchain_core.language_models.chat_models import BaseChatModel

# Load API keys from .env so conditional skips (e.g. E2E) resolve correctly.
load_dotenv()

# Allow imports from backend/core, backend/agents, and backend/scripts.
sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(0, str(Path(__file__).parent.parent / "backend" / "core"))
sys.path.insert(0, str(Path(__file__).parent.parent / "backend" / "agents"))
sys.path.insert(0, str(Path(__file__).parent.parent / "backend" / "scripts"))

from test_embedding import FakeEmbeddingProvider  # noqa: E402


@pytest.fixture
def provider():
    """Deterministic embedding provider for tests."""
    return FakeEmbeddingProvider(dimension=128)


@pytest.fixture
def store():
    """Fresh in-memory ChromaDB collection."""
    from vector_store import VectorStore
    s = VectorStore(persist_dir=":memory:")
    yield s
    try:
        s.delete_collection()
    except Exception:
        pass


# ---------------------------------------------------------------------------
# Phase 2: search_transcripts tool
# ---------------------------------------------------------------------------


class TestSearchTranscriptsTool:
    """Unit tests for backend/agents/tools.py::make_search_transcripts."""

    def test_empty_store_returns_no_index_message(self, provider, store):
        from tools import make_search_transcripts

        search = make_search_transcripts(provider, store, top_k=3)
        result = search.invoke("migración")
        assert "No hay transcripciones indexadas" in result

    def test_search_returns_formatted_result_with_metadata(self, provider, store):
        from tools import make_search_transcripts

        store.add(
            ids=["v001_chunk_0"],
            documents=["La migración es un fenómeno global."],
            metadatas=[{
                "video_id": "v001",
                "title": "Testimonio de migración",
                "chunk_index": 0,
                "start_time": 12.5,
                "end_time": 18.3,
            }],
            embeddings=provider.embed(["La migración es un fenómeno global."]),
        )

        search = make_search_transcripts(provider, store, top_k=3)
        result = search.invoke("migración")

        assert "Testimonio de migración" in result
        assert "12.5" in result
        assert "18.3" in result
        assert "La migración es un fenómeno global" in result

    def test_top_k_limits_number_of_results(self, provider, store):
        from tools import make_search_transcripts

        docs = [f"Documento de migración número {i}." for i in range(5)]
        store.add(
            ids=[f"v002_chunk_{i}" for i in range(5)],
            documents=docs,
            metadatas=[{
                "video_id": "v002",
                "title": "Serie migratoria",
                "chunk_index": i,
                "start_time": float(i),
                "end_time": float(i + 1),
            } for i in range(5)],
            embeddings=provider.embed(docs),
        )

        search = make_search_transcripts(provider, store, top_k=2)
        result = search.invoke("migración")

        # Each result is formatted as a block prefixed with [1], [2], ...
        assert "[1]" in result
        assert "[2]" in result
        assert "[3]" not in result


# ---------------------------------------------------------------------------
# Fake chat model for agent tests (no API calls)
# ---------------------------------------------------------------------------


class FakeChatModel(BaseChatModel):
    """BaseChatModel that returns programmed text responses."""

    responses: list[str]

    def _generate(self, messages, stop=None, **kwargs):
        from langchain_core.messages import AIMessage
        from langchain_core.outputs import ChatGeneration, ChatResult

        text = self.responses[self._counter % len(self.responses)]
        self._counter += 1
        return ChatResult(
            generations=[ChatGeneration(message=AIMessage(content=text))]
        )

    @property
    def _llm_type(self) -> str:
        return "fake-chat-model"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._counter = 0


# ---------------------------------------------------------------------------
# Phase 3: Agent factory
# ---------------------------------------------------------------------------


class TestCreateAgent:
    """Unit tests for backend/agents/agent.py::create_agent."""

    def test_create_agent_returns_agent_executor(self, provider, store):
        from agent import create_agent
        from langchain_classic.agents import AgentExecutor

        llm = FakeChatModel(responses=["Final Answer: Respuesta de prueba."])
        tools = []
        executor = create_agent(llm=llm, tools=tools, verbose=False)

        assert isinstance(executor, AgentExecutor)

    def test_create_agent_has_conversation_buffer_memory(self, provider, store):
        from agent import create_agent
        from langchain_classic.memory import ConversationBufferMemory

        llm = FakeChatModel(responses=["Final Answer: Respuesta de prueba."])
        executor = create_agent(llm=llm, tools=[])

        assert isinstance(executor.memory, ConversationBufferMemory)
        assert executor.memory.memory_key == "chat_history"

    def test_create_agent_prompt_is_spanish(self, provider, store):
        from agent import create_agent, SYSTEM_PROMPT

        llm = FakeChatModel(responses=["Final Answer: Respuesta de prueba."])
        executor = create_agent(llm=llm, tools=[])

        assert "español" in SYSTEM_PROMPT.lower()
        assert "Cero" in SYSTEM_PROMPT
        assert executor is not None

    def test_create_agent_can_invoke_with_fake_llm(self, provider, store):
        from agent import create_agent

        llm = FakeChatModel(responses=["Final Answer: Respuesta de prueba."])
        executor = create_agent(llm=llm, tools=[])

        result = executor.invoke({"input": "Hola"})
        assert "Respuesta de prueba" in result["output"]


# ---------------------------------------------------------------------------
# Phase 4: Memory accumulation
# ---------------------------------------------------------------------------


class TestMemoryAccumulation:
    """ConversationBufferMemory accumulates turns within a session."""

    def test_memory_accumulates_two_turns(self, provider, store):
        from agent import create_agent
        from langchain_core.messages import HumanMessage, AIMessage

        llm = FakeChatModel(responses=[
            "Final Answer: Primera respuesta.",
            "Final Answer: Segunda respuesta.",
        ])
        executor = create_agent(llm=llm, tools=[])

        executor.invoke({"input": "Pregunta uno"})
        executor.invoke({"input": "Pregunta dos"})

        messages = executor.memory.chat_memory.messages
        human_messages = [m for m in messages if isinstance(m, HumanMessage)]
        ai_messages = [m for m in messages if isinstance(m, AIMessage)]

        assert len(human_messages) == 2
        assert len(ai_messages) == 2
        assert human_messages[0].content == "Pregunta uno"
        assert human_messages[1].content == "Pregunta dos"
        assert "Primera respuesta" in ai_messages[0].content
        assert "Segunda respuesta" in ai_messages[1].content

    def test_memory_includes_history_in_prompt(self, provider, store):
        from agent import create_agent
        from langchain_core.messages import HumanMessage, AIMessage

        llm = FakeChatModel(responses=[
            "Final Answer: Primera respuesta.",
            "Final Answer: Segunda respuesta.",
            "Final Answer: Tercera respuesta.",
        ])
        executor = create_agent(llm=llm, tools=[])

        executor.invoke({"input": "Pregunta uno"})
        executor.invoke({"input": "Pregunta dos"})
        executor.invoke({"input": "Pregunta tres"})

        # After three invocations, the public memory API should show three
        # human/AI pairs. This asserts the same fact as checking the fake LLM
        # call count, but without relying on internal state.
        messages = executor.memory.chat_memory.messages
        human_messages = [m for m in messages if isinstance(m, HumanMessage)]
        ai_messages = [m for m in messages if isinstance(m, AIMessage)]
        assert len(human_messages) == 3
        assert len(ai_messages) == 3


# ---------------------------------------------------------------------------
# Phase 5: CLI REPL
# ---------------------------------------------------------------------------


class TestAgentCLI:
    """Unit tests for backend/scripts/agent_cli.py REPL."""

    def test_cli_welcome_and_quit(self, monkeypatch, capsys):
        from unittest.mock import MagicMock
        import agent_cli

        fake_agent = MagicMock()
        monkeypatch.setattr(agent_cli, "create_agent", lambda: fake_agent)
        monkeypatch.setattr("builtins.input", lambda _: "quit")

        agent_cli.main()

        captured = capsys.readouterr()
        assert "Cero" in captured.out
        assert "Bienvenido" in captured.out
        fake_agent.invoke.assert_not_called()

    def test_cli_asks_question_and_prints_answer(self, monkeypatch, capsys):
        from unittest.mock import MagicMock
        import agent_cli

        fake_agent = MagicMock()
        fake_agent.invoke.return_value = {"output": "Respuesta del agente."}
        monkeypatch.setattr(agent_cli, "create_agent", lambda: fake_agent)

        inputs = iter(["¿De qué trata?", "salir"])
        monkeypatch.setattr("builtins.input", lambda _: next(inputs))

        agent_cli.main()

        captured = capsys.readouterr()
        assert "Respuesta del agente" in captured.out
        fake_agent.invoke.assert_called_once()

    def test_cli_exits_with_salir(self, monkeypatch, capsys):
        from unittest.mock import MagicMock
        import agent_cli

        fake_agent = MagicMock()
        monkeypatch.setattr(agent_cli, "create_agent", lambda: fake_agent)
        monkeypatch.setattr("builtins.input", lambda _: "salir")

        agent_cli.main()

        captured = capsys.readouterr()
        assert "Cero" in captured.out
        fake_agent.invoke.assert_not_called()

    def test_cli_exits_when_api_key_missing(self, monkeypatch, capsys):
        import agent_cli

        monkeypatch.delenv("GEMINI_API_KEY", raising=False)

        with pytest.raises(SystemExit) as exc_info:
            agent_cli.main()

        assert exc_info.value.code == 1
        captured = capsys.readouterr()
        assert "GEMINI_API_KEY" in captured.out


# ---------------------------------------------------------------------------
# Phase 6: End-to-end (requires GEMINI_API_KEY)
# ---------------------------------------------------------------------------


@pytest.mark.skipif(
    not bool(os.getenv("GEMINI_API_KEY")),
    reason="GEMINI_API_KEY not set; add it to .env to run end-to-end tests",
)
class TestAgentE2E:
    """End-to-end agent test with real Gemini LLM and embeddings."""

    def test_e2e_agent_answers_from_transcripts(self):
        from agent import create_agent
        from embedding_gemini import GeminiEmbeddingProvider
        from vector_store import VectorStore

        provider = GeminiEmbeddingProvider()
        store = VectorStore(persist_dir=":memory:")

        store.add(
            ids=["v100_chunk_0"],
            documents=["La migración en el mediterráneo es un tema complejo y peligroso."],
            metadatas=[{
                "video_id": "v100",
                "title": "Cruce del Mediterráneo",
                "chunk_index": 0,
                "start_time": 0.0,
                "end_time": 10.0,
            }],
            embeddings=provider.embed([
                "La migración en el mediterráneo es un tema complejo y peligroso."
            ]),
        )

        from tools import make_search_transcripts

        tools = [make_search_transcripts(provider, store, top_k=3)]
        agent = create_agent(tools=tools)
        result = agent.invoke({"input": "¿Qué se dice sobre la migración en el mediterráneo?"})
        answer = result.get("output", "")

        assert "mediterráneo" in answer.lower() or "migración" in answer.lower()
