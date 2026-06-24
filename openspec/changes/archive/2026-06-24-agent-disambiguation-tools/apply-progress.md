# Apply Progress: Agent disambiguation tools

## Status

All implementation tasks complete. Full targeted test suite passes. Three pre-existing BGE-M3 tests fail due to torch/transformers CVE-2025-32434 version mismatch in the uv environment (expected; BGE-M3 path requires conda).

## TDD Cycle Evidence

| Task | Test File | Layer | Safety Net | RED | GREEN | TRIANGULATE | REFACTOR |
|------|-----------|-------|------------|-----|-------|-------------|----------|
| 1.1 | `tests/test_vector_store.py` | Unit | ✅ 5/5 | ✅ Written | ✅ Passed | ✅ 4 cases | ✅ Clean |
| 1.2-1.3 | `tests/test_vector_store.py` | Unit | N/A (extends existing) | ✅ Written | ✅ Passed | ✅ 4 cases | ✅ Clean |
| 2.1-2.4 | `tests/test_agent.py` | Unit | ✅ 16/16 | ✅ Written | ✅ Passed | ✅ 6 cases | ✅ Clean |
| 2.5-2.6 | `tests/test_agent.py` | Unit | ✅ 23/23 | ✅ Written | ✅ Passed | ✅ 1 case | ✅ Clean |
| 3.1-3.3 | `tests/test_agent.py` | Unit | ✅ 23/23 | ✅ Written | ✅ Passed | ✅ 3 prompt cases | ✅ Clean |
| 3.4 | `tests/test_agent.py` | Integration | ✅ 23/23 | ✅ Written | ✅ Passed | ✅ 2 fake-LLM cases | ✅ Clean |
| 4.1-4.3 | `tests/test_agent.py`, `tests/test_vector_store.py` | Integration/E2E | ✅ 37/37 | N/A (verification) | ✅ Passed | N/A | N/A |

## Test Summary

- **Total tests written**: 16 new tests
- **Total tests passing**: 137 passed, 3 failed, 1 skipped
- **Layers used**: Unit (13), Integration (3)
- **Approval tests**: None — no refactoring tasks
- **Pure functions created**: `_speaker_from_metadata`, `_year_from_metadata`

## Files Changed

| File | Action | What Was Done |
|------|--------|---------------|
| `backend/core/vector_store.py` | Modified | Added `video_id` parameter to `search()` with ChromaDB `where` filter; added `get_unique_videos()` aggregation. |
| `backend/agents/tools.py` | Modified | Added `make_list_videos` and `make_get_video_info`; extended `make_search_transcripts` with optional `video_id`. |
| `backend/agents/agent.py` | Modified | Updated `SYSTEM_PROMPT` with tool inventory, reformulation, and list-formatting instructions; registered all 3 tools in `create_agent()`. |
| `tests/test_vector_store.py` | Modified | Added `TestVectorStoreVideoScoping` with 4 tests for scoped search and unique-video aggregation. |
| `tests/test_agent.py` | Modified | Added helpers, `TestListVideosTool` (4 tests), `TestGetVideoInfoTool` (2 tests), scoped search test, prompt assertions, and fake-LLM integration tests for new tools; added E2E cleanup to fix in-memory dimension isolation. |
| `openspec/changes/agent-disambiguation-tools/tasks.md` | Modified | Marked all tasks `[x]`. |

## Deviations from Design

- `list_videos` and `get_video_info` read from `data/raw/whisper` (the canonical `VideoData.save_json` output directory) rather than `data/processed/`, matching the design document and existing tooling.
- `get_video_info` summary uses the first 300 characters of `full_text` exactly as designed.

## Issues Found

1. **In-memory ChromaDB dimension isolation**: Running `test_agent.py` before `test_vector_store.py` left a 3072-dimensional in-memory collection from the E2E test, causing later FakeEmbeddingProvider tests (128-dim) to fail with `InvalidArgumentError: Collection expecting embedding with dimension of 3072, got 128`. Fixed by adding `store.delete_collection()` cleanup at the end of the E2E test.
2. **Pre-existing BGE-M3 failures**: `tests/test_embedding_bge_m3.py` fails in the uv environment because `transformers` now requires `torch >= 2.6` for `torch.load` (CVE-2025-32434). This is environmental and unrelated to this change; the project convention documents BGE-M3 as the conda path.

## Verification Results

- `uv run python -m pytest tests/test_agent.py tests/test_vector_store.py -v`: **38 passed**
- `uv run python -m pytest tests/ -v`: **137 passed, 3 failed (BGE-M3 environmental), 1 skipped**
- `uv run python backend/scripts/agent_cli.py` (piped `quit`): starts correctly
- `uv run python backend/scripts/rag_test.py` (piped `quit`): starts correctly, reports 220 indexed chunks
