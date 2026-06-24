# Design: Fix Agent ReAct Parsing Failure — Migrate to Native Tool Calling

## Technical Approach

Replace the text-based ReAct loop in `backend/agents/agent.py` with `create_tool_calling_agent` wrapped by `AgentExecutor`, then add per-session memory via `RunnableWithMessageHistory` backed by a dict of `InMemoryChatMessageHistory` instances. This lets Gemini 2.5 Flash emit structured `tool_calls` instead of free-text `Thought/Action` blocks, eliminating the parsing failures that exhaust `max_iterations`. Callers in the CLI and API pass a `session_id` through the `configurable` invoke config; tests are updated to assert the new runnable shape and history retention. `rag_test.py` also gains a `--provider bge-m3` option so local embeddings can be used without a Gemini key.

## Architecture Decisions

### Decision: Agent runtime

| Option | Tradeoff | Decision |
|--------|----------|----------|
| Keep `create_react_agent` + parsing | Zero code churn, but Gemini 2.5 Flash routinely omits `Thought:` and triggers `handle_parsing_errors`, causing loops or wrong outputs. | Reject |
| `create_tool_calling_agent` + `AgentExecutor` | Native tool support in Gemini; no text parsing; preserves `intermediate_steps` for source extraction in `chat.py`. | Choose |
| Raw Gemini API tool calling | Bypasses LangChain patterns already used in the project; loses prompt/memory helpers and consistent error handling. | Reject |
| LangGraph agent graph | More powerful, but overkill for a single-tool conversational agent and adds a new abstraction layer. | Reject |

### Decision: Memory mechanism

| Option | Tradeoff | Decision |
|--------|----------|----------|
| Keep `ConversationBufferMemory` | Deprecated in LangChain 0.3.1+ and couples prompt template to a specific memory key. | Reject |
| `InMemoryChatMessageHistory` + `RunnableWithMessageHistory` | Modern message-history pattern; session-scoped; easy to swap for Redis/DB later. | Choose |
| Persistent DB history (Redis/SQL) | Correct long-term choice, but out of scope for this change and not needed for current in-memory usage. | Reject |

### Decision: Source extraction from tool results

| Option | Tradeoff | Decision |
|--------|----------|----------|
| Parse `intermediate_steps` from `AgentExecutor` output | Existing `chat.py` regex already works with `search_transcripts` output format; minimal change. | Choose |
| Parse from final `messages` list returned by raw tool-calling runnable | Would require rewriting `parse_sources` and changing the API result structure. | Reject |

## Data Flow

```
┌─────────────┐     ┌──────────────────────────────────────────────┐
│ User query  │────→│ RunnableWithMessageHistory                   │
│ + session_id│     │  ├── loads InMemoryChatMessageHistory[session]│
└─────────────┘     │  └── invokes AgentExecutor                    │
                    └──────────────────────┬───────────────────────┘
                                           │
                                           ▼
                    ┌──────────────────────────────────────────────┐
                    │ create_tool_calling_agent                    │
                    │  ├── ChatPromptTemplate (system + history)   │
                    │  └── ChatGoogleGenerativeAI with tools bound │
                    └──────────────────────┬───────────────────────┘
                                           │
              ┌────────────────────────────┼────────────────────────────┐
              │                            │                            │
              ▼                            ▼                            ▼
      ┌───────────────┐          ┌─────────────────┐          ┌──────────────┐
      │ Final Answer  │          │ tool_call       │          │ No results   │
      │ (returned)    │          │ search_transcripts          │ (fallback)   │
      └───────────────┘          └────────┬────────┘          └──────────────┘
                                          │
                                          ▼
                              ┌───────────────────────┐
                              │ make_search_transcripts│
                              │  → embed_query         │
                              │  → VectorStore.search  │
                              │  → formatted string    │
                              └───────────┬───────────┘
                                          │
                                          ▼
                              ┌───────────────────────┐
                              │ Observation injected  │
                              │ into message history  │
                              │ as ToolMessage        │
                              └───────────────────────┘
```

