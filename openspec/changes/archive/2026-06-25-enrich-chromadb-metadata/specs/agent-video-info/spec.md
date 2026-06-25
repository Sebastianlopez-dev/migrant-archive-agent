# Delta for agent-video-info

## MODIFIED Requirements

### Requirement: get_video_info reads channel and year from ChromaDB

The system MUST expose `get_video_info(video_id)` returning `title`, `description`, `year`, `channel`, `duration`, `speaker`, `chunk_count`, and a brief summary derived from ChromaDB metadata.
(Previously: `channel` and `year` were read from JSON files.)

#### Scenario: Retrieve video metadata from vector store

- GIVEN a video with id "v1" is indexed in ChromaDB
- WHEN `get_video_info("v1")` is called
- THEN it returns the video's title, description, year, channel, duration, speaker(s), chunk_count, and a concise summary

#### Scenario: Missing video

- GIVEN no video has id "missing"
- WHEN `get_video_info("missing")` is called
- THEN it returns a clear "video not found" response
