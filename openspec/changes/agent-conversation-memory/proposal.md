# Proposal: Agent Conversation Memory

## Intent

Build the first iteration of **Cero**, a LangChain ReAct agent that answers Spanish questions over archived video transcripts while remembering conversation context. This change delivers a CLI-only agent (no FastAPI) with one tool, conversation memory, and a Gemini-backed LLM.

## Scope

### In Scope
- Interactive CLI script `backend/scripts/agent_cli.py`
- LangChain ReAct orchestrator `backend/agents/agent.py`
- One tool `search_transcripts` in `backend/agents/tools.py`
- `ConversationBufferMemory(return_messages=True)` for context
- `ChatGoogleGenerativeAI(model="gemini-2.5-flash")` via `langchain-google-genai`
- Reuse `GeminiEmbeddingProvider` for query embedding before ChromaDB search
- Tests for agent/tool integration

### Out of Scope
- FastAPI endpoint (S06 is CLI-only)
- Additional metadata/analytics tools (2–15 from roadmap)
- SummaryBufferMemory or persistent memory stores
- Auth, rate limiting, deployment

## Approach

```
User input → backend/scripts/agent_cli.py
            → backend/agents/agent.py (ReAct agent)
              → backend/agents/tools.py:search_transcripts
                → GeminiEmbeddingProvider.embed_query()
                → VectorStore.search()
                → ChromaDB
              ← transcript chunks + metadata
            ← Spanish answer with context
```

The CLI loads environment variables, instantiates the agent with memory, and enters a read-eval-print loop. The agent's single tool embeds the user's question using the existing Gemini provider and returns top-k ChromaDB chunks so the LLM can synthesize an answer in Spanish.

## Key Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Agent type | LangChain ReAct | Tool-use loop with built-in reasoning; minimal custom routing |
| LLM | `gemini-2.5-flash` | Already anticipated in `.env.example`; cost-effective for Spanish Q&A |
| Memory | `ConversationBufferMemory` | Simplest correct option; swappable to `SummaryBufferMemory` later |
| Embeddings | `GeminiEmbeddingProvider` | Must match ingestion vectors (3072-dim) or retrieval breaks |
| Interface | CLI only | S06 deliverable; defers FastAPI complexity |

## Dependencies

Install:
- `langchain`
- `langchain-google-genai`

Existing dependencies used:
- `google-genai==2.8.0`
- ChromaDB via `backend/core/vector_store.py`
- `python-dotenv` for env loading

## File Plan

### New
- `backend/agents/agent.py` — ReAct agent orchestrator
- `backend/agents/tools.py` — `search_transcripts` tool
- `backend/scripts/agent_cli.py` — interactive CLI
- `tests/test_agent.py` — integration tests

### Modified
- `pyproject.toml` or `requirements.txt` — add langchain packages
- `.env.example` — confirm `GEMINI_API_KEY` usage

## Risks

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| google-genai/langchain-google-genai version mismatch | Medium | Pin versions; test import after install |
| Spanish ReAct prompt misfires | Medium | Add Spanish system prompt; smoke-test common queries |
| Query/ingestion embedding mismatch | Low | Enforce `GeminiEmbeddingProvider` on both paths |
| Token/cost growth with memory | Low | Buffer memory is small; monitor via logs |

## Rollback Plan

1. Delete new files under `backend/agents/` and `backend/scripts/agent_cli.py`.
2. Remove added langchain packages from dependency files.
3. Revert any `.env.example` changes.
4. Existing RAG pipeline and ingestion remain untouched.

## Success Criteria

- [x] `python backend/scripts/agent_cli.py` starts an interactive prompt.
- [x] Agent answers a Spanish question using transcript search results.
- [x] Agent remembers previous turns within the same session.
- [x] Tests pass: `pytest tests/test_agent.py`.
- [x] No regression in existing `rag_test.py` or embedding tests.