## File Changes

| File | Action | Description |
|------|--------|-------------|
| `backend/agents/agent.py` | Modify | Replace ReAct agent with `create_tool_calling_agent` + `AgentExecutor`; add `InMemoryChatMessageHistory` store and `RunnableWithMessageHistory` wrapper; simplify `SYSTEM_PROMPT`. |
| `backend/scripts/agent_cli.py` | Modify | Pass `{"configurable": {"session_id": "cli-session"}}` on invoke. |
| `backend/api/models.py` | Modify | Add `session_id: str = "default"` to `AskRequest`. |
| `backend/api/dependencies.py` | Modify | Return the history-wrapped runnable; keep the existing GEMINI_API_KEY guard. |
| `backend/api/routes/chat.py` | Modify | Invoke with `configurable={"session_id": request.session_id}`; continue parsing `intermediate_steps` for sources. |
| `backend/scripts/rag_test.py` | Modify | Add `--provider {gemini,bge-m3}`; conditionally import/embed with BGE-M3; skip GEMINI_API_KEY check for local provider. |
| `tests/test_agent.py` | Modify | Update `FakeChatModel` to a tool-calling fake; assert on new runnable return shape and session message history. |

## Interfaces / Contracts

```python
from langchain_classic.agents import AgentExecutor, create_tool_calling_agent
from langchain_core.chat_history import InMemoryChatMessageHistory
from langchain_core.runnables.history import RunnableWithMessageHistory

_sessions: dict[str, InMemoryChatMessageHistory] = {}


def get_session_history(session_id: str) -> BaseChatMessageHistory:
    if session_id not in _sessions:
        _sessions[session_id] = InMemoryChatMessageHistory()
    return _sessions[session_id]


def create_agent(...) -> RunnableWithMessageHistory:
    agent = create_tool_calling_agent(llm, tools, prompt)
    executor = AgentExecutor(agent=agent, tools=tools, max_iterations=10)
    return RunnableWithMessageHistory(
        executor,
        get_session_history,
        input_messages_key="input",
        history_messages_key="chat_history",
    )
```

Invoke contract (all callers):

```python
agent.invoke(
    {"input": question},
    config={"configurable": {"session_id": session_id}},
)
```

## Testing Strategy

| Layer | What to Test | Approach |
|-------|-------------|----------|
| Unit | `create_agent` returns a `RunnableWithMessageHistory` | Assert type and that `get_session_history` is wired. |
| Unit | Fake LLM tool-calling loop | Implement `FakeToolCallingModel` that emits `AIMessage.tool_calls` for `search_transcripts`, then a final answer; verify `AgentExecutor` calls the tool and returns the final answer. |
| Unit | Session history retention | Invoke twice with the same `session_id`; check `InMemoryChatMessageHistory` contains both Human/AI pairs. |
| Unit | Empty store / no results | Reuse existing `search_transcripts` tool tests; format is unchanged. |
| Integration | Real Gemini native tool calling | Run with real `ChatGoogleGenerativeAI` and in-memory ChromaDB; verify answer cites indexed transcript. |
| Integration | API `/ask` session plumbing | Use FastAPI `TestClient`; pass explicit `session_id`; verify follow-up question has context. |
| CLI | `agent_cli.py` session id | Mock the runnable and assert invoked with `configurable={"session_id": "cli-session"}`. |
| RAG | `rag_test.py --provider bge-m3` | Run with BGE-M3 provider and in-memory data; ensure no `GEMINI_API_KEY` required. |

## Migration / Rollout

No data migration is required. The change is a drop-in replacement for the agent factory; the `search_transcripts` tool output format stays the same, so `chat.py` source parsing continues to work. Rollback is a single revert of the affected files.

## Open Questions

- [ ] Does the pinned `langchain-classic` version expose `create_tool_calling_agent`? Verify imports before implementation; upgrade if needed.
- [ ] Should `chat.py` also return the `session_id` to callers so the frontend can reuse it? Currently the request body carries it.
