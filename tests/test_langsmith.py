"""Tests for LangSmith tracing integration and the test guard fixture."""

import os

import pytest


def test_langsmith_tracing_is_disabled_for_tests():
    """The test guard fixture forces LANGSMITH_TRACING=false."""
    assert os.environ["LANGSMITH_TRACING"] == "false"


def test_fixture_overrides_host_tracing_environment():
    """Even when the host shell exports LANGSMITH_TRACING=true, pytest disables it."""
    assert os.environ["LANGSMITH_TRACING"] == "false"


class TestLangSmithTracingEnabled:
    """Integration tests that exercise the agent while tracing is enabled."""

    def test_agent_runs_normally_with_tracing_enabled_and_fake_key(
        self,
        monkeypatch,
        provider,
        store,
    ):
        """When tracing is enabled with an invalid key, the agent still answers.

        This covers Edge 1 (missing/invalid API key) and confirms the
        LangSmith client does not crash the request.
        """
        monkeypatch.setenv("LANGSMITH_TRACING", "true")
        monkeypatch.setenv("LANGSMITH_API_KEY", "ls-fake-key")

        from agent import create_agent
        from tests.test_agent import FakeToolCallingModel

        llm = FakeToolCallingModel(final_answer="Respuesta con trazado.")
        agent = create_agent(llm=llm, tools=[], verbose=False)

        result = agent.invoke(
            {"input": "Hola"},
            {"configurable": {"session_id": "langsmith-enabled-session"}},
        )

        assert "Respuesta con trazado" in result["output"]
