"""Tests for the RAGAS evaluation layer.

Covers:
  - QA dataset loading and validation
  - Context extraction from agent intermediate_steps
  - RAGAS dataset construction
  - Evaluation pipeline wiring (unit tests with mocked RAGAS)
  - Missing API key handling
  - End-to-end evaluation (skipped without GEMINI_API_KEY)
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from dotenv import load_dotenv

load_dotenv()

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_PROJECT_ROOT))

from backend.agents.agent import create_agent
from backend.agents.tools import make_search_transcripts
from backend.evaluation.evaluate import (
    DEFAULT_METRICS,
    METRIC_MAP,
    build_metrics,
    build_ragas_dataset,
    build_report,
    compute_averages,
    extract_contexts,
    invoke_agent,
    load_qa_dataset,
    parse_metrics_arg,
    run_evaluation,
)
from datasets import Dataset

sys.path.insert(0, str(_PROJECT_ROOT / "tests"))
from test_agent import FakeChroma, FakeToolCallingModel


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


class _FakeAction:
    """Minimal AgentAction stand-in for context extraction tests."""

    def __init__(self, tool: str, tool_input: dict | None = None) -> None:
        self.tool = tool
        self.tool_input = tool_input or {}


# ---------------------------------------------------------------------------
# QA dataset loading
# ---------------------------------------------------------------------------


class TestLoadQADataset:
    """Unit tests for load_qa_dataset."""

    def test_loads_default_dataset(self):
        data = load_qa_dataset(_PROJECT_ROOT / "backend" / "evaluation" / "qa_dataset.json")
        assert len(data) == 5
        required = {"question", "ground_truth", "contexts_keywords"}
        for i, item in enumerate(data):
            assert required <= set(item.keys()), f"Item {i} missing required fields"
            assert isinstance(item["question"], str) and item["question"].strip()
            assert isinstance(item["ground_truth"], str) and item["ground_truth"].strip()
            assert isinstance(item["contexts_keywords"], list)

    def test_raises_when_file_missing(self, tmp_path):
        with pytest.raises(FileNotFoundError):
            load_qa_dataset(tmp_path / "missing.json")

    def test_raises_when_json_is_not_a_list(self, tmp_path):
        path = tmp_path / "bad.json"
        path.write_text(json.dumps({"question": "What?"}))
        with pytest.raises(ValueError, match="JSON list"):
            load_qa_dataset(path)

    def test_raises_when_required_fields_missing(self, tmp_path):
        path = tmp_path / "bad.json"
        path.write_text(json.dumps([{"question": "What?"}]))
        with pytest.raises(ValueError, match="missing fields"):
            load_qa_dataset(path)

    def test_raises_when_question_is_empty(self, tmp_path):
        path = tmp_path / "bad.json"
        path.write_text(json.dumps([{"question": "", "ground_truth": "Answer", "contexts_keywords": []}]))
        with pytest.raises(ValueError, match="invalid question"):
            load_qa_dataset(path)


# ---------------------------------------------------------------------------
# Context extraction
# ---------------------------------------------------------------------------


class TestExtractContexts:
    """Unit tests for extract_contexts."""

    def test_extracts_all_tool_observations(self):
        steps = [
            (_FakeAction("list_videos"), "1. Video A"),
            (_FakeAction("search_transcripts"), "chunk one"),
            (_FakeAction("get_video_info"), "Title: Video A"),
            (_FakeAction("search_transcripts"), "chunk two"),
        ]
        assert extract_contexts(steps) == [
            "1. Video A", "chunk one", "Title: Video A", "chunk two"
        ]

    def test_returns_empty_for_no_steps(self):
        assert extract_contexts([]) == []

    def test_returns_all_tool_observations(self):
        steps = [
            (_FakeAction("list_videos"), "video list"),
            (_FakeAction("get_video_info"), "video info"),
        ]
        assert extract_contexts(steps) == ["video list", "video info"]

    def test_coerces_observation_to_string(self):
        steps = [(_FakeAction("search_transcripts"), {"text": "chunk"})]
        assert extract_contexts(steps) == ["{'text': 'chunk'}"]


# ---------------------------------------------------------------------------
# Agent invocation
# ---------------------------------------------------------------------------


class TestInvokeAgent:
    """Unit tests for invoke_agent."""

    def test_invokes_with_provided_session_id(self, provider, tmp_path):
        store = FakeChroma(provider, str(tmp_path / "chroma"))
        store.delete_collection()
        store.add(
            ids=["v1_chunk_0"],
            documents=["La migración es un fenómeno global."],
            metadatas=[{"video_id": "v1", "title": "Test", "chunk_index": 0}],
            embeddings=provider.embed(["La migración es un fenómeno global."]),
        )
        search = make_search_transcripts(store, top_k=3)
        llm = FakeToolCallingModel(
            final_answer="Respuesta final.",
            tool_name="search_transcripts",
            tool_args={"query": "migración"},
        )
        agent = create_agent(llm=llm, tools=[search])

        result = invoke_agent("¿Qué es la migración?", session_id="unit-session", agent=agent)

        assert "Respuesta final" in result["output"]
        assert any(step[0].tool == "search_transcripts" for step in result.get("intermediate_steps", []))

    def test_generates_session_id_when_not_provided(self, provider, tmp_path):
        store = FakeChroma(provider, str(tmp_path / "chroma"))
        store.delete_collection()
        agent = create_agent(llm=FakeToolCallingModel(), tools=[])
        result = invoke_agent("Hola", agent=agent)
        assert "Respuesta de prueba" in result["output"]


# ---------------------------------------------------------------------------
# RAGAS dataset construction
# ---------------------------------------------------------------------------


class TestBuildRagasDataset:
    """Unit tests for build_ragas_dataset."""

    def test_builds_dataset_with_contexts(self):
        qa = [
            {"question": "Q1", "ground_truth": "A1", "contexts_keywords": ["k1"]},
            {"question": "Q2", "ground_truth": "A2", "contexts_keywords": ["k2"]},
        ]
        results = [
            {"output": "ans1", "intermediate_steps": [(_FakeAction("search_transcripts"), "ctx1")]},
            {"output": "ans2", "intermediate_steps": [(_FakeAction("search_transcripts"), "ctx2")]},
        ]
        dataset = build_ragas_dataset(qa, results)

        assert isinstance(dataset, Dataset)
        assert dataset["question"] == ["Q1", "Q2"]
        assert dataset["answer"] == ["ans1", "ans2"]
        assert dataset["contexts"] == [["ctx1"], ["ctx2"]]
        assert dataset["ground_truth"] == ["A1", "A2"]

    def test_uses_empty_contexts_when_no_search_steps(self):
        qa = [{"question": "Q1", "ground_truth": "A1", "contexts_keywords": ["k1"]}]
        results = [{"output": "ans1", "intermediate_steps": [(_FakeAction("unknown_tool"), "list")]}]
        dataset = build_ragas_dataset(qa, results)
        assert dataset["contexts"] == [[]]


# ---------------------------------------------------------------------------
# Metric parsing and report helpers
# ---------------------------------------------------------------------------


class TestParseMetricsArg:
    """Unit tests for parse_metrics_arg."""

    def test_default_metrics(self):
        assert parse_metrics_arg(None) == DEFAULT_METRICS

    def test_parses_single_metric(self):
        assert parse_metrics_arg("faithfulness") == ["faithfulness"]

    def test_parses_multiple_metrics(self):
        assert parse_metrics_arg("faithfulness, context_precision") == ["faithfulness", "context_precision"]

    def test_ignores_whitespace_and_case(self):
        assert parse_metrics_arg("  Faithfulness , ANSWER_RELEVANCY ") == ["faithfulness", "answer_relevancy"]

    def test_invalid_metric_raises(self):
        with pytest.raises(ValueError, match="Invalid metrics"):
            parse_metrics_arg("unknown")


class TestBuildMetrics:
    """Unit tests for build_metrics."""

    def test_builds_all_default_metrics(self):
        mock_llm = MagicMock()
        mock_emb = MagicMock()
        metrics = build_metrics(DEFAULT_METRICS, mock_llm, mock_emb)
        assert len(metrics) == len(DEFAULT_METRICS)
        for metric, name in zip(metrics, DEFAULT_METRICS):
            assert isinstance(metric, METRIC_MAP[name])

    def test_answer_relevancy_receives_embeddings(self):
        mock_llm = MagicMock()
        mock_emb = MagicMock()
        metrics = build_metrics(["answer_relevancy"], mock_llm, mock_emb)
        assert metrics[0].embeddings is mock_emb


class TestComputeAverages:
    """Unit tests for compute_averages."""

    def test_averages_per_metric(self):
        scores = [
            {"faithfulness": 1.0, "answer_relevancy": 0.5},
            {"faithfulness": 0.0, "answer_relevancy": 0.5},
        ]
        averages = compute_averages(scores, ["faithfulness", "answer_relevancy"])
        assert averages["faithfulness"] == pytest.approx(0.5)
        assert averages["answer_relevancy"] == pytest.approx(0.5)

    def test_skips_missing_values(self):
        scores = [{"faithfulness": 1.0}, {"faithfulness": None}]
        averages = compute_averages(scores, ["faithfulness"])
        assert averages["faithfulness"] == pytest.approx(1.0)


class TestBuildReport:
    """Unit tests for build_report."""

    def test_report_contains_per_question_and_averages(self):
        scores = [{"faithfulness": 1.0}]
        report = build_report(scores, ["faithfulness"])
        assert report["metric_names"] == ["faithfulness"]
        assert report["per_question"] == scores
        assert report["averages"] == {"faithfulness": 1.0}


# ---------------------------------------------------------------------------
# Evaluation pipeline wiring
# ---------------------------------------------------------------------------


class TestRunEvaluation:
    """Unit tests for run_evaluation with RAGAS mocked."""

    def test_run_evaluation_calls_ragas_evaluate(self, monkeypatch):
        monkeypatch.setenv("GEMINI_API_KEY", "dummy-key-for-unit-test")
        dataset = Dataset.from_dict({
            "question": ["Q1"],
            "answer": ["A1"],
            "contexts": [["C1"]],
            "ground_truth": ["G1"],
        })

        # Mock the scorer to return a known value instead of calling the API
        async def fake_score(_sample):
            return 1.0

        fake_scorer = MagicMock()
        fake_scorer.single_turn_ascore = fake_score

        with patch("backend.evaluation.evaluate.build_metrics", return_value=[fake_scorer]):
            scores = run_evaluation(dataset, ["faithfulness"])

        assert len(scores) == 1
        assert scores[0]["faithfulness"] == 1.0

    def test_run_evaluation_raises_without_api_key(self, monkeypatch):
        monkeypatch.delenv("GEMINI_API_KEY", raising=False)
        dataset = Dataset.from_dict({
            "question": ["Q1"],
            "answer": ["A1"],
            "contexts": [["C1"]],
            "ground_truth": ["G1"],
        })
        with pytest.raises(RuntimeError, match="GEMINI_API_KEY"):
            run_evaluation(dataset, ["faithfulness"])


# ---------------------------------------------------------------------------
# CLI and integration
# ---------------------------------------------------------------------------


class TestCLI:
    """Unit tests for CLI entry points."""

    def test_main_exits_when_api_key_missing(self, monkeypatch, capsys, tmp_path):
        monkeypatch.delenv("GEMINI_API_KEY", raising=False)
        from backend.evaluation.evaluate import main
        from argparse import Namespace
        cache_file = tmp_path / "cache.json"
        cache_file.write_text("[]", encoding="utf-8")
        with patch(
            "backend.evaluation.evaluate.argparse.ArgumentParser.parse_args",
            return_value=Namespace(from_cache=cache_file, output=None, metrics=None),
        ):
            with pytest.raises(SystemExit) as exc:
                main()
        assert exc.value.code == 1
        captured = capsys.readouterr()
        assert "GEMINI_API_KEY" in captured.err


# ---------------------------------------------------------------------------
# End-to-end
# ---------------------------------------------------------------------------


@pytest.mark.skipif(
    not bool(os.getenv("GEMINI_API_KEY")),
    reason="GEMINI_API_KEY not set; add it to .env to run end-to-end evaluation tests",
)
@pytest.mark.slow
class TestEvaluationE2E:
    """End-to-end evaluation using the real agent and Gemini evaluator."""

    def test_e2e_evaluation_on_subset(self, tmp_path):
        dataset_path = _PROJECT_ROOT / "backend" / "evaluation" / "qa_dataset.json"
        qa_pairs = load_qa_dataset(dataset_path)[:3]
        agent = create_agent()

        results = []
        for i, qa in enumerate(qa_pairs):
            result = invoke_agent(qa["question"], session_id=f"e2e-{i}", agent=agent)
            results.append(result)

        dataset = build_ragas_dataset(qa_pairs, results)
        scores = run_evaluation(dataset, ["faithfulness"])

        assert len(scores) == 3
        for row in scores:
            assert "faithfulness" in row
