"""RAGAS evaluation CLI for the migrant-archive agent.

Loads cached agent answers from `eval_cache.json` (produced by
`cache_answers.py`), builds a RAGAS dataset, and computes RAGAS metrics using
Gemini as the evaluator.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
import uuid
import warnings
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

load_dotenv()

# Make `from backend.agents.agent import create_agent` work both when running as
# a script and when imported from tests. The agent module uses bare imports such
# as `from tools import ...`, so backend/agents and backend/core must also be
# on sys.path.
_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(_PROJECT_ROOT))
sys.path.insert(0, str(_PROJECT_ROOT / "backend" / "agents"))
sys.path.insert(0, str(_PROJECT_ROOT / "backend" / "core"))

# Ragas 0.4.x still imports ChatVertexAI from the deprecated
# ``langchain_community.chat_models.vertexai`` path, which langchain-community
# 0.4+ removed. Providing a minimal stub module lets ``import ragas`` succeed
# when the project uses Gemini-based evaluation.
try:
    from langchain_community.chat_models.vertexai import ChatVertexAI  # type: ignore # noqa: F401
except ModuleNotFoundError:  # pragma: no cover
    import langchain_community.chat_models
    import types

    _vertexai_stub = types.ModuleType("langchain_community.chat_models.vertexai")

    class _ChatVertexAIStub:  # type: ignore
        """Placeholder for the deprecated ChatVertexAI import."""

        pass

    _vertexai_stub.ChatVertexAI = _ChatVertexAIStub  # type: ignore
    sys.modules["langchain_community.chat_models.vertexai"] = _vertexai_stub
    langchain_community.chat_models.vertexai = _vertexai_stub  # type: ignore

# Filter noisy deprecation warnings from RAGAS internal imports.
warnings.filterwarnings("ignore", category=DeprecationWarning, module="ragas")
warnings.filterwarnings(
    "ignore",
    message=".*Importing.*ragas\\.metrics.*",
    category=DeprecationWarning,
)

from backend.agents.agent import create_agent  # noqa: E402
from datasets import Dataset  # noqa: E402
from langchain_google_genai import (  # noqa: E402
    ChatGoogleGenerativeAI,
    GoogleGenerativeAIEmbeddings,
)
from ragas.dataset_schema import SingleTurnSample  # noqa: E402
from ragas.embeddings import LangchainEmbeddingsWrapper  # noqa: E402
from ragas.llms import LangchainLLMWrapper  # noqa: E402
from ragas.metrics import (  # noqa: E402
    AnswerRelevancy,
    ContextPrecision,
    ContextRecall,
    Faithfulness,
)


DEFAULT_QA_DATASET = Path(__file__).with_name("qa_dataset.json")
DEFAULT_CACHE_PATH = Path(__file__).with_name("eval_cache.json")

METRIC_MAP: dict[str, type] = {
    "faithfulness": Faithfulness,
    "answer_relevancy": AnswerRelevancy,
    "context_precision": ContextPrecision,
    "context_recall": ContextRecall,
}

DEFAULT_METRICS = list(METRIC_MAP.keys())


def load_qa_dataset(path: str | Path) -> list[dict]:
    """Load and validate the Q&A ground-truth dataset.

    Args:
        path: Path to a JSON file containing a list of Q&A records.

    Returns:
        List of validated Q&A dictionaries.

    Raises:
        FileNotFoundError: If the dataset file does not exist.
        ValueError: If the dataset is malformed or missing required fields.
    """
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"QA dataset not found: {path}")

    with path.open(encoding="utf-8") as f:
        data = json.load(f)

    if not isinstance(data, list):
        raise ValueError("QA dataset must be a JSON list.")

    required = {"question", "ground_truth", "contexts_keywords"}
    for i, item in enumerate(data):
        if not isinstance(item, dict):
            raise ValueError(f"Item {i} must be an object.")
        missing = required - set(item.keys())
        if missing:
            raise ValueError(f"Item {i} missing fields: {sorted(missing)}")
        if not isinstance(item.get("question"), str) or not item["question"].strip():
            raise ValueError(f"Item {i} has invalid question.")
        if not isinstance(item.get("ground_truth"), str):
            raise ValueError(f"Item {i} has invalid ground_truth.")

    return data


def extract_contexts(intermediate_steps: list[tuple[Any, Any]]) -> list[str]:
    """Extract retrieved contexts from ALL tool observations.

    Captures observations from ``search_transcripts`` (semantic chunks),
    ``get_video_info`` (metadata), and ``list_videos`` (catalog). The agent
    chooses the right tool per question — all tool outputs are valid context.

    Args:
        intermediate_steps: AgentExecutor intermediate_steps, a list of
            ``(action, observation)`` tuples.

    Returns:
        List of observation strings for every tool action.
    """
    contexts: list[str] = []
    if not intermediate_steps:
        return contexts
    for action, observation in intermediate_steps:
        if getattr(action, "tool", None) in (
            "search_transcripts",
            "get_video_info",
            "list_videos",
        ):
            contexts.append(str(observation))
    return contexts


def invoke_agent(
    question: str,
    session_id: str | None = None,
    agent=None,
) -> dict:
    """Invoke the agent directly and return the raw result.

    Args:
        question: User question.
        session_id: Optional session ID. A fresh UUID is generated if omitted.
        agent: Pre-built agent. If None, ``create_agent()`` is called.

    Returns:
        Agent result dict containing at least ``output`` and
        ``intermediate_steps``.
    """
    if agent is None:
        agent = create_agent()
    if session_id is None:
        session_id = f"eval-{uuid.uuid4().hex[:8]}"
    return agent.invoke(
        {"input": question, "language": "Spanish"},
        {"configurable": {"session_id": session_id}},
    )


def build_ragas_dataset(qa_pairs: list[dict], agent_results: list[dict]) -> Dataset:
    """Build a RAGAS Dataset from Q&A pairs and agent invocation results.

    Args:
        qa_pairs: Validated Q&A records from ``load_qa_dataset``.
        agent_results: Agent result dicts, one per question.

    Returns:
        A Hugging Face ``datasets.Dataset`` with question, answer, contexts,
        and ground_truth columns.
    """
    records: dict[str, list] = {
        "question": [],
        "answer": [],
        "contexts": [],
        "ground_truth": [],
    }
    for qa, result in zip(qa_pairs, agent_results):
        records["question"].append(qa["question"])
        records["answer"].append(str(result.get("output", "")))
        records["contexts"].append(extract_contexts(result.get("intermediate_steps", [])))
        records["ground_truth"].append(qa["ground_truth"])
    return Dataset.from_dict(records)


def build_metrics(
    metric_names: list[str],
    eval_llm,
    eval_embeddings,
):
    """Instantiate RAGAS metrics from names.

    Args:
        metric_names: List of metric keys from ``METRIC_MAP``.
        eval_llm: RAGAS LLM instance (from ``llm_factory``).
        eval_embeddings: RAGAS embeddings instance.

    Returns:
        List of configured RAGAS metric instances.
    """
    metrics = []
    for name in metric_names:
        cls = METRIC_MAP.get(name)
        if cls is None:
            available = ", ".join(METRIC_MAP.keys())
            raise ValueError(f"Unknown metric: {name}. Available: {available}")
        kwargs: dict[str, Any] = {"llm": eval_llm}
        if name == "answer_relevancy":
            kwargs["embeddings"] = eval_embeddings
        metrics.append(cls(**kwargs))
    return metrics


def run_evaluation(
    dataset: Dataset,
    metric_names: list[str],
    api_key: str | None = None,
) -> list[dict]:
    """Run RAGAS evaluation serially — one sample at a time, no parallel workers.

    Uses ``SingleTurnSample`` + ``single_turn_ascore`` to avoid the
    parallel-execution timeouts that ``evaluate()`` triggers with Gemini.

    Args:
        dataset: RAGAS dataset built by ``build_ragas_dataset``.
        metric_names: Metrics to compute.
        api_key: Optional Gemini API key. Defaults to ``GEMINI_API_KEY`` env.

    Returns:
        List of score dictionaries, one per question.
    """
    key = api_key or os.getenv("GEMINI_API_KEY")
    if not key:
        raise RuntimeError("GEMINI_API_KEY is required for RAGAS evaluation.")

    eval_llm = LangchainLLMWrapper(ChatGoogleGenerativeAI(
        model="gemini-2.5-flash",
        google_api_key=key,
        temperature=0,
    ))
    eval_embeddings = LangchainEmbeddingsWrapper(GoogleGenerativeAIEmbeddings(
        model="models/gemini-embedding-2",
        google_api_key=key,
    ))

    # Build one scorer per metric
    scorers = build_metrics(metric_names, eval_llm, eval_embeddings)

    # Evaluate each question serially
    scores: list[dict] = []
    for i in range(len(dataset)):
        sample = SingleTurnSample(
            user_input=dataset[i]["question"],
            response=dataset[i]["answer"],
            retrieved_contexts=dataset[i]["contexts"],
            reference=dataset[i]["ground_truth"],
        )
        row: dict = {}
        for metric_name, scorer in zip(metric_names, scorers):
            try:
                print(f"  [{i+1}/{len(dataset)}] {metric_name}...", end=" ", flush=True)
                score = asyncio.run(scorer.single_turn_ascore(sample))
                row[metric_name] = float(score) if score is not None else None
                print(f"{row[metric_name]}")
            except Exception as e:
                print(f"FAILED: {e}")
                row[metric_name] = None
        scores.append(row)

    return scores


def compute_averages(scores: list[dict], metric_names: list[str]) -> dict[str, float]:
    """Compute average scores per metric, ignoring missing values."""
    averages: dict[str, float] = {}
    for name in metric_names:
        values = [
            row[name]
            for row in scores
            if name in row and row[name] is not None
        ]
        if values:
            averages[name] = sum(values) / len(values)
    return averages


def build_report(scores: list[dict], metric_names: list[str]) -> dict:
    """Build a clean evaluation report with per-question scores and averages."""
    return {
        "metric_names": metric_names,
        "per_question": scores,
        "averages": compute_averages(scores, metric_names),
    }


def parse_metrics_arg(value: str | None) -> list[str]:
    """Parse the ``--metrics`` comma-separated list.

    Args:
        value: Raw CLI value, e.g. ``faithfulness,context_recall``.

    Returns:
        List of normalized metric names.
    """
    if not value:
        return DEFAULT_METRICS
    names = [name.strip().lower() for name in value.split(",") if name.strip()]
    invalid = [name for name in names if name not in METRIC_MAP]
    if invalid:
        available = ", ".join(METRIC_MAP.keys())
        raise ValueError(f"Invalid metrics: {invalid}. Available: {available}")
    return names


def main() -> None:
    """CLI entry point for the evaluation script."""
    parser = argparse.ArgumentParser(
        description="Evaluate the migrant-archive agent with RAGAS from cached answers.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Path to write JSON report",
    )
    parser.add_argument(
        "--metrics",
        type=str,
        default=None,
        help="Comma-separated RAGAS metrics",
    )
    parser.add_argument(
        "--from-cache",
        type=Path,
        default=None,
        help="Path to a cached agent-answers JSON (default: eval_cache.json)",
    )
    args = parser.parse_args()

    cache_path = args.from_cache or DEFAULT_CACHE_PATH
    if not cache_path.exists():
        print(
            "No cache found. Run: uv run python backend/evaluation/cache_answers.py",
            file=sys.stderr,
        )
        sys.exit(1)

    if not os.getenv("GEMINI_API_KEY"):
        print(
            "Error: GEMINI_API_KEY environment variable is required.",
            file=sys.stderr,
        )
        sys.exit(1)

    metric_names = parse_metrics_arg(args.metrics)

    print(f"Reading from cache: {cache_path}")
    cache = json.loads(cache_path.read_text(encoding="utf-8"))
    records: dict[str, list] = {
        "question": [], "answer": [], "contexts": [], "ground_truth": [],
    }
    for item in cache:
        records["question"].append(item["question"])
        records["answer"].append(item["answer"])
        records["contexts"].append(item["contexts"])
        records["ground_truth"].append(item["ground_truth"])
    dataset = Dataset.from_dict(records)
    scores = run_evaluation(dataset, metric_names)

    report = build_report(scores, metric_names)

    print(json.dumps(report, indent=2, ensure_ascii=False))

    if args.output:
        args.output.write_text(
            json.dumps(report, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        print(f"Report written to {args.output}")


if __name__ == "__main__":
    main()
