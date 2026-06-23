# Delta for Agent Conversation Memory

## ADDED Requirements

### Requirement: REQ-AGENT-001 LangChain ReAct agent with memory

The system MUST provide a ReAct agent (`backend/agents/agent.py`) that uses `ChatGoogleGenerativeAI(model="gemini-2.5-flash")` and `ConversationBufferMemory(return_messages=True)`. The agent MUST remember previous question-and-answer pairs within the same session and synthesize answers in Spanish using transcript search results.

#### Scenario: First question about a video topic

- GIVEN the agent is running with an empty conversation buffer
- WHEN the user asks "¿De qué trata el video?"
- THEN the agent SHALL invoke `search_transcripts` with the user's question
- AND the agent SHALL answer in Spanish using the returned transcript chunks

#### Scenario: Follow-up question uses memory context

- GIVEN the agent has already answered a question about a video topic
- WHEN the user asks "¿Y qué más dijo sobre eso?" without naming the topic again
- THEN the agent SHALL use the prior conversation context to resolve the reference
- AND the agent SHALL NOT ask the user to clarify which video or topic they mean

### Requirement: REQ-AGENT-002 search_transcripts tool

The system MUST provide a LangChain tool `search_transcripts` (`backend/agents/tools.py`) that embeds the user's query via `GeminiEmbeddingProvider`, calls `VectorStore.search(query_embedding, top_k=3)`, and returns formatted results containing chunk text, video title, and timestamps.

#### Scenario: Spanish query returns top-3 transcript chunks

- GIVEN a ChromaDB collection populated with transcript chunks and metadata
- WHEN the tool receives a Spanish question
- THEN the tool SHALL embed the query using `GeminiEmbeddingProvider.embed_query()`
- AND the tool SHALL call `VectorStore.search(query_embedding, top_k=3)`
- AND the tool SHALL return up to 3 results formatted with chunk text, video title, start_time, and end_time

### Requirement: REQ-AGENT-003 CLI interface

The system MUST provide an interactive REPL script at `backend/scripts/agent_cli.py`. The script MUST load environment variables from `.env` (including `GEMINI_API_KEY`), print a welcome message in Spanish, accept questions, print answers with sources, and exit when the user types `quit` or `salir`.

#### Scenario: User runs the agent CLI and asks one question

- GIVEN a terminal with `.env` containing `GEMINI_API_KEY`
- WHEN the user runs `python backend/scripts/agent_cli.py`
- THEN the script SHALL print a Spanish welcome message
- AND the script SHALL accept a typed question
- AND the script SHALL print the agent's answer and the sources used

#### Scenario: User exits the CLI

- GIVEN the CLI is waiting for input
- WHEN the user types `quit` or `salir`
- THEN the script SHALL terminate cleanly

### Requirement: REQ-AGENT-004 Memory persistence within session

The system MUST accumulate question-and-answer pairs in `ConversationBufferMemory` across turns within a single CLI session. Follow-up questions that reference prior context MUST be answered correctly using that accumulated memory.

#### Scenario: Third turn references the first turn

- GIVEN a running CLI session with a previous turn-1 question "¿Qué dijo sobre migración?" and a turn-2 follow-up "¿En qué minuto?"
- WHEN the user asks in turn 3 "¿Y por qué lo mencionó?"
- THEN the agent SHALL resolve "lo" as the migration topic from turn 1
- AND the agent SHALL answer based on the prior context without requesting clarification

### Requirement: REQ-AGENT-005 Tests

The system MUST provide tests in `tests/test_agent.py` covering agent initialization, tool result formatting, memory accumulation, and end-to-end question answering.

#### Scenario: Agent initializes without errors

- GIVEN a test fixture with a mock LLM and a mock embedding provider
- WHEN the agent is instantiated
- THEN the agent SHALL initialize without raising an exception

#### Scenario: search_transcripts returns formatted results

- GIVEN an in-memory `VectorStore` populated with documents and a `FakeEmbeddingProvider` that returns deterministic vectors
- WHEN `search_transcripts` is called with a query
- THEN the tool SHALL return results containing chunk text, video title, and timestamps

#### Scenario: ConversationBufferMemory accumulates messages

- GIVEN an agent with `ConversationBufferMemory`
- WHEN two question-and-answer turns are performed
- THEN the memory buffer SHALL contain both human questions and both AI answers

#### Scenario: End-to-end agent answers a question

- GIVEN a populated ChromaDB store and either a real or mocked LLM
- WHEN the agent receives a Spanish question answerable from the transcripts
- THEN the agent SHALL produce an answer that references information from the returned transcript chunks
