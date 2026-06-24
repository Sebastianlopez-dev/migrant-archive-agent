# Proposal: Fix Agent ReAct Parsing Failure — Migrate to Native Tool Calling

## Intent

Gemini 2.5 Flash fails to follow the strict text-based ReAct format (`Thought: … Action: …`), causing `create_react_agent` to throw parsing errors and exhaust `max_iterations`. This change replaces text ReAct with Gemini native function calling and modernizes memory from deprecated `ConversationBufferMemory` to `InMemoryChatMessageHistory` + `RunnableWithMessageHistory`.

## Scope

### In Scope
- Rewrite `backend/agents/agent.py` to use `create_tool_calling_agent`.
- Replace `ConversationBufferMemory` with `InMemoryChatMessageHistory` and `RunnableWithMessageHistory`.
- Simplify `SYSTEM_PROMPT` to a role description without ReAct format boilerplate.
- Propagate `session_id` through `agent_cli.py`, `dependencies.py`, and `chat.py`.
- Update `tests/test_agent.py` to match the new agent/memory interface.
- Add `--provider bge-m3` option to `backend/scripts/rag_test.py` for local embeddings.

### Out of Scope
- Changing the `search_transcripts` tool output format.
- Adding persistent chat history storage (remains in-memory).
- Frontend changes or API contract changes beyond `session_id` plumbing.

## Capabilities

### New Capabilities
- None.

### Modified Capabilities
- `agent-conversation`: Replaces ReAct text parsing with native tool calling and migrates memory to the modern LangChain message-history pattern.

## Approach

Use `create_tool_calling_agent(llm, tools, prompt)` so Gemini emits structured `tool_calls` instead of parseable text. Wrap the agent in `RunnableWithMessageHistory`, backed by a dict of `InMemoryChatMessageHistory` instances keyed by `session_id`. Keep tool definitions and the `search_transcripts` implementation unchanged. Update callers to supply a `session_id` and tests to assert on the new runnable return shape and history accumulation.

## Affected Areas

| Area | Impact | Description |
|------|--------|-------------|
| `backend/agents/agent.py` | Modified | Agent factory, prompt, memory, and executor/runnable return type. |
| `backend/scripts/agent_cli.py` | Modified | Pass fixed `session_id` for REPL history. |
| `backend/api/dependencies.py` | Modified | Return runnable and accept/provide `session_id`. |
| `backend/api/routes/chat.py` | Modified | Use `session_id` when invoking the runnable. |
| `tests/test_agent.py` | Modified | Update fake LLM, history assertions, and return-shape checks. |
| `backend/scripts/rag_test.py` | Modified | Add `--provider bge-m3` flag. |

## Risks

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| `create_tool_calling_agent` unsupported by pinned `langchain-*` versions | Low | Verify imports work before implementation; pin or upgrade if needed. |
| Fake LLM in tests cannot simulate `tool_calls` | Med | Extend `FakeChatModel` to emit `AIMessage.tool_calls` or use LangChain's fake tool-calling utilities. |
| `chat.py` source parsing breaks if tool output format changes | Low | Keep `search_transcripts` output format unchanged. |

## Rollback Plan

Revert the commit(s) for this change. The previous `create_react_agent` implementation is self-contained in `agent.py`; restoring it plus the old callers/tests returns the codebase to the prior state.

## Dependencies

- `langchain-classic` / `langchain-core` must expose `create_tool_calling_agent` and `RunnableWithMessageHistory`.
- Existing `langchain-google-genai` must support native tool calling with Gemini.

## Success Criteria

- [ ] `uv run python -m pytest tests/test_agent.py -v` passes.
- [ ] Manual CLI query about an indexed topic returns an answer without `Invalid Format` errors.
- [ ] API `/ask` endpoint answers correctly and preserves history within a session.
- [ ] `rag_test.py --provider bge-m3` runs without requiring `GEMINI_API_KEY`.
