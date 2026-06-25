# Delta for agent-conversation

## MODIFIED Requirements

### Requirement: search_transcripts accepts optional year and channel filters

The system MUST expose `search_transcripts(query, video_id=None, year=None, channel=None)` and apply provided filters to the vector search.
(Previously: only `query` and optional `video_id` were supported.)

#### Scenario: Filter search by year

- GIVEN chunks exist for 2023 and 2024
- WHEN the agent calls `search_transcripts("migration", year=2024)`
- THEN only 2024 chunks are returned

#### Scenario: Filter search by channel

- GIVEN chunks exist for "Canal 1" and "Canal 2"
- WHEN the agent calls `search_transcripts("border", channel="Canal 1")`
- THEN only chunks from "Canal 1" are returned

#### Scenario: Combine filters

- GIVEN chunks exist for multiple years and channels
- WHEN the agent calls `search_transcripts("policy", year=2024, channel="Canal 1")`
- THEN only chunks matching both filters are returned

#### Scenario: Scoped search remains supported

- GIVEN chunks exist for video "v1" and "v2"
- WHEN the agent calls `search_transcripts("policy", video_id="v1")`
- THEN only chunks from "v1" are returned

### Requirement: System prompt exposes filter capabilities

The system MUST update the agent system prompt so it mentions that `search_transcripts` supports optional `year` and `channel` filters.
(Previously: the prompt did not mention year or channel filters.)

#### Scenario: Prompt mentions filters

- GIVEN the agent is created
- WHEN the system prompt is inspected
- THEN it mentions the optional `year` and `channel` filters for `search_transcripts`
