# Tasks: Fix Agent ReAct Parsing Failure — Migrate to Native Tool Calling

## Review Workload Forecast

| Field | Value |
|-------|-------|
| Estimated changed lines | 350–500 |
| 400-line budget risk | High |
| Chained PRs recommended | No |
| Suggested split | Single PR with size:exception; optional split: PR1 agent+tests, PR2 CLI/API/rag_test |
| Delivery strategy | single-pr |
| Chain strategy | size-exception |

Decision needed before apply: Yes
Chained PRs recommended: No
Chain strategy: size-exception
400-line budget risk: High

### Suggested Work Units

| Unit | Goal | Commit/PR | Notes |
|------|------|-----------|-------|
| 1 | Agent runtime + tests | PR 1 (size:exception) | Convert `agent.py` and `test_agent.py` to native tool calling |
| 2 | CLI/API session plumbing | PR 1 (size:exception) | Thread `session_id` through CLI and FastAPI layers |
| 3 | RAG test provider switch | PR 1 (size:exception) | Add `--provider bge-m3` to `rag_test.py` |

## Phase 1: RED — Update test fixtures and failing tests

- [x] 1.1 Replace `FakeChatModel` in `tests/test_agent.py` with `FakeToolCallingModel` that emits `AIMessage.tool_calls` and a final-answer `AIMessage`.
- [x] 1.2 Add failing test: `create_agent` returns a `RunnableWithMessageHistory` wired with `input_messages_key="input"` and `history_messages_key="chat_history"`.
- [x] 1.3 Add failing test: two invocations with the same `session_id` retain both Human/AI pairs in `InMemoryChatMessageHistory`.
- [x] 1.4 Add failing test: `FakeToolCallingModel` triggers `search_transcripts`, observes the formatted result, and returns the final answer.
- [x] 1.5 Add failing test: `backend/api/models.py::AskRequest` accepts `session_id` and `chat.py` invokes with `config={"configurable": {"session_id": ...}}`.
- [x] 1.6 Add failing test: `backend/scripts/agent_cli.py` invokes the agent with `config={"configurable": {"session_id": "cli-session"}}`.

## Phase 2: GREEN — Agent runtime

- [x] 2.1 Rewrite `backend/agents/agent.py`: import `create_tool_calling_agent`, `InMemoryChatMessageHistory`, and `RunnableWithMessageHistory`; add `_sessions` dict and `get_session_history` helper.
- [x] 2.2 Simplify `SYSTEM_PROMPT` to remove ReAct `Thought:/Action:` format while keeping Spanish instructions and tool guidance.
- [x] 2.3 Build `create_tool_calling_agent` inside `AgentExecutor`, wrap with `RunnableWithMessageHistory`, and keep `create_agent(llm, tools, verbose)` callable.
- [x] 2.4 Preserve backward-compatible call patterns: `create_agent()`, `create_agent(verbose=True)`, and `create_agent(tools=tools)`.

## Phase 3: GREEN — CLI and API wiring

- [x] 3.1 Update `backend/scripts/agent_cli.py` to pass `config={"configurable": {"session_id": "cli-session"}}` on every `agent.invoke`.
- [x] 3.2 Add `session_id: str = "default"` to `backend/api/models.py::AskRequest`.
- [x] 3.3 Update `backend/api/dependencies.py` return type and docstring to reflect the history-wrapped runnable.
- [x] 3.4 Update `backend/api/routes/chat.py` to invoke the agent with `request.session_id` and continue parsing `intermediate_steps` into `Source` objects.

## Phase 4: GREEN — RAG test provider switch

- [ ] 4.1 Add `--provider {gemini,bge-m3}` to `backend/scripts/rag_test.py` and conditionally instantiate `GeminiEmbeddingProvider` or `BGE_M3EmbeddingProvider`.
- [ ] 4.2 Skip the `GEMINI_API_KEY` check when `--provider bge-m3` is used.

> **SKIPPED per user request**: "Agregar --provider bge-m3 a rag_test.py no es necesario porque no voy a cambiar la dimension de los embeddings por ahora."

## Phase 5: REFACTOR — Cleanup and verification

- [x] 5.1 Remove dead `ConversationBufferMemory` imports and unused ReAct prompt variables from `backend/agents/agent.py`.
- [x] 5.2 Run `uv run python -m pytest tests/ -v` and fix any regressions.
- [x] 5.3 Smoke-test `python backend/scripts/agent_cli.py` and `python backend/scripts/rag_test.py --provider bge-m3 --help`.

> Note: Phase 4 was skipped per explicit user instruction. `rag_test.py` smoke test for `--provider bge-m3 --help` was therefore not applicable; CLI import smoke test passed.
