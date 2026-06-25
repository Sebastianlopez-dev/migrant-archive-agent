# Spec: agent-conversation

## Requirement: Agent factory uses native tool calling

The system MUST build the conversational agent with `create_tool_calling_agent` and register `search_transcripts`, `list_videos`, and `get_video_info`.

(Previously: only `search_transcripts` was registered.)

### Scenario: Default agent construction

- GIVEN `create_agent()` is called without arguments
- WHEN the factory initializes
- THEN it returns an agent backed by `create_tool_calling_agent`
- AND the runnable is wrapped with `RunnableWithMessageHistory`

### Scenario: Fake tool-calling LLM invokes scoped search

- GIVEN a fake LLM emits an `AIMessage` with `tool_calls` for `search_transcripts` including `video_id`
- WHEN the agent is invoked
- THEN `search_transcripts` runs scoped to that video and returns matching chunks

## Requirement: Agent registers list_videos and get_video_info

The system MUST register `list_videos` and `get_video_info` as callable tools in the agent.

### Scenario: Agent lists videos on ambiguous query

- GIVEN the user asks "what is this about?"
- WHEN the agent runs
- THEN it calls `list_videos()`
- AND it asks the user which video they mean

### Scenario: Agent retrieves video metadata

- GIVEN the user asks "tell me about video X"
- WHEN the agent runs
- THEN it calls `get_video_info(video_id="X")`

## Requirement: Agent reformulates queries before search

The system MUST instruct the LLM to rewrite short or vague queries into descriptive English sentences of at least 3-5 words before calling `search_transcripts`.

### Scenario: Short name reformulation

- GIVEN the user asks "who is Lina?"
- WHEN the agent searches
- THEN `search_transcripts` receives a reformulated descriptive query such as "Who is Lina and what is her role?"

## Requirement: Agent presents results as structured lists

The system MUST instruct the LLM to emit answers as numbered or bulleted lists, never as dense paragraphs.

### Scenario: Search results formatting

- GIVEN `search_transcripts` returns transcript chunks
- WHEN the agent answers
- THEN the final response uses numbered or bulleted list formatting

## Requirement: Conversation history uses InMemoryChatMessageHistory

The system MUST retain conversation context across invocations within the same `session_id` using `InMemoryChatMessageHistory` and `RunnableWithMessageHistory`.

(Previously: used `ConversationBufferMemory` with `memory_key="chat_history"`.)

### Scenario: History accumulates within a session

- GIVEN an agent invoked once with `session_id="session-1"`
- WHEN it is invoked again with the same `session_id`
- THEN the second response has access to the first human/AI exchange

### Scenario: Sessions are isolated

- GIVEN history exists for `session_id="session-1"`
- WHEN the agent is invoked with `session_id="session-2"`
- THEN the new session starts with no prior messages

## Requirement: System prompt is role-focused

The system MUST provide a simplified system prompt that describes the agent role, mandates query reformulation, requires list-formatted output, and lists all three tools.

(Previously: the prompt described only `search_transcripts` and did not require reformulation or list formatting.)

### Scenario: Prompt mentions all tools

- GIVEN the agent is created
- WHEN the system prompt is inspected
- THEN it mentions `search_transcripts`, `list_videos`, and `get_video_info`

### Scenario: Prompt lacks ReAct markers

- GIVEN the agent is created
- WHEN the system prompt is inspected
- THEN it does NOT contain `Thought:`, `Action:`, or `Final Answer:`

## Requirement: CLI passes session_id

The system MUST pass a fixed `session_id` through `agent_cli.py` so the REPL maintains conversation history across queries.

(Previously: the CLI invoked `agent.invoke({"input": query})` without session identity.)

### Scenario: REPL maintains context across turns

- GIVEN the CLI is running interactively
- WHEN the user asks two related questions
- THEN the second answer reflects the context of the first

## Requirement: API endpoint supports session-based history

The system MUST extend `POST /api/ask` to accept and use a `session_id` for conversation history.

(Previously: each request created a fresh agent with no session identity.)

### Scenario: API preserves history within a session

- GIVEN two requests to `/api/ask` with the same `session_id`
- WHEN the second question depends on the first
- THEN the response reflects the prior exchange

### Scenario: API rejects missing API key

- GIVEN `GEMINI_API_KEY` is not configured
- WHEN a request is made to `/api/ask`
- THEN the endpoint returns HTTP 503 with a clear error message

## Requirement: Graceful error handling

The system SHOULD handle missing API key, empty ChromaDB, and LLM failures gracefully.

### Scenario: Empty vector store returns friendly message

- GIVEN the ChromaDB collection contains zero documents
- WHEN `search_transcripts` is invoked
- THEN it returns `No hay transcripciones indexadas aún.`

### Scenario: Missing API key surfaces clear error

- GIVEN `GEMINI_API_KEY` is not configured
- WHEN `create_agent()` defaults to a Gemini LLM
- THEN it raises a clear error before attempting the LLM call

## Requirement: Backward-compatible create_agent signature

The system SHOULD keep the `create_agent(llm, tools, memory, verbose)` signature compatible; the `memory` parameter MAY accept `InMemoryChatMessageHistory` or be ignored in favor of session-scoped history.

### Scenario: Caller passes legacy memory argument

- GIVEN a caller provides a `memory` argument
- WHEN `create_agent()` is invoked
- THEN it does not raise `TypeError`
- AND session-scoped history still takes precedence at invocation time

## Requirement: search_transcripts accepts optional year and channel filters

The system MUST expose `search_transcripts(query, video_id=None, year=None, channel=None)` and apply provided filters to the vector search.
(Previously: only `query` and optional `video_id` were supported.)

### Scenario: Filter search by year

- GIVEN chunks exist for 2023 and 2024
- WHEN the agent calls `search_transcripts("migration", year=2024)`
- THEN only 2024 chunks are returned

### Scenario: Filter search by channel

- GIVEN chunks exist for "Canal 1" and "Canal 2"
- WHEN the agent calls `search_transcripts("border", channel="Canal 1")`
- THEN only chunks from "Canal 1" are returned

### Scenario: Combine filters

- GIVEN chunks exist for multiple years and channels
- WHEN the agent calls `search_transcripts("policy", year=2024, channel="Canal 1")`
- THEN only chunks matching both filters are returned

### Scenario: Scoped search remains supported

- GIVEN chunks exist for video "v1" and "v2"
- WHEN the agent calls `search_transcripts("policy", video_id="v1")`
- THEN only chunks from "v1" are returned

## Requirement: System prompt exposes filter capabilities

The system MUST update the agent system prompt so it mentions that `search_transcripts` supports optional `year` and `channel` filters.
(Previously: the prompt did not mention year or channel filters.)

### Scenario: Prompt mentions filters

- GIVEN the agent is created
- WHEN the system prompt is inspected
- THEN it mentions the optional `year` and `channel` filters for `search_transcripts`
