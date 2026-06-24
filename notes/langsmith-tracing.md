# LangSmith Tracing — Zero-Code Integration

LangSmith provides observability into every agent run: LLM calls, tool executions,
latency, token usage, and cost. No application code was modified to enable it.

## How it works

Three layers, all existing before LangSmith was added:

**1. LangChain emits events internally.**

`AgentExecutor`, `ChatGoogleGenerativeAI`, and every tool fire lifecycle events
through LangChain's callback system:

```
on_llm_start  → LLM begins generation
on_llm_end    → LLM finished. Tokens: 342. Latency: 1.2s.
on_tool_start → search_transcripts executing...
on_tool_end   → search_transcripts done. 3 chunks returned.
on_chain_start → AgentExecutor iteration begins
on_chain_end   → AgentExecutor iteration ends
```

This callback system is built into LangChain. It runs whether LangSmith is
installed or not — the events are always there, waiting for a listener.

**2. LangSmith registers itself as a listener.**

When Python executes `import langsmith` (triggered by importing any LangChain
module that depends on it), the package checks for `LANGSMITH_TRACING=true`.
If found, it installs a `LangChainTracer` into the global callback manager:

```python
# Internal to langsmith — runs once at import time:
if os.getenv("LANGSMITH_TRACING") == "true":
    register_global_tracer(LangChainTracer(...))
```

From that moment, every LangChain event is captured. No code passes the tracer
explicitly — it sits at the framework level, invisible to application logic.

**3. The tracer builds a span tree and sends it.**

Each `start`/`end` pair becomes a span. Spans are nested by execution order:

```
AgentExecutor (chain span, 2.3s)
├── ChatGoogleGenerativeAI (llm span, 1.2s)
│   └── input: "Que es FILMIG?", output: tool_call to search_transcripts
├── search_transcripts (tool span, 0.4s)
│   └── input: query vector, output: 3 chunks
└── ChatGoogleGenerativeAI (llm span, 0.7s)
    └── input: chunks + history, output: "FILMIG es..."
```

Each span carries metadata: model name, token count, latency, tool name,
video IDs, and error info if something fails. The full tree is sent to
`api.smith.langchain.com`.

## Files involved

| File | Role |
|------|------|
| `requirements.txt` | Declares `langsmith==0.9.1` dependency |
| `.env` | Contains `LANGSMITH_TRACING=true` and API key |
| `backend/agents/agent.py` | **No LangSmith code.** Traced automatically via the callback system. |
| `tests/conftest.py` | Session fixture forces `LANGSMITH_TRACING=false` during pytest |
| `tests/test_langsmith.py` | Verifies the guard fixture works |

## Setup

```bash
# .env
LANGSMITH_TRACING=true
LANGSMITH_API_KEY=lsv2_pt...
LANGSMITH_PROJECT=migrant-archive
LANGSMITH_ENDPOINT=https://api.smith.langchain.com
```

No code changes. Run the agent or API normally. Traces appear at
[smith.langchain.com](https://smith.langchain.com) in the `migrant-archive`
project.

## Test safety

Without a guard, every `pytest` run would send fake LLM traces to LangSmith,
polluting the project with test data and wasting the free tier quota.

`tests/conftest.py` prevents this with a session-scoped autouse fixture:

```python
@pytest.fixture(autouse=True, scope="session")
def _disable_langsmith_tracing():
    os.environ["LANGSMITH_TRACING"] = "false"
    yield
    os.environ.pop("LANGSMITH_TRACING", None)
```

This runs once before any test and restores the original value after the
session ends. `tests/test_langsmith.py` verifies it works.

## Why env vars and not code?

LangChain 1.x intentionally moved tracing from programmatic to environment-driven.
The [v1 migration guide](https://python.langchain.com/docs/versions/v1_migration/)
lists this as a core design change. The rationale: observability is infrastructure
concern. Coupling it to application code creates:

- Boilerplate: every `invoke()` call needs a `callbacks=[tracer]` argument
- Fragility: forgotten tracer → silent gap in observability
- Environment coupling: dev/staging/prod need different code paths

Environment variables decouple all three. Same code, different config.

## Free tier

5,000 traces/month on the free plan. The project's volume (~10 videos, agent
used for development and demo) fits well within this limit.

## References

- [LangSmith Observability Docs](https://docs.smith.langchain.com/observability/how_to_guides/tracing/trace_with_langchain)
- [LangChain v1 Migration Guide](https://python.langchain.com/docs/versions/v1_migration/)
- [LangChain Callbacks System](https://python.langchain.com/docs/modules/callbacks/)
