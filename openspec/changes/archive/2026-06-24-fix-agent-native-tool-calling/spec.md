# Delta Specs for fix-agent-native-tool-calling

## Domain: agent-conversation

### MODIFIED Requirements

#### Requirement: Agent factory uses native tool calling

The system MUST build the conversational agent with `create_tool_calling_agent` instead of `create_react_agent` so Gemini emits structured `tool_calls` rather than parseable text.

(Previously: used `create_react_agent` with explicit Thought/Action/Final Answer text parsing.)

##### Scenario: Default agent construction

- GIVEN `create_agent()` is called without arguments
- WHEN the factory initializes
- THEN it returns an agent backed by `create_tool_calling_agent`
- AND the runnable is wrapped with `RunnableWithMessageHistory`

##### Scenario: Fake tool-calling LLM invokes search_transcripts

- GIVEN a fake LLM that emits an `AIMessage` with `tool_calls` for `search_transcripts`
- WHEN the agent is invoked with a Spanish question
- THEN `search_transcripts` runs and the final answer is formatted in Spanish

#### Requirement: Conversation history uses InMemoryChatMessageHistory

The system MUST retain conversation context across invocations within the same `session_id` using `InMemoryChatMessageHistory` and `RunnableWithMessageHistory`.

(Previously: used `ConversationBufferMemory` with `memory_key="chat_history"`.)

##### Scenario: History accumulates within a session

- GIVEN an agent invoked once with `session_id="session-1"`
- WHEN it is invoked again with the same `session_id`
- THEN the second response has access to the first human/AI exchange

##### Scenario: Sessions are isolated

- GIVEN history exists for `session_id="session-1"`
- WHEN the agent is invoked with `session_id="session-2"`
- THEN the new session starts with no prior messages

#### Requirement: System prompt is role-focused

The system MUST provide a simplified system prompt that describes the agent role and tool access without ReAct format boilerplate.

(Previously: `SYSTEM_PROMPT` enforced `Thought:`, `Action:`, `Action Input:`, `Observation:`, `Final Answer:` blocks.)

##### Scenario: Prompt lacks ReAct markers

- GIVEN the agent is created
- WHEN the system prompt is inspected
- THEN it does NOT contain `Thought:`, `Action:`, or `Final Answer:`
- AND it states the agent name, Spanish response requirement, and `search_transcripts` availability

#### Requirement: CLI passes session_id

The system MUST pass a fixed `session_id` through `agent_cli.py` so the REPL maintains conversation history across queries.

(Previously: the CLI invoked `agent.invoke({"input": query})` without session identity.)

##### Scenario: REPL maintains context across turns

- GIVEN the CLI is running interactively
- WHEN the user asks two related questions
- THEN the second answer reflects the context of the first

#### Requirement: API endpoint supports session-based history

The system MUST extend `POST /api/ask` to accept and use a `session_id` for conversation history.

(Previously: each request created a fresh agent with no session identity.)

##### Scenario: API preserves history within a session

- GIVEN two requests to `/api/ask` with the same `session_id`
- WHEN the second question depends on the first
- THEN the response reflects the prior exchange

##### Scenario: API rejects missing API key

- GIVEN `GEMINI_API_KEY` is not configured
- WHEN a request is made to `/api/ask`
- THEN the endpoint returns HTTP 503 with a clear error message

#### Requirement: Graceful error handling

The system SHOULD handle missing API key, empty ChromaDB, and LLM failures gracefully.

##### Scenario: Empty vector store returns friendly message

- GIVEN the ChromaDB collection contains zero documents
- WHEN `search_transcripts` is invoked
- THEN it returns `No hay transcripciones indexadas aún.`

##### Scenario: Missing API key surfaces clear error

- GIVEN `GEMINI_API_KEY` is not configured
- WHEN `create_agent()` defaults to a Gemini LLM
- THEN it raises a clear error before attempting the LLM call

### ADDED Requirements

#### Requirement: Backward-compatible create_agent signature

The system SHOULD keep the `create_agent(llm, tools, memory, verbose)` signature compatible; the `memory` parameter MAY accept `InMemoryChatMessageHistory` or be ignored in favor of session-scoped history.

##### Scenario: Caller passes legacy memory argument

- GIVEN a caller provides a `memory` argument
- WHEN `create_agent()` is invoked
- THEN it does not raise `TypeError`
- AND session-scoped history still takes precedence at invocation time

## Domain: rag-test

### ADDED Requirements

#### Requirement: rag_test supports bge-m3 provider

The system MUST support a `--provider bge-m3` option in `backend/scripts/rag_test.py` so the script can run without `GEMINI_API_KEY`.

##### Scenario: Run rag_test with bge-m3

- GIVEN a local BGE-M3 embedding environment is available
- WHEN `rag_test.py --provider bge-m3` is executed
- THEN it uses the BGE-M3 provider and does not require `GEMINI_API_KEY`

##### Scenario: Default provider remains gemini

- GIVEN no `--provider` argument is passed
- WHEN `rag_test.py` is executed
- THEN it uses `GeminiEmbeddingProvider` as before
