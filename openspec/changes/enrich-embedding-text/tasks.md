# Tasks: Enrich Embedding Text with Title, Description, and Timestamps

## Review Workload Forecast

| Field | Value |
|---|---|
| Estimated changed lines | ~210–280 (both PRs) |
| 400-line budget risk | Low |
| Chained PRs recommended | Yes |
| Suggested split | PR #1 ingestion → PR #2 processor/docs |
| Delivery strategy | force-chained |
| Chain strategy | stacked-to-main |

Decision needed before apply: No
Chained PRs recommended: Yes
Chain strategy: stacked-to-main
400-line budget risk: Low

### Suggested Work Units

| Unit | Goal | Likely PR | Notes |
|---|---|---|---|
| 1 | Add `VideoData.enriched_text()` and wire it into `_build_videodata()` | PR #1 | Targets `main`; includes unit tests in new `tests/test_ingestion.py` |
| 2 | Make `Processor.chunk()` use enriched text as fallback and update docs/tests | PR #2 | Targets `main` after PR #1 merges; includes `tests/test_processor.py` updates and README |

---

## Phase 1: PR #1 — Ingestion Enrichment

| # | Task | Files | Est. Lines | Depends on |
|---|---|---|---|---|
| 1.1 | [x] Add module-private `_format_timestamp(seconds, use_hours)` helper that returns `[MM:SS]` or `[HH:MM:SS]` | `backend/core/ingestion.py` | +10 | — |
| 1.2 | [x] Add `VideoData.enriched_text()` returning `Title: …\nDescription: …\n\n[timestamp] segment text` with hour-aware timestamps | `backend/core/ingestion.py` | +25 | 1.1 |
| 1.3 | [x] Update `_build_videodata()` to construct `VideoData` then set `vd.full_text = vd.enriched_text()` | `backend/core/ingestion.py` | +5 / −3 | 1.2 |
| 1.4 | [x] Create `tests/test_ingestion.py` with unit tests for sub-hour format, hour-plus format, empty segments, and `_build_videodata()` persistence | `tests/test_ingestion.py` | +90 (new file) | 1.2, 1.3 |
| 1.5 | [x] Run `pytest tests/test_ingestion.py` and merge PR #1 to `main` | — | — | 1.4 |

---

## Phase 2: PR #2 — Processor Fallback + Documentation

| # | Task | Files | Est. Lines | Depends on |
|---|---|---|---|---|
| 2.1 | [x] Update `Processor.chunk()` to use `video_data.enriched_text()` when `transcript_segments` is non-empty, otherwise `video_data.full_text` | `backend/core/processor.py` | +8 | PR #1 merged |
| 2.2 | [x] Estimate `Chunk.metadata["start_time"]` / `"end_time"` by parsing the first and last `[MM:SS]` / `[HH:MM:SS]` marker in each chunk text | `backend/core/processor.py` | +25 | 2.1 |
| 2.3 | [x] Update exact-text assertions in `tests/test_processor.py` to expect enriched prefix and timestamps | `tests/test_processor.py` | ±25 | 2.1 |
| 2.4 | [x] Add fallback tests: legacy segments enrich, empty segments keep plain `full_text`, chunk metadata time range matches first/last markers | `tests/test_processor.py` | +40 | 2.1, 2.2 |
| 2.5 | [x] Update README Phase 2 chunking docs to mention title/description/timestamp enrichment and legacy fallback | `README.md` | +15 | 2.1 |
| 2.6 | [x] Run full `pytest tests/` and verify `rag_test.py --rebuild` indexes a sample legacy JSON with enriched chunks | — | — | 2.3, 2.4, 2.5 |
| 2.7 | [ ] Merge PR #2 to `main` | — | — | 2.6 |
