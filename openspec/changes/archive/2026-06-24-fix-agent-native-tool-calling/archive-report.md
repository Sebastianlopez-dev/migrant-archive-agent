# Archive Report: fix-agent-native-tool-calling

**Change**: fix-agent-native-tool-calling  
**Project**: migrant-archive-agent  
**Archived**: 2026-06-24  
**Archive path**: `openspec/changes/archive/2026-06-24-fix-agent-native-tool-calling/`  
**Artifact store mode**: hybrid (Engram + OpenSpec)  
**Archive type**: intentional-with-warnings — one planned work unit was skipped per explicit user request.

## Traceability

| Artifact | Engram observation | OpenSpec file |
|----------|-------------------|---------------|
| Proposal | #1103 | `proposal.md` |
| Spec | #1104 | `spec.md` |
| Design | #1105 | `design.md` |
| Tasks | #1106 | `tasks.md` |
| Apply progress | #1107 | `apply-progress.md` |
| Archive report | this report | `archive-report.md` |

## What Was Implemented

- `backend/agents/agent.py`: Replaced `create_react_agent` with `create_tool_calling_agent`, replaced `ConversationBufferMemory` with `RunnableWithMessageHistory` + `InMemoryChatMessageHistory`, simplified the system prompt, added `_normalize_output` for Gemini list-style answers, and enabled `return_intermediate_steps=True` for source extraction.
- `backend/scripts/agent_cli.py`: Uses `session_id="cli-session"` and passes it via the `configurable` invoke config.
- `backend/api/models.py`: Added `session_id: str = "default"` to `AskRequest`.
- `backend/api/dependencies.py`: Updated return type/docstring to `RunnableWithMessageHistory`.
- `backend/api/routes/chat.py`: Forwards `request.session_id` to the agent and continues parsing `intermediate_steps` into `Source` objects.
- `tests/test_agent.py`: New `FakeToolCallingModel`, updated tests for the new agent contract.
- `tests/test_api.py`: Added `session_id` model and route tests.

## What Was Skipped

Phase 4 (RAG test provider switch) was **explicitly skipped** by user request:

> "Agregar --provider bge-m3 a rag_test.py no es necesario porque no voy a cambiar la dimension de los embeddings por ahora."

Consequently, the following requirements from the delta spec were **not synced** to the main specs:

- `rag-test` domain requirement: `rag_test supports bge-m3 provider`

The skipped tasks remain unchecked in the archived `tasks.md` as a deliberate record of the decision:

- [ ] 4.1 Add `--provider {gemini,bge-m3}` to `backend/scripts/rag_test.py`.
- [ ] 4.2 Skip the `GEMINI_API_KEY` check when `--provider bge-m3` is used.

## Test Results

- Agent tests (`tests/test_agent.py`): 16/16 passing
- API tests (`tests/test_api.py`): 15/16 passing (1 pre-existing ChromaDB dimension flaky test)
- Agent + API combined: 31/32 passing
- Full suite: 115 passed, 1 skipped, 4 failed, 2 errors — all failures pre-existing and unrelated to this change

Pre-existing failures observed:

- `tests/test_api.py::test_search_transcripts_observation_includes_video_id`: flaky ChromaDB in-memory collection dimension reuse.
- `tests/test_embedding_bge_m3.py`: 3 failures due to environment torch version < 2.6.
- `tests/test_pipeline_e2e.py`: 2 setup errors importing non-existent `GeminiProvider` from `embedding_gemini`.

No CRITICAL verification issues were introduced by this change.

## Files Changed

| File | Action | Lines |
|------|--------|-------|
| `backend/agents/agent.py` | Rewrite | +135 / −96 |
| `backend/scripts/agent_cli.py` | Modify | +8 / −5 |
| `backend/api/models.py` | Modify | +4 / −1 |
| `backend/api/dependencies.py` | Modify | +3 / −3 |
| `backend/api/routes/chat.py` | Modify | +12 / −8 |
| `tests/test_agent.py` | Modify | +102 / −22 |
| `tests/test_api.py` | Modify | +54 / −0 |

**Total**: 7 files changed, 443 lines (308 insertions, 135 deletions).

## Delta Specs Synced

| Domain | Action | Details |
|--------|--------|---------|
| `agent-conversation` | Created | `openspec/specs/agent-conversation/spec.md` now contains the new source-of-truth requirements. |
| `rag-test` | Skipped | No main spec created because the only delta requirement (`--provider bge-m3`) was explicitly deferred. |

The `agent-conversation` main spec includes all implemented requirements:

- Agent factory uses native tool calling
- Conversation history uses `InMemoryChatMessageHistory`
- System prompt is role-focused
- CLI passes `session_id`
- API endpoint supports session-based history
- Graceful error handling
- Backward-compatible `create_agent` signature

## Verification Report

No standalone `verify-report` artifact was produced for this change. Verification evidence is captured in:

- `apply-progress.md` (Engram #1107 and OpenSpec `apply-progress.md`)
- Test summaries above

## Final DAG State

```
proposal -> specs -> design -> tasks -> apply -> verify -> archive
                                              ✅       ✅       ✅
```

- `apply`: complete
- `verify`: complete (tests demonstrate spec compliance; no CRITICAL issues)
- `archive`: complete

## Notes and Warnings

- This archive is intentional-with-warnings because Phase 4 was skipped by user request and the corresponding `rag-test` delta spec was not promoted to main specs.
- The skipped `rag_test` work can be resumed later by creating a new change that imports the `rag-test` requirement from the archived `spec.md`.
- Source extraction from `intermediate_steps` remains the migration path until a future change refactors `chat.py` to use the final message list.

## SDD Cycle Complete

The change has been planned, implemented, verified, and archived. Ready for the next change.
