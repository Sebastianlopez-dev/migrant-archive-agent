"""Pre-compute agent answers for all Q&A pairs — evaluate from cache later."""
import json
import sys
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(_PROJECT_ROOT))
sys.path.insert(0, str(_PROJECT_ROOT / "backend" / "agents"))
sys.path.insert(0, str(_PROJECT_ROOT / "backend" / "core"))

from backend.evaluation.evaluate import (
    load_qa_dataset, invoke_agent, extract_contexts, DEFAULT_QA_DATASET,
)
from backend.agents.agent import create_agent

CACHE_PATH = Path(__file__).with_name("eval_cache.json")

qa = load_qa_dataset(DEFAULT_QA_DATASET)
print(f"Running agent on {len(qa)} questions...")
agent = create_agent()

cache = []
for i, q in enumerate(qa, 1):
    print(f"  [{i}/{len(qa)}] {q['question'][:60]}")
    r = invoke_agent(q["question"], agent=agent)
    cache.append({
        "question": q["question"],
        "answer": str(r.get("output", "")),
        "contexts": extract_contexts(r.get("intermediate_steps", [])),
        "ground_truth": q["ground_truth"],
    })

CACHE_PATH.write_text(json.dumps(cache, indent=2, ensure_ascii=False), encoding="utf-8")
print(f"Saved {len(cache)} results to backend/evaluation/eval_cache.json. Now run: uv run python backend/evaluation/evaluate.py")
