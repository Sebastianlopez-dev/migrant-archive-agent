"""Tests for the FastAPI chat endpoint and supporting API modules.

Covers:
  - Pydantic request/response model validation
  - POST /api/ask with a mocked agent and parsed sources
  - CORS preflight headers
  - Error handling for missing GEMINI_API_KEY
  - Integration test with the real agent (skipped unless GEMINI_API_KEY is set)
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest
from dotenv import load_dotenv

# Load .env so conditional skips resolve correctly.
load_dotenv()


@pytest.fixture
def provider():
    """Deterministic embedding provider for tests."""
    from tests.test_embedding import FakeEmbeddingProvider

    return FakeEmbeddingProvider(dimension=128)


@pytest.fixture
def store():
    """Fresh in-memory ChromaDB collection."""
    from backend.core.vector_store import VectorStore

    s = VectorStore(persist_dir=":memory:")
    yield s
    try:
        s.delete_collection()
    except Exception:
        pass


# Phase 2: Pydantic models ----------------------------------------------------


def test_ask_request_rejects_empty_question():
    """An empty question must fail model validation."""
    from pydantic import ValidationError

    from backend.api.models import AskRequest

    with pytest.raises(ValidationError):
        AskRequest(question="")


def test_ask_request_accepts_valid_question():
    from backend.api.models import AskRequest

    request = AskRequest(question="¿Cuál es el testimonio de María?")
    assert request.question == "¿Cuál es el testimonio de María?"


def test_source_model_requires_all_fields():
    from backend.api.models import Source

    source = Source(
        video_id="v001",
        title="Testimonio de María",
        start_time="12.5",
        end_time="18.3",
        text="María describe su viaje.",
    )
    assert source.video_id == "v001"
    assert source.title == "Testimonio de María"
    assert source.text == "María describe su viaje."


def test_ask_response_shape():
    from backend.api.models import AskRequest, AskResponse, Source

    response = AskResponse(
        answer="María viajó en 2020.",
        sources=[
            Source(
                video_id="v001",
                title="Testimonio de María",
                start_time="12.5",
                end_time="18.3",
                text="María describe su viaje.",
            )
        ],
    )
    assert response.answer == "María viajó en 2020."
    assert len(response.sources) == 1
    assert response.sources[0].video_id == "v001"


# Phase 3: API route ---------------------------------------------------------


class _FakeAgent:
    """Minimal stand-in for AgentExecutor in route tests."""

    def __init__(self, answer: str, observation: str = ""):
        self.answer = answer
        self.observation = observation

    def invoke(self, inputs: dict):
        return {
            "input": inputs["input"],
            "output": self.answer,
            "intermediate_steps": [(None, self.observation)],
        }


@pytest.fixture
def sample_observation():
    return (
        "[1] v001 | Testimonio de María (12.5–18.3)\n"
        "María describe su viaje.\n\n"
        "[2] v002 | Testimonio de Juan (20.0–25.0)\n"
        "Juan describe su viaje."
    )


def test_post_ask_returns_answer_and_sources(sample_observation):
    from fastapi.testclient import TestClient

    from backend.api.dependencies import get_agent
    from backend.api.main import app

    fake_agent = _FakeAgent(
        answer="María viajó en 2020.",
        observation=sample_observation,
    )
    app.dependency_overrides[get_agent] = lambda: fake_agent

    try:
        client = TestClient(app)
        response = client.post("/api/ask", json={"question": "¿Qué pasó con María?"})
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    body = response.json()
    assert body["answer"] == "María viajó en 2020."
    assert len(body["sources"]) == 2
    assert body["sources"][0]["video_id"] == "v001"
    assert body["sources"][0]["title"] == "Testimonio de María"
    assert body["sources"][0]["start_time"] == "12.5"
    assert body["sources"][0]["end_time"] == "18.3"
    assert "María describe su viaje" in body["sources"][0]["text"]
    assert body["sources"][1]["video_id"] == "v002"


def test_post_ask_accepts_no_intermediate_steps():
    from fastapi.testclient import TestClient

    from backend.api.dependencies import get_agent
    from backend.api.main import app

    fake_agent = _FakeAgent(answer="No encontré información relevante.")
    app.dependency_overrides[get_agent] = lambda: fake_agent

    try:
        client = TestClient(app)
        response = client.post("/api/ask", json={"question": "¿Pregunta sin datos?"})
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    body = response.json()
    assert body["answer"] == "No encontré información relevante."
    assert body["sources"] == []


# Phase 4: CORS + error handling ---------------------------------------------


def test_empty_question_returns_422():
    from fastapi.testclient import TestClient

    from backend.api.main import app

    client = TestClient(app)
    response = client.post("/api/ask", json={"question": ""})

    assert response.status_code == 422
    assert "detail" in response.json()


def test_cors_preflight_returns_allowed_origin():
    from fastapi.testclient import TestClient

    from backend.api.main import app

    client = TestClient(app)
    response = client.options(
        "/api/ask",
        headers={
            "Origin": "http://localhost:5173",
            "Access-Control-Request-Method": "POST",
        },
    )

    assert response.status_code == 200
    assert response.headers.get("access-control-allow-origin") == "http://localhost:5173"


def test_missing_api_key_returns_503(monkeypatch):
    from fastapi.testclient import TestClient

    from backend.api.main import app

    monkeypatch.delenv("GEMINI_API_KEY", raising=False)

    client = TestClient(app)
    response = client.post("/api/ask", json={"question": "¿Pregunta?"})

    assert response.status_code == 503
    assert "GEMINI_API_KEY" in response.json()["detail"]


# Phase 8: Integration test (real agent) -------------------------------------


@pytest.mark.skipif(
    not bool(os.getenv("GEMINI_API_KEY")),
    reason="GEMINI_API_KEY not set; add it to .env to run integration tests",
)
def test_post_ask_integration_with_real_agent():
    """End-to-end API call using the real agent when an API key is present."""
    import google.genai.errors
    from fastapi.testclient import TestClient

    from backend.api.main import app

    client = TestClient(app)
    try:
        response = client.post("/api/ask", json={"question": "¿Qué es la migración?"})
    except google.genai.errors.ClientError as exc:
        pytest.skip(f"Gemini API unavailable for integration test: {exc}")

    assert response.status_code == 200
    body = response.json()
    assert isinstance(body["answer"], str)
    assert len(body["answer"]) > 0
    assert isinstance(body["sources"], list)


# Phase 5: Source parsing ------------------------------------------------------


def test_parse_sources_extracts_all_fields(sample_observation):
    from backend.api.models import Source
    from backend.api.routes.chat import parse_sources

    sources = parse_sources([(None, sample_observation)])

    assert len(sources) == 2
    assert sources[0] == Source(
        video_id="v001",
        title="Testimonio de María",
        start_time="12.5",
        end_time="18.3",
        text="María describe su viaje.",
    )
    assert sources[1].video_id == "v002"
    assert sources[1].start_time == "20.0"


def test_parse_sources_returns_empty_list_for_no_steps():
    from backend.api.routes.chat import parse_sources

    assert parse_sources([]) == []
    assert parse_sources(None) == []


def test_search_transcripts_observation_includes_video_id(provider, store):
    """The tool observation must use the [n] VIDEO_ID | Title (start–end) format."""
    from backend.api.routes.chat import parse_sources
    from tools import make_search_transcripts

    store.add(
        ids=["v003_chunk_0"],
        documents=["Contenido del testimonio."],
        metadatas=[{
            "video_id": "v003",
            "title": "Testimonio de Pedro",
            "chunk_index": 0,
            "start_time": 5.0,
            "end_time": 9.0,
        }],
        embeddings=provider.embed(["Contenido del testimonio."]),
    )

    search = make_search_transcripts(provider, store, top_k=3)
    observation = search.invoke("testimonio")

    assert "v003" in observation
    assert "|" in observation
    sources = parse_sources([(None, observation)])
    assert len(sources) == 1
    assert sources[0].video_id == "v003"
    assert sources[0].title == "Testimonio de Pedro"
