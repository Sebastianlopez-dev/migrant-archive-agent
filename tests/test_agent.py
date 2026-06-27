"""Tests for the agent conversation memory system.

Covers:
  - search_transcripts tool formatting and edge cases
  - list_videos and get_video_info catalog tools
  - Agent initialization with native tool calling and session history
  - Per-session message retention across turns
  - CLI REPL behavior and session plumbing
  - End-to-end agent answering (skipped unless GEMINI_API_KEY is set)
"""

import json
import os
import sys
from pathlib import Path

import pytest
from dotenv import load_dotenv
from langchain_core.embeddings import Embeddings
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_chroma import Chroma

# Load API keys from .env so conditional skips (e.g. E2E) resolve correctly.
load_dotenv()

# Allow imports from backend/core, backend/agents, and backend/scripts.
sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(0, str(Path(__file__).parent.parent / "backend" / "core"))
sys.path.insert(0, str(Path(__file__).parent.parent / "backend" / "agents"))
sys.path.insert(0, str(Path(__file__).parent.parent / "backend" / "scripts"))

from tests.test_embedding import FakeEmbeddingProvider  # noqa: E402


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


class _FakeLangchainEmbeddings(Embeddings):
    """Wraps the deterministic FakeEmbeddingProvider as a LangChain Embeddings class."""

    def __init__(self, provider: FakeEmbeddingProvider) -> None:
        self._provider = provider

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return self._provider.embed(texts)

    def embed_query(self, text: str) -> list[float]:
        return self._provider.embed_query(text)


class FakeChroma:
    """Lightweight Chroma wrapper that exposes the interface the agent tools expect.

    The tools use ``store._collection.get/count`` and ``store.similarity_search``.
    This fake uses a real ``langchain_chroma.Chroma`` instance backed by fake
    embeddings so the tool logic can be exercised without calling Gemini.
    """

    def __init__(self, provider: FakeEmbeddingProvider, persist_dir: str) -> None:
        self._provider = provider
        self._persist_dir = persist_dir
        self._embedding_function = _FakeLangchainEmbeddings(provider)
        self._chroma = self._create_chroma()

    def _create_chroma(self) -> Chroma:
        return Chroma(
            collection_name="test_agent",
            embedding_function=self._embedding_function,
            persist_directory=self._persist_dir,
        )

    def add(
        self,
        ids: list[str],
        documents: list[str],
        metadatas: list[dict],
        embeddings: list[list[float]],
    ) -> None:
        """Add texts to the underlying Chroma collection."""
        # Embeddings are ignored because the fake embedding function produces
        # deterministic vectors that match the provider fixture.
        _ = embeddings
        self._chroma.add_texts(texts=documents, metadatas=metadatas, ids=ids)

    def delete_collection(self) -> None:
        """Drop the collection and recreate a fresh one for the next test step."""
        self._chroma.delete_collection()
        self._chroma = self._create_chroma()

    @property
    def _collection(self):
        return self._chroma._collection

    def as_retriever(self, **kwargs):
        return self._chroma.as_retriever(**kwargs)

    def similarity_search(self, query: str, k: int | None = None, filter=None):
        return self._chroma.similarity_search(query, k=k, filter=filter)


def _make_video_data(
    video_id: str,
    title: str,
    description: str = "",
    channel: str = "unknown",
    upload_date: str = "20240101",
    duration: int = 120,
    full_text: str = "",
) -> dict:
    """Build a minimal VideoData-shaped dict for tool tests."""
    return {
        "video_id": video_id,
        "title": title,
        "description": description,
        "transcript_segments": [],
        "full_text": full_text or f"Contenido completo de {title}.",
        "metadata": {
            "duration": duration,
            "upload_date": upload_date,
            "channel": channel,
        },
    }


def _save_video_data(tmp_path: Path, data: dict) -> Path:
    filepath = tmp_path / f"{data['video_id']}.json"
    filepath.write_text(json.dumps(data, indent=2, ensure_ascii=False))
    return filepath


@pytest.fixture
def store(provider, tmp_path):
    """Fresh in-memory ChromaDB collection wrapped for the new tool contract."""
    return FakeChroma(provider, str(tmp_path / "chroma"))


# ---------------------------------------------------------------------------
# Phase 2: search_transcripts tool
# ---------------------------------------------------------------------------


