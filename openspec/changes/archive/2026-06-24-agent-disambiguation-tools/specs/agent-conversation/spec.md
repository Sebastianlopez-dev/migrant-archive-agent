# Delta Spec: agent-conversation

## ADDED Requirements

### Requirement: Agent registers list_videos and get_video_info

The system MUST register `list_videos` and `get_video_info` as callable tools in the agent.

#### Scenario: Agent lists videos on ambiguous query

- GIVEN the user asks "what is this about?"
- WHEN the agent runs
- THEN it calls `list_videos()`
- AND it asks the user which video they mean

#### Scenario: Agent retrieves video metadata

- GIVEN the user asks "tell me about video X"
- WHEN the agent runs
- THEN it calls `get_video_info(video_id="X")`

### Requirement: Agent reformulates queries before search

The system MUST instruct the LLM to rewrite short or vague queries into descriptive English sentences of at least 3-5 words before calling `search_transcripts`.

#### Scenario: Short name reformulation

- GIVEN the user asks "who is Lina?"
- WHEN the agent searches
- THEN `search_transcripts` receives a reformulated descriptive query such as "Who is Lina and what is her role?"

### Requirement: Agent presents results as structured lists

The system MUST instruct the LLM to emit answers as numbered or bulleted lists, never as dense paragraphs.

#### Scenario: Search results formatting

- GIVEN `search_transcripts` returns transcript chunks
- WHEN the agent answers
- THEN the final response uses numbered or bulleted list formatting

## MODIFIED Requirements

### Requirement: Agent factory uses native tool calling

The system MUST build the conversational agent with `create_tool_calling_agent` and register `search_transcripts`, `list_videos`, and `get_video_info`.
(Previously: only `search_transcripts` was registered.)

#### Scenario: Default agent construction

- GIVEN `create_agent()` is called without arguments
- WHEN the factory initializes
- THEN it returns an agent backed by `create_tool_calling_agent`
- AND the runnable is wrapped with `RunnableWithMessageHistory`

#### Scenario: Fake tool-calling LLM invokes scoped search

- GIVEN a fake LLM emits an `AIMessage` with `tool_calls` for `search_transcripts` including `video_id`
- WHEN the agent is invoked
- THEN `search_transcripts` runs scoped to that video and returns matching chunks

### Requirement: System prompt is role-focused

The system MUST provide a simplified system prompt that describes the agent role, mandates query reformulation, requires list-formatted output, and lists all three tools.
(Previously: the prompt described only `search_transcripts` and did not require reformulation or list formatting.)

#### Scenario: Prompt mentions all tools

- GIVEN the agent is created
- WHEN the system prompt is inspected
- THEN it mentions `search_transcripts`, `list_videos`, and `get_video_info`

#### Scenario: Prompt lacks ReAct markers

- GIVEN the agent is created
- WHEN the system prompt is inspected
- THEN it does NOT contain `Thought:`, `Action:`, or `Final Answer:`
