# Apply Progress: Fix Agent ReAct Parsing Failure — Migrate to Native Tool Calling

## Goal
Implement the migration from ReAct text parsing to native tool calling for the migrant-archive conversational agent, with per-session history via RunnableWithMessageHistory + InMemoryChatMessageHistory, and session_id plumbing through CLI and API.

## What Was Implemented
- Rewrote `backend/agents/agent.py`:
  - Replaced `create_react_agent` + `ConversationBufferMemory` with `create_tool_calling_agent` + `AgentExecutor` + `RunnableWithMessageHistory`.
  - Added module-level `_sessions` dict and `get_session_history(session_id)` helper.
  - Simplified `SYSTEM_PROMPT` (removed ReAct Thought:/Action:/agent_scratchpad instructions).
  - Added `_normalize_output` to coerce Gemini list-style final answers into strings.
  - Added `return_intermediate_steps=True` so `chat.py` can continue parsing sources.
- Updated `tests/test_agent.py`:
  - Replaced `FakeChatModel` with `FakeToolCallingModel` (supports `tool_calls` and `bind_tools`).
  - Added/updated tests for runnable type, history keys, tool-calling loop, session isolation, and CLI session_id config.
- Updated `backend/scripts/agent_cli.py` to pass `{"configurable": {"session_id": "cli-session"}}` on invoke.
- Updated `backend/api/models.py` to add `session_id: str = "default"` to `AskRequest`.
- Updated `backend/api/routes/chat.py` to pass the request session_id on agent invoke.
- Updated `backend/api/dependencies.py` return type and docstring to `RunnableWithMessageHistory`.
- Updated `tests/test_api.py`:
  - Added `AskRequest` session_id default/acceptance tests.
  - Updated `_FakeAgent` to capture config.
  - Added test that `/api/ask` forwards `session_id` to the agent.

## Phase 4 Skipped
Per explicit user instruction, `--provider bge-m3` support in `backend/scripts/rag_test.py` was NOT implemented.

## TDD Cycle Evidence
| Task | Test File | Layer | Safety Net | RED | GREEN | TRIANGULATE | REFACTOR |
|------|-----------|-------|------------|-----|-------|-------------|----------|
| 1.1 FakeToolCallingModel | `tests/test_agent.py` | Unit | ✅ 11/14 (3 pre-existing CLI failures) | ✅ Written | ✅ Passed | ✅ tool call + final answer | ✅ Clean |
| 1.2 RunnableWithMessageHistory | `tests/test_agent.py` | Unit | ✅ 11/14 | ✅ Written | ✅ Passed | ➖ Single scenario | ✅ Clean |
| 1.3 Session history retention | `tests/test_agent.py` | Unit | ✅ 11/14 | ✅ Written | ✅ Passed | ✅ same session + isolation | ✅ Clean |
| 1.4 Tool-calling loop | `tests/test_agent.py` | Unit | ✅ 11/14 | ✅ Written | ✅ Passed | ✅ with real tool + store | ✅ Clean |
| 1.5 API session_id model/route | `tests/test_api.py` | Unit | ✅ 13/16 (isolation/env issues) | ✅ Written | ✅ Passed | ✅ default + explicit session | ✅ Clean |
| 1.6 CLI session_id | `tests/test_agent.py` | Unit | ✅ 11/14 | ✅ Written | ✅ Passed | ➖ Single scenario | ✅ Clean |
| 2.1-2.4 Agent runtime | `tests/test_agent.py` | Unit | ✅ 11/14 | ✅ Tests above | ✅ Passed | ✅ See 1.1-1.4 | ✅ Removed dead imports |
| 3.1-3.4 CLI/API wiring | `tests/test_agent.py`, `tests/test_api.py` | Unit/Integration | ✅ 11/14 | ✅ Tests above | ✅ Passed | ✅ CLI + API routes | ✅ Clean |
| 5.1-5.3 Cleanup/verify | `tests/` | Integration | ✅ 11/14 | N/A (refactor) | ✅ Full suite 115/122 | N/A | ✅ Clean |

## Test Summary
- **Total tests written/updated**: ~12 new/updated tests across `test_agent.py` and `test_api.py`.
- **Agent tests**: 16/16 passing.
- **API tests**: 16/16 passing.
- **Full suite**: 115 passed, 1 skipped, 4 failed, 2 errors (all pre-existing failures unrelated to this change).
- **Layers used**: Unit (primary), Integration (FastAPI TestClient).
- **Approval tests**: None — this was a behavioral migration, not a pure refactor.
- **Pure functions created**: `_normalize_output(result: dict) -> dict` in `agent.py`.

## Pre-existing Failures Observed (Not Caused by This Change)
- `tests/test_api.py::test_search_transcripts_observation_includes_video_id`: flaky due to ChromaDB in-memory collection dimension reuse (3072 vs 128) depending on test order.
- `tests/test_embedding_bge_m3.py`: 3 failures due to environment torch version <2.6 (CVE-2025-32434 block in transformers).
- `tests/test_pipeline_e2e.py`: 2 setup errors importing non-existent `GeminiProvider` from `embedding_gemini`.

## Deviations from Design
- Added `return_intermediate_steps=True` to `AgentExecutor` (design did not specify it but it is required for `chat.py` to keep extracting sources).
- Added `_normalize_output` helper to convert Gemini list-style final answer content into a string (design assumed output was already a string).

## Files Changed
- `backend/agents/agent.py` — rewritten agent factory
- `backend/scripts/agent_cli.py` — session_id plumbing
- `backend/api/models.py` — `AskRequest.session_id`
- `backend/api/routes/chat.py` — pass session_id on invoke
- `backend/api/dependencies.py` — return type/docstring update
- `tests/test_agent.py` — new fake model and tests
- `tests/test_api.py` — session_id model and route tests

## Status
Implementation complete. Ready for `sdd-verify`.
