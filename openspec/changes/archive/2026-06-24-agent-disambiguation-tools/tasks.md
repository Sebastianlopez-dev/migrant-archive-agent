# Tasks: Agent disambiguation tools

## Review Workload Forecast

| Field | Value |
|-------|-------|
| Estimated changed lines | ~340–370 |
| 400-line budget risk | Low |
| Chained PRs recommended | No |
| Suggested split | Single PR |
| Delivery strategy | single-pr-default |
| Chain strategy | pending |

Decision needed before apply: No
Chained PRs recommended: No
Chain strategy: pending
400-line budget risk: Low

## Phase 1: Foundation — VectorStore scoping & catalog

- [x] 1.1 (RED) Write `test_search_with_video_id_filter` and `test_get_unique_videos` in `tests/test_vector_store.py` (~40 lines).
- [x] 1.2 (GREEN) Add `video_id: str | None = None` to `VectorStore.search()` and apply ChromaDB `where` filter in `backend/core/vector_store.py` (~15 lines).
- [x] 1.3 (GREEN) Add `VectorStore.get_unique_videos()` aggregating unique `video_id` values with chunk counts in `backend/core/vector_store.py` (~25 lines).
- [x] 1.4 (REFACTOR) Run `uv run python -m pytest tests/test_vector_store.py -v` and fix warnings.

## Phase 2: Core tools — listing, info, scoped search

- [x] 2.1 (RED) Write unit tests for `make_list_videos` in `tests/test_agent.py`: all videos, filter by year, filter by speaker, combined filters (~50 lines).
- [x] 2.2 (GREEN) Implement `make_list_videos(video_data_dir, store)` in `backend/agents/tools.py` reading `VideoData` JSON and filtering by year/speaker (~40 lines).
- [x] 2.3 (RED) Write unit tests for `make_get_video_info` in `tests/test_agent.py`: existing video and missing video (~30 lines).
- [x] 2.4 (GREEN) Implement `make_get_video_info(video_data_dir, store)` in `backend/agents/tools.py` returning JSON metadata + 300-char summary (~35 lines).
- [x] 2.5 (RED) Add test for `search_transcripts` with `video_id` parameter in `tests/test_agent.py` (~20 lines).
- [x] 2.6 (GREEN) Extend `make_search_transcripts` signature to accept `video_id: str | None = None` and pass it to `store.search()` in `backend/agents/tools.py` (~10 lines).

## Phase 3: Agent assembly & prompt

- [x] 3.1 (RED) Write prompt assertions in `tests/test_agent.py`: `SYSTEM_PROMPT` mentions all three tools, reformulation, list formatting, and lacks ReAct markers (~20 lines).
- [x] 3.2 (GREEN) Update `SYSTEM_PROMPT` in `backend/agents/agent.py` to mention tools, reformulation, and list formatting (~8 lines).
- [x] 3.3 (GREEN) Update `create_agent()` default tools to register `list_videos`, `get_video_info`, and `search_transcripts` in `backend/agents/agent.py` (~10 lines).
- [x] 3.4 (RED) Write integration test with fake LLM emitting `list_videos` and `get_video_info` tool calls in `tests/test_agent.py` (~40 lines).

## Phase 4: Verification

- [x] 4.1 Run full test suite: `uv run python -m pytest tests/test_agent.py tests/test_vector_store.py -v`.
- [x] 4.2 Verify agent CLI still starts: `python backend/scripts/agent_cli.py` (quit immediately).
- [x] 4.3 Run E2E test only if `GEMINI_API_KEY` is set.