class TestSearchTranscriptsTool:
    """Unit tests for backend/agents/tools.py::make_search_transcripts."""

    def test_empty_store_returns_no_index_message(self, provider, store):
        from tools import make_search_transcripts

        search = make_search_transcripts(store, top_k=3)
        result = search.invoke("migración")
        assert "No hay transcripciones indexadas" in result

    def test_search_returns_formatted_result_with_metadata(self, provider, store):
        from tools import make_search_transcripts

        store.delete_collection()
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

        search = make_search_transcripts(store, top_k=3)
        result = search.invoke("migración")

        assert "Testimonio de migración" in result
        assert "v001" in result
        assert "12.5" in result
        assert "18.3" in result
        assert "La migración es un fenómeno global" in result

    def test_top_k_limits_number_of_results(self, provider, store):
        from tools import make_search_transcripts

        store.delete_collection()
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

        search = make_search_transcripts(store, top_k=2)
        result = search.invoke("migración")

        # Each result is formatted as a block prefixed with [1], [2], ...
        assert "[1]" in result
        assert "[2]" in result
        assert "[3]" not in result

    def test_search_with_video_id_scopes_results(self, provider, store):
        from tools import make_search_transcripts

        store.delete_collection()
        docs = ["Texto del video A.", "Texto del video B."]
        store.add(
            ids=["vA_chunk_0", "vB_chunk_0"],
            documents=docs,
            metadatas=[{
                "video_id": "vA",
                "title": "Video A",
                "chunk_index": 0,
                "start_time": 0.0,
                "end_time": 10.0,
                "channel": "Canal 1",
                "year": 2024,
            }, {
                "video_id": "vB",
                "title": "Video B",
                "chunk_index": 0,
                "start_time": 0.0,
                "end_time": 10.0,
                "channel": "Canal 2",
                "year": 2023,
            }],
            embeddings=provider.embed(docs),
        )

        search = make_search_transcripts(store, top_k=5)
        result = search.invoke({"query": "texto", "video_id": "vA"})

        assert "Video A" in result
        assert "Video B" not in result

    def test_search_with_year_filter(self, provider, store):
        from tools import make_search_transcripts

        store.delete_collection()
        docs = ["Texto del 2024.", "Texto del 2023."]
        store.add(
            ids=["v1_chunk_0", "v2_chunk_0"],
            documents=docs,
            metadatas=[{
                "video_id": "v1",
                "title": "Video 2024",
                "chunk_index": 0,
                "start_time": 0.0,
                "end_time": 10.0,
                "channel": "Canal 1",
                "year": 2024,
            }, {
                "video_id": "v2",
                "title": "Video 2023",
                "chunk_index": 0,
                "start_time": 0.0,
                "end_time": 10.0,
                "channel": "Canal 1",
                "year": 2023,
            }],
            embeddings=provider.embed(docs),
        )

        search = make_search_transcripts(store, top_k=5)
        result = search.invoke({"query": "texto", "year": 2024})

        assert "Video 2024" in result
        assert "Video 2023" not in result

    def test_search_with_channel_filter(self, provider, store):
        from tools import make_search_transcripts

        store.delete_collection()
        docs = ["Texto del Canal 1.", "Texto del Canal 2."]
        store.add(
            ids=["v1_chunk_0", "v2_chunk_0"],
            documents=docs,
            metadatas=[{
                "video_id": "v1",
                "title": "Video Canal 1",
                "chunk_index": 0,
                "start_time": 0.0,
                "end_time": 10.0,
                "channel": "Canal 1",
                "year": 2024,
            }, {
                "video_id": "v2",
                "title": "Video Canal 2",
                "chunk_index": 0,
                "start_time": 0.0,
                "end_time": 10.0,
                "channel": "Canal 2",
                "year": 2024,
            }],
            embeddings=provider.embed(docs),
        )

        search = make_search_transcripts(store, top_k=5)
        result = search.invoke({"query": "texto", "channel": "Canal 1"})

        assert "Video Canal 1" in result
        assert "Video Canal 2" not in result

    def test_search_with_combined_year_and_channel_filters(self, provider, store):
        from tools import make_search_transcripts

        store.delete_collection()
        docs = ["Canal 1 2024.", "Canal 2 2024.", "Canal 1 2023."]
        store.add(
            ids=["v1_chunk_0", "v2_chunk_0", "v3_chunk_0"],
            documents=docs,
            metadatas=[{
                "video_id": "v1",
                "title": "Canal 1 2024",
                "chunk_index": 0,
                "start_time": 0.0,
                "end_time": 10.0,
                "channel": "Canal 1",
                "year": 2024,
            }, {
                "video_id": "v2",
                "title": "Canal 2 2024",
                "chunk_index": 0,
                "start_time": 0.0,
                "end_time": 10.0,
                "channel": "Canal 2",
                "year": 2024,
            }, {
                "video_id": "v3",
                "title": "Canal 1 2023",
                "chunk_index": 0,
                "start_time": 0.0,
                "end_time": 10.0,
                "channel": "Canal 1",
                "year": 2023,
            }],
            embeddings=provider.embed(docs),
        )

        search = make_search_transcripts(store, top_k=5)
        result = search.invoke({"query": "Canal", "year": 2024, "channel": "Canal 1"})

        assert "Canal 1 2024" in result
        assert "Canal 2 2024" not in result
        assert "Canal 1 2023" not in result


