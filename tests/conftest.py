"""Shared pytest configuration and import paths."""

import os
import sys
from pathlib import Path

import pytest

_PROJECT_ROOT = Path(__file__).resolve().parent.parent


def pytest_configure(config):
    config.addinivalue_line("markers", "slow: marks tests as slow")

# Several backend modules import sibling packages as top-level names
# (e.g. `from core.embedding import ...`).  Adding these directories to
# sys.path makes the test suite order-independent and robust.
sys.path.insert(0, str(_PROJECT_ROOT / "backend"))
sys.path.insert(0, str(_PROJECT_ROOT / "backend" / "core"))
sys.path.insert(0, str(_PROJECT_ROOT / "backend" / "agents"))
sys.path.insert(0, str(_PROJECT_ROOT / "backend" / "scripts"))


@pytest.fixture
def provider():
    """Deterministic embedding provider for tests."""
    from tests.test_embedding import FakeEmbeddingProvider

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


@pytest.fixture(autouse=True, scope="session")
def _disable_langsmith_tracing():
    """Force LangSmith tracing off for the entire test session.

    This prevents local / CI test runs from sending traces to the
    LangSmith project, even when the host shell has LANGSMITH_TRACING=true.
    """
    original = os.environ.get("LANGSMITH_TRACING")
    os.environ["LANGSMITH_TRACING"] = "false"
    yield
    if original is None:
        os.environ.pop("LANGSMITH_TRACING", None)
    else:
        os.environ["LANGSMITH_TRACING"] = original
