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
from langchain_core.language_models.chat_models import BaseChatModel

# Load API keys from .env so conditional skips (e.g. E2E) resolve correctly.
load_dotenv()

# Allow imports from backend/core, backend/agents, and backend/scripts.
sys.path.insert(0, str(Path(__file__).parent))
sys.path.insert(0, str(Path(__file__).parent.parent / "backend" / "core"))
sys.path.insert(0, str(Path(__file__).parent.parent / "backend" / "agents"))
sys.path.insert(0, str(Path(__file__).parent.parent / "backend" / "scripts"))

from test_embedding import FakeEmbeddingProvider  # noqa: E402


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


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

        search = make_search_transcripts(provider, store, top_k=3)
        result = search.invoke("migración")

        assert "Testimonio de migración" in result
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

        search = make_search_transcripts(provider, store, top_k=2)
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

        search = make_search_transcripts(provider, store, top_k=5)
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

        search = make_search_transcripts(provider, store, top_k=5)
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

        search = make_search_transcripts(provider, store, top_k=5)
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

        search = make_search_transcripts(provider, store, top_k=5)
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

        list_videos = make_list_videos(tmp_path, store)
        result = list_videos.invoke({})
        parsed = json.loads(result)

        assert len(parsed) == 2
        assert parsed[0]["video_id"] == "v1"
        assert parsed[0]["channel"] == "Canal Lina"
        assert parsed[0]["year"] == 2024
        assert parsed[0]["chunk_count"] == 1
        assert parsed[1]["video_id"] == "v2"
        assert parsed[1]["channel"] == "Canal Ana"
        assert parsed[1]["year"] == 2023
        assert parsed[1]["chunk_count"] == 2

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

        list_videos = make_list_videos(tmp_path, store)
        result = list_videos.invoke({"year": 2024})
        parsed = json.loads(result)

        assert len(parsed) == 1
        assert parsed[0]["title"] == "Video 2024"
        assert parsed[0]["year"] == 2024

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

        list_videos = make_list_videos(tmp_path, store)
        result = list_videos.invoke({"speaker": "Lina"})
        parsed = json.loads(result)

        assert len(parsed) == 1
        assert parsed[0]["title"] == "Video Lina"
        assert parsed[0]["speaker"] == "Lina"

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

        list_videos = make_list_videos(tmp_path, store)
        result = list_videos.invoke({"channel": "Canal 1"})
        parsed = json.loads(result)

        assert len(parsed) == 1
        assert parsed[0]["title"] == "Video Canal 1"
        assert parsed[0]["channel"] == "Canal 1"

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

        list_videos = make_list_videos(tmp_path, store)
        result = list_videos.invoke({"year": 2024, "speaker": "Lina", "channel": "Canal Lina"})
        parsed = json.loads(result)

        assert len(parsed) == 1
        assert parsed[0]["title"] == "Lina 2024"

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

        list_videos = make_list_videos(tmp_path, store)
        result = list_videos.invoke({})
        parsed = json.loads(result)

        assert len(parsed) == 1
        assert parsed[0]["video_id"] == "v1"
        assert parsed[0]["title"] == "Solo en store"
        assert parsed[0]["channel"] == "Canal Store"
        assert parsed[0]["year"] == 2024


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
        store.add(
            ids=["v1_chunk_0", "v1_chunk_1"],
            documents=["a", "b"],
            metadatas=[
                {"video_id": "v1", "title": "Título de prueba", "chunk_index": 0, "channel": "Canal Store", "year": 2024, "speaker": "Lina", "duration": 125},
                {"video_id": "v1", "title": "Título de prueba", "chunk_index": 1, "channel": "Canal Store", "year": 2024, "speaker": "Lina", "duration": 125},
            ],
            embeddings=provider.embed(["a", "b"]),
        )

        get_info = make_get_video_info(tmp_path, store)
        result = get_info.invoke({"video_id": "v1"})
        parsed = json.loads(result)

        assert parsed["title"] == "Título de prueba"
        assert parsed["description"] == "Descripción de prueba"
        assert parsed["year"] == 2024
        assert parsed["duration"] == 125
        assert parsed["channel"] == "Canal Store"
        assert parsed["chunk_count"] == 2
        assert parsed["summary"].startswith("Texto completo")

    def test_get_video_info_missing_video_returns_not_found(self, provider, store, tmp_path):
        from tools import make_get_video_info

        get_info = make_get_video_info(tmp_path, store)
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

        get_info = make_get_video_info(tmp_path, store)
        result = get_info.invoke({"video_id": "v1"})
        parsed = json.loads(result)

        assert parsed["video_id"] == "v1"
        assert parsed["title"] == "Solo en store"
        assert parsed["year"] == 2024
        assert parsed["channel"] == "Canal Store"
        assert parsed["duration"] == 60
        assert parsed["chunk_count"] == 1


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

    def test_system_prompt_mandates_reformulation(self, provider, store):
        from agent import SYSTEM_PROMPT

        assert "rewrite" in SYSTEM_PROMPT.lower() or "reformulate" in SYSTEM_PROMPT.lower()

    def test_system_prompt_requires_list_formatting(self, provider, store):
        from agent import SYSTEM_PROMPT

        assert "numbered" in SYSTEM_PROMPT.lower() or "bulleted" in SYSTEM_PROMPT.lower()

    def test_system_prompt_requires_channel_and_speakers(self, provider, store):
        from agent import SYSTEM_PROMPT

        assert "channel" in SYSTEM_PROMPT.lower()
        assert "speakers" in SYSTEM_PROMPT.lower()
        assert "ponentes" in SYSTEM_PROMPT.lower()
        assert "re-parse" in SYSTEM_PROMPT.lower() or "reparse" in SYSTEM_PROMPT.lower()
        assert "list" in SYSTEM_PROMPT.lower()

    def test_system_prompt_mentions_search_filters(self, provider, store):
        from agent import SYSTEM_PROMPT

        assert "year" in SYSTEM_PROMPT.lower()
        assert "channel" in SYSTEM_PROMPT.lower()
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

        list_videos = make_list_videos(tmp_path, store)
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

        get_info = make_get_video_info(tmp_path, store)
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

        # Clean up the in-memory collection so later tests can use a different
        # embedding dimension without hitting a ChromaDB dimension mismatch.
        store.delete_collection()