# ---------------------------------------------------------------------------
# Phase 2: list_videos and get_video_info tools
# ---------------------------------------------------------------------------


class TestListVideosTool:
    """Unit tests for backend/agents/tools.py::make_list_videos."""

    def test_list_videos_returns_all_videos(self, provider, store, tmp_path):
        from tools import make_list_videos

        _save_video_data(tmp_path, _make_video_data("v1", "Video uno", channel="Lina"))
        _save_video_data(tmp_path, _make_video_data("v2", "Video dos", channel="Ana"))
        store.delete_collection()
        store.add(
            ids=["v1_chunk_0", "v2_chunk_0", "v2_chunk_1"],
            documents=["uno", "dos", "tres"],
            metadatas=[
                {"video_id": "v1", "title": "Video uno", "chunk_index": 0, "channel": "Canal Lina", "year": 2024},
                {"video_id": "v2", "title": "Video dos", "chunk_index": 0, "channel": "Canal Ana", "year": 2023},
                {"video_id": "v2", "title": "Video dos", "chunk_index": 1, "channel": "Canal Ana", "year": 2023},
            ],
            embeddings=provider.embed(["uno", "dos", "tres"]),
        )

        list_videos = make_list_videos(store)
        result = list_videos.invoke({})

        assert "Video uno" in result
        assert "Video dos" in result
        assert "Canal Lina" in result
        assert "Canal Ana" in result
        assert "1 chunk(s)" in result
        assert "2 chunk(s)" in result
        assert "2 video(s)" in result

    def test_list_videos_filters_by_year(self, provider, store, tmp_path):
        from tools import make_list_videos

        _save_video_data(
            tmp_path,
            _make_video_data("v1", "Video 2023", upload_date="20230101"),
        )
        _save_video_data(
            tmp_path,
            _make_video_data("v2", "Video 2024", upload_date="20240101"),
        )
        store.delete_collection()
        store.add(
            ids=["v1_chunk_0", "v2_chunk_0"],
            documents=["a", "b"],
            metadatas=[
                {"video_id": "v1", "title": "Video 2023", "chunk_index": 0, "channel": "Canal 1", "year": 2023},
                {"video_id": "v2", "title": "Video 2024", "chunk_index": 0, "channel": "Canal 1", "year": 2024},
            ],
            embeddings=provider.embed(["a", "b"]),
        )

        list_videos = make_list_videos(store)
        result = list_videos.invoke({"year": 2024})

        assert "Video 2024" in result
        assert "Video 2023" not in result
        assert "1 video(s)" in result

    def test_list_videos_filters_by_speaker(self, provider, store, tmp_path):
        from tools import make_list_videos

        _save_video_data(
            tmp_path,
            _make_video_data("v1", "Video Lina", channel="Lina"),
        )
        _save_video_data(
            tmp_path,
            _make_video_data("v2", "Video Ana", channel="Ana"),
        )
        store.delete_collection()
        store.add(
            ids=["v1_chunk_0", "v2_chunk_0"],
            documents=["a", "b"],
            metadatas=[
                {"video_id": "v1", "title": "Video Lina", "chunk_index": 0, "channel": "Canal Lina", "year": 2024, "speaker": "Lina"},
                {"video_id": "v2", "title": "Video Ana", "chunk_index": 0, "channel": "Canal Ana", "year": 2024, "speaker": "Ana"},
            ],
            embeddings=provider.embed(["a", "b"]),
        )

        list_videos = make_list_videos(store)
        result = list_videos.invoke({"speaker": "Lina"})

        assert "Video Lina" in result
        assert "Video Ana" not in result
        assert "1 video(s)" in result

    def test_list_videos_filters_by_channel(self, provider, store, tmp_path):
        from tools import make_list_videos

        _save_video_data(
            tmp_path,
            _make_video_data("v1", "Video Canal 1", channel="Canal 1"),
        )
        _save_video_data(
            tmp_path,
            _make_video_data("v2", "Video Canal 2", channel="Canal 2"),
        )
        store.delete_collection()
        store.add(
            ids=["v1_chunk_0", "v2_chunk_0"],
            documents=["a", "b"],
            metadatas=[
                {"video_id": "v1", "title": "Video Canal 1", "chunk_index": 0, "channel": "Canal 1", "year": 2024},
                {"video_id": "v2", "title": "Video Canal 2", "chunk_index": 0, "channel": "Canal 2", "year": 2024},
            ],
            embeddings=provider.embed(["a", "b"]),
        )

        list_videos = make_list_videos(store)
        result = list_videos.invoke({"channel": "Canal 1"})

        assert "Video Canal 1" in result
        assert "Video Canal 2" not in result
        assert "1 video(s)" in result

    def test_list_videos_combines_filters(self, provider, store, tmp_path):
        from tools import make_list_videos

        _save_video_data(
            tmp_path,
            _make_video_data("v1", "Lina 2023", channel="Lina", upload_date="20230101"),
        )
        _save_video_data(
            tmp_path,
            _make_video_data("v2", "Lina 2024", channel="Lina", upload_date="20240101"),
        )
        store.delete_collection()
        store.add(
            ids=["v1_chunk_0", "v2_chunk_0"],
            documents=["a", "b"],
            metadatas=[
                {"video_id": "v1", "title": "Lina 2023", "chunk_index": 0, "channel": "Canal Lina", "year": 2023, "speaker": "Lina"},
                {"video_id": "v2", "title": "Lina 2024", "chunk_index": 0, "channel": "Canal Lina", "year": 2024, "speaker": "Lina"},
            ],
            embeddings=provider.embed(["a", "b"]),
        )

        list_videos = make_list_videos(store)
        result = list_videos.invoke({"year": 2024, "speaker": "Lina", "channel": "Canal Lina"})

        assert "Lina 2024" in result
        assert "Lina 2023" not in result
        assert "1 video(s)" in result

    def test_list_videos_uses_store_when_json_missing(self, provider, store, tmp_path):
        from tools import make_list_videos

        store.delete_collection()
        store.add(
            ids=["v1_chunk_0"],
            documents=["a"],
            metadatas=[{
                "video_id": "v1",
                "title": "Solo en store",
                "chunk_index": 0,
                "channel": "Canal Store",
                "year": 2024,
            }],
            embeddings=provider.embed(["a"]),
        )

        list_videos = make_list_videos(store)
        result = list_videos.invoke({})

        assert "Solo en store" in result
        assert "Canal Store" in result
        assert "1 video(s)" in result


