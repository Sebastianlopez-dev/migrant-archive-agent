# Embedding Text Enrichment Specification

## Purpose

Define how `VideoData` produces an enriched text string that includes the video title, description, and per-segment timestamps, and how ingestion and chunking consume that string to improve RAG retrieval.

## Requirements

### Requirement: REQ-ENRICH-001 VideoData enriched text format

`VideoData.enriched_text()` SHALL return a single string containing the title prefix, description prefix, and each transcript segment prefixed by its start timestamp.

#### Scenario: Standard video under one hour

- GIVEN a `VideoData` with title "Interview", description "Migration story", and segments starting at 0s and 65s
- WHEN `enriched_text()` is called
- THEN the result contains `Title: Interview`, `Description: Migration story`, `[00:00]`, and `[01:05]`

### Requirement: REQ-ENRICH-002 New ingestion uses enriched full text

`_build_videodata()` SHALL set `VideoData.full_text` to `enriched_text()` so newly ingested JSONs persist enriched text.

#### Scenario: Ingesting a new video

- GIVEN `_build_videodata()` receives video info and transcript segments
- WHEN it constructs a `VideoData` instance
- THEN `full_text` equals `enriched_text()` and includes title, description, and timestamps

### Requirement: REQ-ENRICH-003 Processor chunks enriched text for legacy JSONs

`Processor.chunk()` SHALL use `video_data.enriched_text()` when `transcript_segments` are present, otherwise fall back to `video_data.full_text`.

#### Scenario: Legacy JSON with transcript segments

- GIVEN a legacy `VideoData` loaded from JSON with plain `full_text` and existing `transcript_segments`
- WHEN `Processor.chunk()` is called
- THEN the chunk text includes title, description, and timestamp prefixes

#### Scenario: Legacy JSON without transcript segments

- GIVEN a `VideoData` where `transcript_segments` is empty
- WHEN `Processor.chunk()` is called
- THEN it uses `video_data.full_text` without enrichment

### Requirement: REQ-ENRICH-004 Chunk metadata carries segment time range

Each `Chunk.metadata` SHALL include `start_time` and `end_time` corresponding to the estimated timestamp of the chunk's first and last characters.

#### Scenario: Chunk spans two segments

- GIVEN a video with segments at 0s and 120s
- WHEN `Processor.chunk()` produces a chunk spanning both segments
- THEN `metadata["start_time"]` is 0.0 and `metadata["end_time"]` is 120.0

### Requirement: REQ-ENRICH-005 Timestamp format adapts to duration

Segment timestamps SHALL be formatted as `[MM:SS]` for videos under one hour and `[HH:MM:SS]` for videos of one hour or longer.

#### Scenario: Hour-long video

- GIVEN a segment starting at 3661 seconds
- WHEN `enriched_text()` formats the timestamp
- THEN the prefix is `[01:01:01]`

#### Scenario: Sub-hour video

- GIVEN a segment starting at 65 seconds
- WHEN `enriched_text()` formats the timestamp
- THEN the prefix is `[01:05]`

### Requirement: REQ-ENRICH-006 Long descriptions do not dominate first chunk

The system SHOULD prevent a long description from consuming the majority of the first chunk by chunking or truncating the description separately from the transcript.

#### Scenario: Description exceeds chunk budget

- GIVEN a video whose description text is longer than the configured chunk size
- WHEN `Processor.chunk()` is called
- THEN the first chunk contains no more than one chunk-size worth of description text
