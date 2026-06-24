# Spec: agent-video-info

## Requirement: get_video_info returns single video metadata

The system MUST expose `get_video_info(video_id)` returning `title`, `description`, `year`, `duration`, `speaker`(s), `chunk_count`, and a brief summary of the video content.

### Scenario: Retrieve video metadata

- GIVEN a video with id "v1" is indexed
- WHEN `get_video_info("v1")` is called
- THEN it returns the video's title, description, year, duration, speaker(s), chunk_count, and a concise summary

### Scenario: Missing video

- GIVEN no video has id "missing"
- WHEN `get_video_info("missing")` is called
- THEN it returns a clear "video not found" response