class TestGetVideoInfoTool:
    """Unit tests for backend/agents/tools.py::make_get_video_info."""

    def test_get_video_info_returns_metadata(self, provider, store, tmp_path):
        from tools import make_get_video_info

        _save_video_data(
            tmp_path,
            _make_video_data(
                "v1",
                "Título de prueba",
                description="Descripción de prueba",
                channel="Lina",
                upload_date="20240515",
                duration=125,
                full_text="Texto completo del video de prueba.",
            ),
        )
        store.delete_collection()
        first_doc = (
            "Description: Descripción de prueba\n"
            "[00:00] Texto completo del video de prueba."
        )
        store.add(
            ids=["v1_chunk_0", "v1_chunk_1"],
            documents=[first_doc, "b"],
            metadatas=[
                {"video_id": "v1", "title": "Título de prueba", "chunk_index": 0, "channel": "Canal Store", "year": 2024, "speaker": "Lina", "duration": 125},
                {"video_id": "v1", "title": "Título de prueba", "chunk_index": 1, "channel": "Canal Store", "year": 2024, "speaker": "Lina", "duration": 125},
            ],
            embeddings=provider.embed([first_doc, "b"]),
        )

        get_info = make_get_video_info(store)
        result = get_info.invoke({"video_id": "v1"})

        assert "Title: Título de prueba" in result
        assert "Description: Descripción de prueba" in result
        assert "Year: 2024" in result
        assert "Duration: 125s" in result
        assert "Channel: Canal Store" in result
        assert "Chunks: 2" in result
        assert "Speaker(s): Lina" in result
        assert "Transcript:" in result

    def test_get_video_info_missing_video_returns_not_found(self, provider, store, tmp_path):
        from tools import make_get_video_info

        get_info = make_get_video_info(store)
        result = get_info.invoke({"video_id": "missing"})

        assert "no encontrado" in result.lower() or "not found" in result.lower()

    def test_get_video_info_uses_store_when_json_missing(self, provider, store, tmp_path):
        from tools import make_get_video_info

        store.delete_collection()
        store.add(
            ids=["v1_chunk_0"],
            documents=["a"],
            metadatas=[{
                "video_id": "v1",
                "title": "Solo en store",
                "chunk_index": 0,
                "channel": "Canal Store",
                "year": 2024,
                "duration": 60,
            }],
            embeddings=provider.embed(["a"]),
        )

        get_info = make_get_video_info(store)
        result = get_info.invoke({"video_id": "v1"})

        assert "ID: v1" in result
        assert "Title: Solo en store" in result
        assert "Year: 2024" in result
        assert "Channel: Canal Store" in result
        assert "Duration: 60s" in result
        assert "Chunks: 1" in result


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

    def test_system_prompt_mentions_all_tools(self, provider, store):
        from agent import SYSTEM_PROMPT

        assert "list_videos" in SYSTEM_PROMPT
        assert "get_video_info" in SYSTEM_PROMPT
        assert "search_transcripts" in SYSTEM_PROMPT

    def test_system_prompt_has_search_strategy(self, provider, store):
        from agent import SYSTEM_PROMPT

        assert "Search strategy" in SYSTEM_PROMPT

    def test_system_prompt_mentions_filmig(self, provider, store):
        from agent import SYSTEM_PROMPT

        assert "FILMIG" in SYSTEM_PROMPT

    def test_system_prompt_requires_plain_text_formatting(self, provider, store):
        from agent import SYSTEM_PROMPT

        assert "plain text" in SYSTEM_PROMPT.lower() or "Do NOT use markdown" in SYSTEM_PROMPT

    def test_system_prompt_mentions_search_filters(self, provider, store):
        from agent import SYSTEM_PROMPT

        assert "year" in SYSTEM_PROMPT.lower()
        assert "channel" in SYSTEM_PROMPT.lower()
        assert "video_id" in SYSTEM_PROMPT.lower()
        assert "search_transcripts" in SYSTEM_PROMPT

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

        store.delete_collection()
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

        search = make_search_transcripts(store, top_k=3)
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

    def test_fake_llm_calls_list_videos(self, provider, store, tmp_path):
        from agent import create_agent
        from tools import make_list_videos

        _save_video_data(tmp_path, _make_video_data("v1", "Video uno"))
        store.delete_collection()
        store.add(
            ids=["v1_chunk_0"],
            documents=["Texto del video uno."],
            metadatas=[{"video_id": "v1", "title": "Video uno", "chunk_index": 0}],
            embeddings=provider.embed(["Texto del video uno."]),
        )

        list_videos = make_list_videos(store)
        llm = FakeToolCallingModel(
            final_answer="Aquí está la lista de videos.",
            tool_name="list_videos",
            tool_args={},
        )
        agent = create_agent(llm=llm, tools=[list_videos], verbose=False)

        result = agent.invoke(
            {"input": "Lista los videos"},
            {"configurable": {"session_id": "list-session"}},
        )

        assert "lista de videos" in result["output"].lower()
        assert result.get("intermediate_steps")
        tool_call_name = result["intermediate_steps"][0][0].tool
        assert tool_call_name == "list_videos"

    def test_fake_llm_calls_get_video_info(self, provider, store, tmp_path):
        from agent import create_agent
        from tools import make_get_video_info

        _save_video_data(tmp_path, _make_video_data("v1", "Video uno"))
        store.delete_collection()
        store.add(
            ids=["v1_chunk_0"],
            documents=["Texto del video uno."],
            metadatas=[{"video_id": "v1", "title": "Video uno", "chunk_index": 0}],
            embeddings=provider.embed(["Texto del video uno."]),
        )

        get_info = make_get_video_info(store)
        llm = FakeToolCallingModel(
            final_answer="Aquí está la información del video.",
            tool_name="get_video_info",
            tool_args={"video_id": "v1"},
        )
        agent = create_agent(llm=llm, tools=[get_info], verbose=False)

        result = agent.invoke(
            {"input": "Cuéntame del video v1"},
            {"configurable": {"session_id": "info-session"}},
        )

        assert "información del video" in result["output"].lower()
        assert result.get("intermediate_steps")
        tool_call_name = result["intermediate_steps"][0][0].tool
        assert tool_call_name == "get_video_info"


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
# Phase 5b: Bounded history (sliding window)
# ---------------------------------------------------------------------------


