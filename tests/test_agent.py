"""Tests for the agent conversation memory system.

Covers:
  - search_transcripts tool formatting and edge cases
  - Agent initialization with native tool calling and session history
  - Per-session message retention across turns
  - CLI REPL behavior and session plumbing
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


class FakeToolCallingModel(BaseChatModel):
    """BaseChatModel that simulates native tool calling.

    First call returns an AIMessage with a single tool call. Subsequent calls
    (after a ToolMessage has been injected by the executor) return the final
    answer.
    """

    final_answer: str = "Respuesta de prueba."
    tool_name: str = "search_transcripts"
    tool_args: dict = {"query": "migración"}

    def _generate(self, messages, stop=None, **kwargs):
        from langchain_core.messages import AIMessage, ToolMessage
        from langchain_core.outputs import ChatGeneration, ChatResult

        if any(isinstance(m, ToolMessage) for m in messages):
            msg = AIMessage(content=self.final_answer)
        else:
            msg = AIMessage(
                content="",
                tool_calls=[{
                    "name": self.tool_name,
                    "args": self.tool_args,
                    "id": "call_1",
                }],
            )
        return ChatResult(generations=[ChatGeneration(message=msg)])

    def bind_tools(self, tools, **kwargs):
        """Return self so create_tool_calling_agent can bind tools."""
        return self

    @property
    def _llm_type(self) -> str:
        return "fake-tool-calling-model"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)


# ---------------------------------------------------------------------------
# Phase 3: Agent factory
# ---------------------------------------------------------------------------


class TestCreateAgent:
    """Unit tests for backend/agents/agent.py::create_agent."""

    def test_create_agent_returns_runnable_with_history(self, provider, store):
        from agent import create_agent
        from langchain_core.runnables.history import RunnableWithMessageHistory

        llm = FakeToolCallingModel(final_answer="Respuesta final.")
        agent = create_agent(llm=llm, tools=[], verbose=False)

        assert isinstance(agent, RunnableWithMessageHistory)

    def test_create_agent_wires_history_keys(self, provider, store):
        from agent import create_agent
        from langchain_core.runnables.history import RunnableWithMessageHistory

        llm = FakeToolCallingModel(final_answer="Respuesta final.")
        agent = create_agent(llm=llm, tools=[], verbose=False)

        assert agent.input_messages_key == "input"
        assert agent.history_messages_key == "chat_history"

    def test_create_agent_prompt_has_no_react_format(self, provider, store):
        from agent import create_agent, SYSTEM_PROMPT
        from langchain_core.runnables.history import RunnableWithMessageHistory

        llm = FakeToolCallingModel(final_answer="Respuesta final.")
        agent = create_agent(llm=llm, tools=[], verbose=False)

        assert isinstance(agent, RunnableWithMessageHistory)
        assert "Cero" in SYSTEM_PROMPT
        assert "spanish" in SYSTEM_PROMPT.lower()
        assert "Thought:" not in SYSTEM_PROMPT
        assert "Action:" not in SYSTEM_PROMPT
        assert "agent_scratchpad" not in SYSTEM_PROMPT

    def test_create_agent_can_invoke_with_fake_llm(self, provider, store):
        from agent import create_agent

        llm = FakeToolCallingModel(final_answer="Respuesta final.")
        agent = create_agent(llm=llm, tools=[], verbose=False)

        result = agent.invoke(
            {"input": "Hola"},
            {"configurable": {"session_id": "test-session"}},
        )
        assert "Respuesta final" in result["output"]


# ---------------------------------------------------------------------------
# Phase 4: Tool calling loop
# ---------------------------------------------------------------------------


class TestToolCallingLoop:
    """Native tool calling execution with a fake LLM."""

    def test_fake_llm_calls_search_transcripts(self, provider, store):
        from agent import create_agent
        from tools import make_search_transcripts

        store.add(
            ids=["v003_chunk_0"],
            documents=["La migración es un fenómeno global."],
            metadatas=[{
                "video_id": "v003",
                "title": "Testimonio de migración",
                "chunk_index": 0,
                "start_time": 12.5,
                "end_time": 18.3,
            }],
            embeddings=provider.embed(["La migración es un fenómeno global."]),
        )

        search = make_search_transcripts(provider, store, top_k=3)
        llm = FakeToolCallingModel(
            final_answer="La migración es un fenómeno global.",
            tool_args={"query": "migración"},
        )
        agent = create_agent(llm=llm, tools=[search], verbose=False)

        result = agent.invoke(
            {"input": "¿Qué es la migración?"},
            {"configurable": {"session_id": "tool-session"}},
        )

        assert "fenómeno global" in result["output"]
        assert result.get("intermediate_steps")


# ---------------------------------------------------------------------------
# Phase 5: Memory accumulation
# ---------------------------------------------------------------------------


class TestMemoryAccumulation:
    """Per-session message history accumulates turns."""

    def test_history_retains_two_turns_same_session(self, provider, store):
        from agent import create_agent, get_session_history
        from langchain_core.messages import HumanMessage, AIMessage

        llm = FakeToolCallingModel(final_answer="Primera respuesta.")
        agent = create_agent(llm=llm, tools=[], verbose=False)

        agent.invoke(
            {"input": "Pregunta uno"},
            {"configurable": {"session_id": "mem-session"}},
        )

        llm.final_answer = "Segunda respuesta."
        agent.invoke(
            {"input": "Pregunta dos"},
            {"configurable": {"session_id": "mem-session"}},
        )

        history = get_session_history("mem-session")
        messages = history.messages
        human_messages = [m for m in messages if isinstance(m, HumanMessage)]
        ai_answers = [
            m for m in messages
            if isinstance(m, AIMessage)
            and m.content in ("Primera respuesta.", "Segunda respuesta.")
        ]

        assert len(human_messages) == 2
        assert human_messages[0].content == "Pregunta uno"
        assert human_messages[1].content == "Pregunta dos"
        assert len(ai_answers) == 2

    def test_history_is_isolated_by_session_id(self, provider, store):
        from agent import create_agent, get_session_history
        from langchain_core.messages import HumanMessage

        llm = FakeToolCallingModel(final_answer="Respuesta A.")
        agent = create_agent(llm=llm, tools=[], verbose=False)

        agent.invoke(
            {"input": "Pregunta A"},
            {"configurable": {"session_id": "session-a"}},
        )
        agent.invoke(
            {"input": "Pregunta B"},
            {"configurable": {"session_id": "session-b"}},
        )

        history_a = get_session_history("session-a")
        history_b = get_session_history("session-b")

        assert len([m for m in history_a.messages if isinstance(m, HumanMessage)]) == 1
        assert len([m for m in history_b.messages if isinstance(m, HumanMessage)]) == 1
        assert history_a.messages[0].content == "Pregunta A"
        assert history_b.messages[0].content == "Pregunta B"


# ---------------------------------------------------------------------------
# Phase 6: CLI REPL
# ---------------------------------------------------------------------------


class TestAgentCLI:
    """Unit tests for backend/scripts/agent_cli.py REPL."""

    def _make_fake_agent(self):
        from unittest.mock import MagicMock

        fake_agent = MagicMock()
        fake_agent.invoke.return_value = {"output": "Respuesta del agente."}
        return fake_agent

    def test_cli_welcome_and_quit(self, monkeypatch, capsys):
        import agent_cli

        fake_agent = self._make_fake_agent()
        monkeypatch.setattr(agent_cli, "create_agent", lambda **_: fake_agent)
        monkeypatch.setattr("builtins.input", lambda _: "quit")

        agent_cli.main()

        captured = capsys.readouterr()
        assert "Cero" in captured.out
        assert "Bienvenido" in captured.out
        fake_agent.invoke.assert_not_called()

    def test_cli_asks_question_and_prints_answer(self, monkeypatch, capsys):
        import agent_cli

        fake_agent = self._make_fake_agent()
        monkeypatch.setattr(agent_cli, "create_agent", lambda **_: fake_agent)

        inputs = iter(["¿De qué trata?", "salir"])
        monkeypatch.setattr("builtins.input", lambda _: next(inputs))

        agent_cli.main()

        captured = capsys.readouterr()
        assert "Respuesta del agente" in captured.out
        fake_agent.invoke.assert_called_once()

    def test_cli_invokes_with_session_id(self, monkeypatch, capsys):
        import agent_cli

        fake_agent = self._make_fake_agent()
        monkeypatch.setattr(agent_cli, "create_agent", lambda **_: fake_agent)

        inputs = iter(["¿De qué trata?", "salir"])
        monkeypatch.setattr("builtins.input", lambda _: next(inputs))

        agent_cli.main()

        fake_agent.invoke.assert_called_once()
        call_args = fake_agent.invoke.call_args
        assert call_args.kwargs.get("config") == {
            "configurable": {"session_id": "cli-session"},
        }

    def test_cli_exits_with_salir(self, monkeypatch, capsys):
        import agent_cli

        fake_agent = self._make_fake_agent()
        monkeypatch.setattr(agent_cli, "create_agent", lambda **_: fake_agent)
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
# Phase 7: End-to-end (requires GEMINI_API_KEY)
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
        result = agent.invoke(
            {"input": "¿Qué se dice sobre la migración en el mediterráneo?"},
            {"configurable": {"session_id": "e2e-session"}},
        )
        answer = result.get("output", "")

        assert "mediterráneo" in answer.lower() or "migración" in answer.lower()
