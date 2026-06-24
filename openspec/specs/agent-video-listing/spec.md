# Spec: agent-video-listing

## Requirement: list_videos returns video catalog

The system MUST expose `list_videos(year=None, speaker=None)` returning, for each video: `video_id`, `title`, `year`, `speaker`, and `chunk_count`.

### Scenario: List all videos

- GIVEN multiple videos are indexed in the vector store
- WHEN the agent calls `list_videos()`
- THEN it returns every video with `video_id`, `title`, `year`, `speaker`, and `chunk_count`

### Scenario: Filter by year

- GIVEN videos exist for 2023 and 2024
- WHEN the agent calls `list_videos(year=2024)`
- THEN only videos whose `year` equals 2024 are returned

### Scenario: Filter by speaker

- GIVEN videos by "Lina" and videos by other speakers
- WHEN the agent calls `list_videos(speaker="Lina")`
- THEN only videos whose speaker matches "Lina" are returned

### Scenario: Combine filters

- GIVEN videos by "Lina" exist in 2023 and 2024
- WHEN the agent calls `list_videos(year=2024, speaker="Lina")`
- THEN only 2024 videos by "Lina" are returned