class TestBoundedChatMessageHistory:
    """Unit tests for BoundedChatMessageHistory sliding window."""

    def test_trim_drops_oldest_when_buffer_exceeded(self):
        from agent import BoundedChatMessageHistory
        from langchain_core.messages import HumanMessage, AIMessage

        history = BoundedChatMessageHistory(max_messages=4)

        for i in range(3):  # 6 messages: Q1,A1,Q2,A2,Q3,A3
            history.add_message(HumanMessage(content=f"Pregunta {i+1}"))
            history.add_message(AIMessage(content=f"Respuesta {i+1}"))

        assert len(history.messages) == 4
        assert history.messages[0].content == "Pregunta 2"
        assert history.messages[-1].content == "Respuesta 3"

    def test_no_trim_when_under_limit(self):
        from agent import BoundedChatMessageHistory
        from langchain_core.messages import HumanMessage, AIMessage

        history = BoundedChatMessageHistory(max_messages=10)

        history.add_message(HumanMessage(content="Hola"))
        history.add_message(AIMessage(content="Hola!"))

        assert len(history.messages) == 2

    def test_default_max_messages_is_ten(self):
        from agent import BoundedChatMessageHistory

        history = BoundedChatMessageHistory()
        assert history._max_messages == 10


# ---------------------------------------------------------------------------
# Phase 7: End-to-end (requires GEMINI_API_KEY)
# ---------------------------------------------------------------------------


