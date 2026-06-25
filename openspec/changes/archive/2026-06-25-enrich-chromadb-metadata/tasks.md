# Tasks: Enrich ChromaDB Metadata

## Review Workload Forecast

| Field | Value |
|-------|-------|
| Estimated changed lines | 350-450 |
| 400-line budget risk | Medium |
| Chained PRs recommended | No |
| Suggested split | Single PR |
| Delivery strategy | single-pr-default |
| Chain strategy | pending |

Decision needed before apply: No
Chained PRs recommended: No
Chain strategy: pending
400-line budget risk: Medium

## Phase 1: Processor Metadata Enrichment

- [x] 1.1 RED: Add test in `tests/test_processor.py` asserting chunk metadata contains `channel` and `year` from `VideoData.metadata`.
- [x] 1.2 GREEN: Modify `backend/core/processor.py` to extract `channel` and `year` and include them in every chunk's metadata dict.
- [x] 1.3 REFACTOR: Keep metadata construction clean and preserve existing fields (`video_id`, `title`, `speaker`, etc.).

## Phase 2: VectorStore Compound Filters + Catalog

- [x] 2.1 RED: Add test in `tests/test_vector_store.py` for `VectorStore.get_video_metadata()` returning title, year, channel, speaker, duration, and chunk_count.
- [x] 2.2 GREEN: Implement `VectorStore.get_video_metadata(video_id)` in `backend/core/vector_store.py` using the first chunk of the video.
- [x] 2.3 RED: Add test for compound `where` filtering (`video_id` + `year`, `year` + `channel`, `$or` on speaker/channel).
- [x] 2.4 GREEN: Extend `VectorStore.search()` to build ChromaDB `$and`/`$or` clauses from `video_id`, `year`, and `channel`.
- [x] 2.5 REFACTOR: Extract a helper to build the `where` dict so tests can inspect it directly.

## Phase 3: Agent Tools and Prompt

- [x] 3.1 RED: Update `tests/test_agent.py` to assert `search_transcripts`, `list_videos`, and `get_video_info` use new signatures and store-backed metadata.
- [x] 3.2 GREEN: Update `search_transcripts` in `backend/agents/tools.py` to accept and forward `year` and `channel` filters.
- [x] 3.3 GREEN: Update `list_videos` in `backend/agents/tools.py` to return `year` and `channel` derived from `VectorStore`.
- [x] 3.4 GREEN: Update `get_video_info` in `backend/agents/tools.py` to return `year` and `channel` from `VectorStore.get_video_metadata()`.
- [x] 3.5 GREEN: Update the system prompt in `backend/agents/agent.py` to mention optional `year` and `channel` filters.
- [x] 3.6 REFACTOR: Keep JSON files as fallback during transition; do not remove existing readers yet.

## Phase 4: Verification

- [x] 4.1 Run unit and integration tests: `uv run python -m pytest tests/test_processor.py tests/test_vector_store.py tests/test_agent.py -v`.
- [x] 4.2 Run E2E tests if `GEMINI_API_KEY` is set; otherwise confirm they are skipped cleanly.
- [x] 4.3 Fix any regressions and ensure all new scenarios from the spec pass.
