# Memory Types in LLM Applications

Reference: [LangChain Memory Migration Guide](
  https://python.langchain.com/docs/versions/migrating_memory/conversation_buffer_memory/
)
and [LangGraph Short-Term Memory](
  https://docs.langchain.com/oss/python/langchain/short-term-memory
)

This document catalogs the canonical memory types for LLM-powered applications,
which ones require an LLM, and how our project implements them.

---

## Taxonomy

### 1. Conversation Buffer Memory

**What it stores**: Every message (human + AI) in a list. No compression, no summarization.

**Requires LLM?**: No, to store. Yes, to interpret (the LLM reads the full history as prompt context).

**Classic API (deprecated)**:
```python
from langchain_classic.memory import ConversationBufferMemory
memory = ConversationBufferMemory()
memory.save_context({"input": "hi"}, {"output": "hello"})
```

**Modern API (LangGraph / RunnableWithMessageHistory)**:
```python
from langchain_core.chat_history import InMemoryChatMessageHistory
from langchain_core.runnables.history import RunnableWithMessageHistory

store = {}
def get_session_history(session_id: str):
    if session_id not in store:
        store[session_id] = InMemoryChatMessageHistory()
    return store[session_id]

agent = RunnableWithMessageHistory(executor, get_session_history, ...)
```

**Our implementation**: `agent.py` line 54 — `_sessions: dict[str, InMemoryChatMessageHistory]`.
This is what powers `agent_cli.py`.

**Risk**: Context window overflow. A long conversation eventualy exceeds the LLM's max tokens.

---

### 2. Conversation Buffer Window Memory

**What it stores**: Only the last K messages. Older messages are dropped (FIFO).

**Requires LLM?**: No, to store. Yes, to interpret.

**Classic API (deprecated)**:
```python
from langchain_classic.memory import ConversationBufferWindowMemory
memory = ConversationBufferWindowMemory(k=5)  # keep last 5 exchanges
```

**Our implementation**: `rag_memory.py` — 120 lines, single-purpose demo.

```python
class SearchRecord:
    def __init__(self, query: str, results: list[dict]):
        self.query = query
        self.result_count = len(results)
        self.video_ids = {r["metadata"]["video_id"] for r in results if ...}

class History:
    def __init__(self):
        self._searches: list[SearchRecord] = []

    def add(self, query, results):
        self._searches.append(SearchRecord(query, results))
        if len(self._searches) > MAX_HISTORY:  # 5
            self._searches.pop(0)
```

No CLI commands except `history`. Everything else is a free-text semantic search.
The `history` command prints the buffer; the user (not an LLM) reads it.

**When to use**: When you want short-term context but cannot afford the context window
cost of the full history. Also useful as a teaching tool: same data structure as
`agent_cli.py`, different consumer (human vs LLM).

---

### 3. Conversation Summary Memory

**What it stores**: A running summary of the conversation, periodically updated by the LLM.

**Requires LLM?**: YES — the LLM generates the summary. This is the first type that
cannot work without an LLM.

**Classic API (deprecated)**:
```python
from langchain_classic.memory import ConversationSummaryMemory
memory = ConversationSummaryMemory(llm=llm)
```

**How it works**:
1. Conversation reaches N messages
2. LLM is called: "Summarize this conversation so far"
3. The summary replaces the full history in the prompt
4. New messages are appended to the summary

**Benefit**: Constant token usage regardless of conversation length.

**Tradeoff**: Information loss — the summary may omit details that become relevant later.

---

### 4. Conversation Summary Buffer Memory

**What it stores**: A summary of old messages + the last K raw messages.

**Requires LLM?**: YES — for summarization.

**Classic API (deprecated)**:
```python
from langchain_classic.memory import ConversationSummaryBufferMemory
memory = ConversationSummaryBufferMemory(llm=llm, max_token_limit=2000)
```

**How it works**: Hybrid of types 2 and 3.
- Old messages are summarized
- Recent messages are kept in full
- The prompt receives: summary + recent messages

**Benefit**: Best of both worlds — context window control + recent detail.

---

### 5. Conversation Entity Memory

**What it stores**: A structured dictionary of entities extracted from the conversation.
Example: `{"Nadia": "speaker in FILMIG 2025 video", "FILMIG": "conference series"}`

**Requires LLM?**: YES — the LLM extracts and updates entities. However, a rule-based
parser can achieve the same result without an LLM.

**Not implemented in our project.**

---

### 6. Conversation Knowledge Graph Memory

**What it stores**: Entities AND their relationships as a knowledge graph.
Example: `(Nadia) -[spoke_at]-> (FILMIG 2025) -[hosted_by]-> (Plataforma Cero)`

**Requires LLM?**: YES — for relationship extraction.

**Not implemented in our project.**

---

### 7. Vector-Store Backed Memory

**What it stores**: Past conversation turns embedded as vectors. Retrieves relevant
past interactions via semantic search rather than recency.

**Requires LLM?**: YES — for embedding + retrieval relevance.

**How it works**:
1. Each conversation turn is embedded and stored in a vector DB
2. On a new query, semantically similar past turns are retrieved
3. Retrieved turns are injected into the LLM prompt as context

**Not implemented in our project.** Could be built on top of our existing ChromaDB store.

---

## Memory Type Summary

| Type | Stores | Needs LLM to store? | Needs LLM to use? | Our implementation |
|---|---|---|---|---|
| Buffer | All messages | No | Yes (reads history as context) | `agent.py` (RunnableWithMessageHistory) |
| Window | Last K messages | No | Yes | `rag_memory.py` (MAX_HISTORY=5) |
| Summary | Running summary | YES | Yes | Not implemented |
| Summary Buffer | Summary + recent K | YES | Yes | Not implemented |
| Entity | Extracted entities | Can be rule-based | No, if rule-based | Not implemented |
| Knowledge Graph | Entities + relations | YES | Yes | Not implemented |
| Vector-Store | Embedded past turns | YES | Yes | Not implemented (possible with ChromaDB) |

---

## Our Project: From Zero Memory to Agent Memory

```
rag_test.py              rag_memory.py               agent_cli.py
───────────              ─────────────               ────────────
No memory                Buffer Window (type 2)       Buffer (type 1)
                         K = 5                        via LLM context
No LLM for memory        No LLM for memory            LLM required
Raw search output        history command              Natural language
```

**Key insight**: The jump from `rag_memory.py` to `agent_cli.py` is NOT about adding
memory — both have memory (a list of past interactions). The jump is about WHO reads it:

- `rag_memory.py`: the user reads `history` output directly
- `agent_cli.py`: Gemini reads `chat_history` as prompt context

Same buffer, different consumer. One is deterministic, the other is semantic.

---

## References

- [LangChain Memory Migration Guide](https://python.langchain.com/docs/versions/migrating_memory/conversation_buffer_memory/)
- [LangGraph Short-Term Memory](https://docs.langchain.com/oss/python/langchain/short-term-memory)
- [Aurelio AI — Conversational Memory in LangChain](https://www.aurelio.ai/learn/langchain-conversational-memory)
- [LangChain + Gemini Function Calling Guide](https://www.philschmid.de/gemini-function-calling)
