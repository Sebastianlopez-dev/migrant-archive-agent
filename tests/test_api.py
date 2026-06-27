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
def store(provider, tmp_path):
    """Fresh in-memory ChromaDB collection for the new tool contract."""
    from tests.test_agent import FakeChroma

    s = FakeChroma(provider, str(tmp_path / "chroma"))
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


def test_ask_request_defaults_session_id():
    from backend.api.models import AskRequest

    request = AskRequest(question="¿Cuál es el testimonio de María?")
    assert request.session_id == "default"


def test_ask_request_accepts_session_id():
    from backend.api.models import AskRequest

    request = AskRequest(
        question="¿Cuál es el testimonio de María?",
        session_id="session-123",
    )
    assert request.session_id == "session-123"


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
        self.last_config: dict | None = None

    def invoke(self, inputs: dict, config: dict | None = None):
        self.last_config = config
        return {
            "input": inputs["input"],
            "output": self.answer,
            "intermediate_steps": [(None, self.observation)],
        }


@pytest.fixture
def sample_observation():
    return (
        "[1] Testimonio de María (12.5–18.3) | v001\n"
        "María describe su viaje.\n\n"
        "[2] Testimonio de Juan [Juan Pérez] (20.0–25.0) | v002\n"
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


def test_post_ask_passes_session_id_to_agent(sample_observation):
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
        response = client.post(
            "/api/ask",
            json={
                "question": "¿Qué pasó con María?",
                "session_id": "api-session-123",
            },
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    assert fake_agent.last_config == {
        "configurable": {"session_id": "api-session-123"},
    }


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

    # Ensure a clean collection: ChromaDB in-memory mode can leak state
    # from a previous test that used the same collection name.
    store.delete_collection()
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

    search = make_search_transcripts(store, top_k=3)
    observation = search.invoke("testimonio")

    assert "v003" in observation
    assert "| v003" in observation  # ID at end: Title (...) | VIDEO_ID
    sources = parse_sources([(None, observation)])
    assert len(sources) == 1
    assert sources[0].video_id == "v003"
    assert sources[0].title == "Testimonio de Pedro"


def test_parse_sources_strips_speaker_tag_from_title(provider, store):
    """The regex must strip [Speaker] appended by tools.py from the title."""
    from backend.api.routes.chat import parse_sources
    from tools import make_search_transcripts

    store.delete_collection()
    store.add(
        ids=["v004_chunk_0"],
        documents=["Texto con speaker."],
        metadatas=[{
            "video_id": "v004",
            "title": "Conversatorio FILMIG",
            "speaker": "Nadia Jabr, Mohamad Bitari",
            "chunk_index": 0,
            "start_time": 10.0,
            "end_time": 15.0,
        }],
        embeddings=provider.embed(["Texto con speaker."]),
    )

    search = make_search_transcripts(store, top_k=3)
    observation = search.invoke("speaker")

    # The tools.py header format is: VIDEO_ID | Title [Speaker] (start–end)
    assert "Nadia Jabr" in observation
    sources = parse_sources([(None, observation)])
    assert len(sources) == 1
    assert sources[0].title == "Conversatorio FILMIG"  # speaker stripped
    assert sources[0].video_id == "v004"


# ── linkify_answer ───────────────────────────────────────────────────────


def test_linkify_answer_replaces_video_id_with_full_url_link():
    """linkify_answer must turn a bare video_id into a clickable full-URL link."""
    from backend.api.routes.chat import linkify_answer
    from backend.api.models import Source

    sources = [Source(
        video_id="APgxfNssxGQ",
        title="Test Video",
        start_time="1",
        end_time="143",
        text="...",
    )]
    result = linkify_answer("Watch (APgxfNssxGQ) now", sources)
    assert 'href="https://www.youtube.com/watch?v=APgxfNssxGQ&t=1"' in result
    assert ">https://www.youtube.com/watch?v=APgxfNssxGQ&t=1<" in result
    assert "&amp;" not in result  # the link HTML is raw, surrounding text is escaped


def test_linkify_answer_handles_timestamp_suffix():
    """linkify_answer must swallow an existing &t=N suffix after the video_id."""
    from backend.api.routes.chat import linkify_answer
    from backend.api.models import Source

    sources = [Source(
        video_id="mY1hw79ydY0",
        title="Mujeres del Maiz",
        start_time="470",
        end_time="600",
        text="...",
    )]
    result = linkify_answer("Ver (mY1hw79ydY0&t=470)", sources)
    # The entire "mY1hw79ydY0&t=470" span should be replaced with one link.
    assert result.count("<a ") == 1
    assert ">https://www.youtube.com/watch?v=mY1hw79ydY0&t=470<" in result


def test_linkify_answer_dedup_prevents_nested_links():
    """Two sources sharing the same video_id must NOT produce nested <a> tags."""
    from backend.api.routes.chat import linkify_answer
    from backend.api.models import Source

    sources = [
        Source(video_id="APgxfNssxGQ", title="T1", start_time="1", end_time="143", text="..."),
        Source(video_id="APgxfNssxGQ", title="T2", start_time="101", end_time="212", text="..."),
    ]
    result = linkify_answer("Video: (APgxfNssxGQ&t=1)", sources)
    # Only one <a> tag — no nesting
    assert result.count("<a ") == 1
    assert "</a>" in result


def test_linkify_answer_escapes_html_in_surrounding_text():
    """linkify_answer must escape &lt;script&gt; and similar in the non-link text."""
    from backend.api.routes.chat import linkify_answer
    from backend.api.models import Source

    sources = [Source(
        video_id="X",
        title="T",
        start_time="0",
        end_time="1",
        text="...",
    )]
    result = linkify_answer('Say <script>alert(1)</script> (X)', sources)
    assert "<script>" not in result
    assert "&lt;script&gt;" in result
    # The link for X should still be present
    assert "<a " in result
    assert "youtube.com" in result


def test_build_youtube_url_no_timestamp():
    """_build_youtube_url must omit &t= when seconds is 0."""
    from backend.api.routes.chat import _build_youtube_url
    url = _build_youtube_url("abc123", "0:00")
    assert url == "https://www.youtube.com/watch?v=abc123"


def test_build_youtube_url_with_timestamp():
    """_build_youtube_url must append &t=seconds for non-zero start_time."""
    from backend.api.routes.chat import _build_youtube_url
    url = _build_youtube_url("abc123", "2:05")
    assert url == "https://www.youtube.com/watch?v=abc123&t=125"
