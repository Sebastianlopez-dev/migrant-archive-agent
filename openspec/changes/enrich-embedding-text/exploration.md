# Exploration: enrich-embedding-text

## Current State

The RAG pipeline currently embeds a lossy concatenation of transcript segments:

- `ingestion.py::_build_videodata()` (line 93) builds `full_text` as `" ".join(seg["text"] for seg in segments)`.
- `VideoData` stores `title`, `description`, and `transcript_segments` (with `start`/`duration`), but these fields are never embedded.
- `processor.py::Processor.chunk()` (line 75) reads `video_data.full_text` and chunks it.
- `rag_test.py::build_index()` (lines 52-84) loads saved JSONs and calls `processor.process(video_data)`.
- Existing JSON files already contain `title`, `description`, and `transcript_segments` — but their `full_text` field is the plain concatenation.

Result: the embedding model has no access to the video title, description, or timestamp context, even though all three are available in the data model.

## Affected Areas

- `backend/core/ingestion.py:88-101` — `_build_videodata()` must construct enriched `full_text` for newly ingested videos.
- `backend/core/ingestion.py:31` — `full_text` docstring should reflect that it may include title/description/timestamp prefixes.
- `backend/core/processor.py:70-75` — `Processor.chunk()` currently consumes `video_data.full_text` blindly; needs an on-the-fly enrichment path for legacy JSONs.
- `backend/scripts/rag_test.py:52-84` — `build_index()` loads legacy JSONs and passes them to `processor.process()`; either it or `processor.py` must enrich plain `full_text`.
- `backend/core/ingestion_caption.py:49` — calls `_build_videodata()`, so new captions JSONs inherit enrichment automatically.
- `backend/core/ingestion_audio.py:97` — calls `_build_videodata()`, so new Whisper JSONs inherit enrichment automatically.
- `backend/core/ingestion_colab.py:47-55` — delegates to `ingestion_audio.extract_single_video()`, so new Colab JSONs inherit enrichment automatically.
- `README.md:372-657` — Phase 2 / Embeddings Workflow docs describe chunking but never mention metadata enrichment; should be updated.

## Approaches

### 1. Enrichment helper in `ingestion.py` + optional processor flag

- Add a module-level helper `build_enriched_text(title, description, segments)` in `ingestion.py`.
- `_build_videodata()` uses it for new JSONs.
- `Processor` gets a new optional flag `enrich: bool = False`; when `True`, it calls the helper on `video_data` fields before chunking.
- `rag_test.py::build_index()` instantiates `Processor(..., enrich=True)`.

**Pros:**
- Single source of truth for the enrichment format.
- Existing unit tests keep passing because default behavior is unchanged.
- Backward-compatible: legacy JSONs work when `enrich=True`.

**Cons:**
- Adds a coupling between `processor.py` and `ingestion.py` (helper import).
- Two code paths to maintain.

**Effort:** Low

### 2. Enrichment method on `VideoData`

- Add `VideoData.enriched_text()` that builds the string from `title`, `description`, and `transcript_segments`.
- `_build_videodata()` assigns `full_text = VideoData(...).enriched_text()` (or builds inline then constructs object).
- `Processor.chunk()` calls `video_data.enriched_text()` when available, falling back to `full_text`.

**Pros:**
- Encapsulates the data contract inside `VideoData`.
- `processor.py` stays loosely coupled (only knows about `VideoData` public API).
- Future enrichment changes live in one place.

**Cons:**
- Slightly larger `VideoData` class.
- Need to decide how `VideoData` detects whether `full_text` is already enriched.

**Effort:** Low

### 3. Always enrich in `processor.chunk()` and regenerate `full_text`

- Remove reliance on `video_data.full_text`; `Processor.chunk()` always builds enriched text from `title` + `description` + `transcript_segments`.
- `_build_videodata()` can keep the old plain `full_text` for JSON storage, or also switch to enriched.

**Pros:**
- No conditional logic; processor always uses the richest input.
- Legacy and new JSONs treated identically at embedding time.

**Cons:**
- Breaks `tests/test_processor.py` if tests assert exact chunk text (they do assert exact text in `test_short_text_single_chunk`).
- Changes output of `extract_sample.py` and any code that prints `full_text`.
- May surprise users who expect `full_text` to match the plain transcript.

**Effort:** Medium

## Recommendation

Adopt **Approach 2** (`VideoData.enriched_text()` method) with the following details:

1. Add `VideoData.enriched_text()` that returns:
   ```
   Title: {title}
   Description: {description}

   [MM:SS] segment text
   [MM:SS] segment text
   ...
   ```
2. `_build_videodata()` constructs the enriched string and stores it in `full_text` so new JSONs are born enriched.
3. `Processor.chunk()` calls `video_data.enriched_text()` if `transcript_segments` exist, otherwise falls back to `full_text`. This handles legacy JSONs without re-ingestion.
4. Keep `full_text` field for serialization; existing JSONs load cleanly.

This gives a single source of truth, keeps tests mostly intact, and makes both new and existing JSONs work.

## Risks

- **Token budget increase**: title + description + `[MM:SS]` tokens add overhead. With chunk_size=1000 tokens, a very long description could dominate the first chunk.
- **Chunk text changes**: existing tests that assert exact chunk content will need updating.
- **Description length**: YouTube descriptions can be thousands of characters; may need truncation or separate handling.
- **Timestamp format**: `[MM:SS]` only works up to 59:59. For hour-long videos use `[HH:MM:SS]`.
- **Backward compatibility**: `VideoData.load_json()` must still accept plain `full_text`; no schema change required.
- **Embedding cost**: slightly more tokens per chunk, but still negligible for the project scale.

## Ready for Proposal

Yes. The orchestrator can tell the user:

> Exploration complete. The cleanest path is to add a `VideoData.enriched_text()` method, use it inside `_build_videodata()` for new JSONs, and have `Processor.chunk()` call it as a fallback for legacy JSONs. This touches `backend/core/ingestion.py`, `backend/core/processor.py`, `backend/scripts/rag_test.py` (minor wiring), and README Phase 2 docs. Tests will need small updates for exact chunk-text assertions. Ready to write the proposal.
