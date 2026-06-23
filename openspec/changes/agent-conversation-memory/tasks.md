# Tasks: Agent Conversation Memory

## Review Workload Forecast

| Field | Value |
|-------|-------|
| Estimated changed lines | ~360 |
| 400-line budget risk | Low |
| Chained PRs recommended | No |
| Decision needed before apply | No |

---

## Phase 1: Dependencies
- [x] 1.1 Add packages to requirements.txt: langchain-classic==1.0.8, langchain-core==1.4.8, langchain-google-genai==4.2.5, filetype==1.2.0
- [x] 1.2 Create empty `backend/agents/__init__.py`
- [x] 1.3 Install packages: `uv pip install -r requirements.txt`

## Phase 2: search_transcripts Tool (TDD)
- [x] 2.1 RED: Write failing tests in `tests/test_agent.py` for `make_search_transcripts` using `FakeEmbeddingProvider` and in-memory `VectorStore`
- [x] 2.2 GREEN: Implement `backend/agents/tools.py` with `make_search_transcripts(provider, store, top_k=3)`
- [x] 2.3 REFACTOR: Run tool tests until green

## Phase 3: Agent Factory (TDD)
- [x] 3.1 RED: Write failing tests for `create_agent()` using `FakeChatModel`
- [x] 3.2 GREEN: Implement `backend/agents/agent.py` with `create_agent()`, Spanish system prompt, `ConversationBufferMemory`, `AgentExecutor`
- [x] 3.3 REFACTOR: Run agent init tests until green

## Phase 4: Memory Accumulation (TDD)
- [x] 4.1 RED: Write failing test for memory accumulation across two invocations
- [x] 4.2 GREEN: Ensure memory_key="chat_history" wiring works
- [x] 4.3 REFACTOR: Run memory tests until green

## Phase 5: CLI REPL
- [x] 5.1 Write tests for `agent_cli.py` mocking input() and create_agent()
- [x] 5.2 Implement `backend/scripts/agent_cli.py` with REPL, welcome message, quit/salir, source display
- [x] 5.3 Run CLI tests until green

## Phase 6: E2E & Full Suite
- [x] 6.1 Write e2e test (skip unless GEMINI_API_KEY set)
- [x] 6.2 Run full test suite and fix failures
- [x] 6.3 Verify CLI launches and exits cleanly