@pytest.mark.skipif(
    not bool(os.getenv("GEMINI_API_KEY")),
    reason="GEMINI_API_KEY not set; add it to .env to run end-to-end tests",
)
class TestAgentE2E:
    """End-to-end agent test with real Gemini LLM and embeddings."""

    def test_e2e_agent_answers_from_transcripts(self, tmp_path):
        from agent import create_agent
        from tools import make_search_transcripts
        from langchain_google_genai import GoogleGenerativeAIEmbeddings

        embedding_function = GoogleGenerativeAIEmbeddings(model="models/gemini-embedding-001")
        store = Chroma(
            collection_name="e2e_test",
            embedding_function=embedding_function,
            persist_directory=str(tmp_path / "chroma"),
        )

        store.add_texts(
            texts=["La migración en el mediterráneo es un tema complejo y peligroso."],
            metadatas=[{
                "video_id": "v100",
                "title": "Cruce del Mediterráneo",
                "chunk_index": 0,
                "start_time": 0.0,
                "end_time": 10.0,
            }],
            ids=["v100_chunk_0"],
        )

        tools = [make_search_transcripts(store, top_k=3)]
        agent = create_agent(tools=tools)
        result = agent.invoke(
            {"input": "¿Qué se dice sobre la migración en el mediterráneo?"},
            {"configurable": {"session_id": "e2e-session"}},
        )
        answer = result.get("output", "")

        assert "mediterráneo" in answer.lower() or "migración" in answer.lower()

        # Clean up the collection so later tests can use a different
        # embedding dimension without hitting a ChromaDB dimension mismatch.
        store.delete_collection()
