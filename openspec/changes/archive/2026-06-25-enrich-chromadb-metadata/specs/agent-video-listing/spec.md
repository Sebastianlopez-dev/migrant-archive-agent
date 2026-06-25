# Delta for agent-video-listing

## MODIFIED Requirements

### Requirement: list_videos reads channel and year from ChromaDB

The system MUST expose `list_videos(year=None, speaker=None, channel=None)` returning `video_id`, `title`, `year`, `channel`, `speaker`, and `chunk_count` derived from ChromaDB metadata.
(Previously: `channel` was not returned and data was read from JSON files.)

#### Scenario: List all videos from vector store

- GIVEN multiple videos are indexed in ChromaDB
- WHEN the agent calls `list_videos()`
- THEN it returns every video with `video_id`, `title`, `year`, `channel`, `speaker`, and `chunk_count`

#### Scenario: Filter by year

- GIVEN videos exist for 2023 and 2024
- WHEN the agent calls `list_videos(year=2024)`
- THEN only videos whose `year` equals 2024 are returned

#### Scenario: Filter by speaker

- GIVEN videos by "Lina" and videos by other speakers
- WHEN the agent calls `list_videos(speaker="Lina")`
- THEN only videos whose speaker matches "Lina" are returned

#### Scenario: Filter by channel

- GIVEN videos exist on "Canal 1" and "Canal 2"
- WHEN the agent calls `list_videos(channel="Canal 1")`
- THEN only videos on "Canal 1" are returned

#### Scenario: Combine filters

- GIVEN videos by "Lina" exist on "Canal 1" in 2023 and 2024
- WHEN the agent calls `list_videos(year=2024, speaker="Lina", channel="Canal 1")`
- THEN only 2024 videos by "Lina" on "Canal 1" are returned
