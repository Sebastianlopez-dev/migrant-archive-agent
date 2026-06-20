# Proposal: Enrich Embedding Text with Title, Description, and Timestamps

## Intent

RAG retrieval quality suffers because `VideoData.full_text` is a flat transcript concatenation. The embedding model never sees the video title, description, or segment timestamps, even though all three are present in `VideoData`. This change enriches the text that is chunked and embedded so retrieval can match against richer metadata.

## Scope

### In Scope
- Add `VideoData.enriched_text()` in `backend/core/ingestion.py`.
- Use enriched text as `full_text` in `_build_videodata()` for newly ingested JSONs (Change A).
- Make `Processor.chunk()` fall back to `enriched_text()` when transcript segments exist, so existing legacy JSONs are enriched at chunk time without re-ingestion (Change B).
- Update exact-text unit tests and README Phase 2 docs.

### Out of Scope
- Re-ingesting existing JSONs (handled by Change B fallback).
- Truncation rules for very long descriptions (deferred; current dataset has short descriptions).
- Changing chunking algorithm, embedding provider, or vector-store schema.

## Capabilities

### New Capabilities
- `embedding-text-enrichment`: Build a single enriched string (`Title: ...`, `Description: ...`, `[MM:SS]` segments) from `VideoData` fields and use it during ingestion and chunking.

### Modified Capabilities
- None (no existing OpenSpec specs).

## Approach

Adopt exploration recommendation: Approach 2, `VideoData.enriched_text()`.

1. Add `VideoData.enriched_text()` returning:
   ```
   Title: {title}
   Description: {description}

   [MM:SS] segment text
   ...
   ```
2. `_build_videodata()` stores `full_text = VideoData(...).enriched_text()` so new JSONs are born enriched.
3. `Processor.chunk()` uses `video_data.enriched_text()` when `transcript_segments` are present, otherwise falls back to `video_data.full_text`.
4. Format timestamps as `[HH:MM:SS]` when duration exceeds one hour.

## Affected Areas

| Area | Impact | Description |
|---|---|---|
| `backend/core/ingestion.py` | Modified | Add `enriched_text()`; update `_build_videodata()` and docstring |
| `backend/core/processor.py` | Modified | `chunk()` uses `enriched_text()` fallback |
| `tests/test_processor.py` | Modified | Update exact chunk-text assertions |
| `README.md` | Modified | Document enriched chunking in Phase 2 |

## Risks

| Risk | Likelihood | Mitigation |
|---|---|---|
| Token overhead from title/description/timestamps | Low | Chunk size stays 1000 tokens; overhead small at project scale |
| Long description dominates first chunk | Med | Monitor; defer truncation to a follow-up |
| Existing tests asserting exact chunk text break | High | Update assertions as part of the change |
| Timestamp format breaks after 59:59 | Low | Use `[HH:MM:SS]` for hour-plus videos |

## Rollback Plan

- Revert the commits for Change A and Change B.
- Existing legacy JSONs remain valid because `full_text` and `transcript_segments` are preserved.
- If enriched JSONs were generated after Change A, delete or re-ingest them to return to plain `full_text`.

## Dependencies

- None beyond current `VideoData` schema.

## Success Criteria

- [ ] `pytest` passes after updating exact-text assertions.
- [ ] New ingestion produces JSONs with enriched `full_text`.
- [ ] `rag_test.py --rebuild` indexes legacy JSONs using enriched text without re-ingestion.
- [ ] Retrieved chunks include title/description context and `[MM:SS]` timestamps.
