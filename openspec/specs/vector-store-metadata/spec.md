# Spec: vector-store-metadata

## Purpose
ChromaDB chunk metadata becomes the single source of truth for video catalog and semantic filters.

## Requirements

### Requirement: Chunk metadata includes channel and year

The system MUST store `channel` and `year` as metadata fields on every transcript chunk added to ChromaDB.

#### Scenario: Ingested chunk carries metadata

- GIVEN a video with channel "Canal 1" and year 2024
- WHEN the ingestion pipeline chunks and stores transcripts
- THEN each chunk's metadata contains `channel: "Canal 1"` and `year: 2024`

### Requirement: Compound metadata filters

The system MUST support compound `where` filters combining `year`, `channel`, `video_id`, and `speaker` using `$and` and `$or`.

#### Scenario: Filter by year and channel

- GIVEN chunks exist for multiple years and channels
- WHEN a query requests `year=2024` and `channel="Canal 1"`
- THEN only chunks matching both conditions are returned

#### Scenario: Filter by speaker or channel

- GIVEN chunks exist for speaker "Lina" on "Canal 1" and speaker "Ana" on "Canal 2"
- WHEN a query requests `speaker="Lina"` or `channel="Canal 2"`
- THEN chunks matching either condition are returned

### Requirement: Video-level metadata retrieval

The system MUST expose `get_video_metadata(video_id)` returning `title`, `year`, `channel`, `speaker`, `duration`, and `chunk_count` derived from the chunk collection.

#### Scenario: Retrieve existing video metadata

- GIVEN a video "v1" with 5 chunks is indexed
- WHEN `get_video_metadata("v1")` is called
- THEN it returns the title, year, channel, speaker, duration, and chunk_count 5

#### Scenario: Missing video metadata

- GIVEN no chunks exist for video "missing"
- WHEN `get_video_metadata("missing")` is called
- THEN it returns `None` or raises a clear "not found" error
