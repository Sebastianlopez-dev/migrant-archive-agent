# Design: Agent Conversation Memory

## Technical Approach

Build a single Spanish ReAct agent (`Cero`) using `langchain-classic`, `langchain-google-genai`, and `ConversationBufferMemory`. The agent exposes one tool, `search_transcripts`, which embeds the query with the existing `GeminiEmbeddingProvider`, queries the existing `VectorStore` (ChromaDB), and returns formatted transcript chunks. A CLI script wraps the agent in a REPL.

## Architecture Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| LangChain package | `langchain-classic` 1.0.8 | The PyPI `langchain` 1.3.x line is the new prebuilt-agent package; the classic `AgentExecutor` / `create_react_agent` / `ConversationBufferMemory` APIs moved to `langchain-classic`, which is required for compatibility with `langchain-core` 1.x and `langchain-google-genai` 4.x. |
| Agent construction | `create_react_agent` + `AgentExecutor` | Gives explicit control over the prompt and memory wiring while staying on the classic stack; avoids adding `langgraph`. |
| Memory | `ConversationBufferMemory(return_messages=True, memory_key="chat_history")` | Matches the spec; simplest correct option for single-session context. |
| Tool dependencies | Factory-scoped singletons | `create_agent()` builds one `GeminiEmbeddingProvider` and one `VectorStore`, then injects them into `search_transcripts` via a closure. Avoids recreating clients each turn and keeps tests mockable. |
| Embeddings | `GeminiEmbeddingProvider` only | Ingestion already writes 3072-dim Gemini vectors; any other provider would break retrieval. |
| Memory deprecation note | `ConversationBufferMemory` is deprecated in LangChain 1.0 | The class remains fully functional in `langchain-classic` and is the correct API for LangChain 0.3.x. Migration to the newer `create_agent` with checkpointing is planned when LangChain 2.0 is released. See [LangChain short-term memory docs](https://docs.langchain.com/oss/python/langchain/short-term-memory). |

## Data Flow

```
User ──► backend/scripts/agent_cli.py
           │
           ▼
      backend/agents/agent.py
      create_agent(llm, tools, memory)
           │
           ▼
      backend/agents/tools.py:search_transcripts(query)
           │
           ▼
      GeminiEmbeddingProvider.embed_query()
           │
           ▼
      VectorStore.search(top_k=3)
           │
           ▼
      ChromaDB
           │
           └── chunks + metadata ──► LLM ──► Spanish answer
```

## File Changes

| File | Action | Description |
|------|--------|-------------|
| `backend/agents/__init__.py` | Create | Package marker (empty). |
| `backend/agents/agent.py` | Create | `create_agent()` factory and Spanish ReAct prompt. |
| `backend/agents/tools.py` | Create | `search_transcripts` tool with embedding + vector search. |
| `backend/scripts/agent_cli.py` | Create | Interactive REPL, env loading, welcome message. |
| `tests/test_agent.py` | Create | Unit + integration tests for agent, tool, memory, e2e. |
| `requirements.txt` | Modify | Add `langchain-classic`, `langchain-core`, `langchain-google-genai`, `filetype`. |

## Interfaces / Contracts

### `backend/agents/agent.py`

```python
from langchain_classic.agents import AgentExecutor, create_react_agent
from langchain_classic.memory import ConversationBufferMemory
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_google_genai import ChatGoogleGenerativeAI

def create_agent(
    llm: ChatGoogleGenerativeAI | None = None,
    tools: list | None = None,
    memory: ConversationBufferMemory | None = None,
    verbose: bool = False,
) -> AgentExecutor:
    ...
```

System prompt (Spanish):

```text
Eres Cero, un asistente que responde en español sobre testimonios migratorios archivados.
Usa la herramienta search_transcripts para buscar fragmentos relevantes.
Responde en español, cita el video y el rango de tiempo cuando sea posible, y no inventes información.
```

Prompt template:

```python
prompt = ChatPromptTemplate.from_messages([
    ("system", SYSTEM_PROMPT),
    MessagesPlaceholder(variable_name="chat_history"),
    ("human", "{input}"),
    MessagesPlaceholder(variable_name="agent_scratchpad"),
])
```

### `backend/agents/tools.py`

```python
from langchain_core.tools import tool

def make_search_transcripts(provider, store, top_k: int = 3):
    @tool
    def search_transcripts(query: str) -> str:
        """Search archived video transcripts for a given query."""
        if store.count == 0:
            return "No hay transcripciones indexadas aún."
        embedding = provider.embed_query(query)
        results = store.search(embedding, top_k=top_k)
        if not results:
            return "No se encontraron resultados relevantes."
        return "\n\n".join(
            f"[{i+1}] {m.get('title', m.get('video_id'))} "
            f"({m.get('start_time', '?')}–{m.get('end_time', '?')})\n{r['document']}"
            for i, r in enumerate(results)
            for m in [r.get("metadata", {})]
        )
    return search_transcripts
```

### `backend/scripts/agent_cli.py`

```python
def main() -> None:
    load_dotenv()
    # validate GEMINI_API_KEY
    agent = create_agent()
    print("Bienvenido a Cero. Escribe 'quit' o 'salir' para salir.")
    while True:
        query = input("Pregunta> ").strip()
        if query.lower() in ("quit", "salir", "q"):
            break
        result = agent.invoke({"input": query})
        print(result["output"])
```

## Testing Strategy

| Layer | What to Test | Approach |
|-------|-------------|----------|
| Unit | `search_transcripts` formatting and error paths | `FakeEmbeddingProvider` + in-memory `VectorStore`; assert returned string contains title, timestamps, chunk text. |
| Unit | Agent initialization | Inject a fake `BaseChatModel`; assert `AgentExecutor` created with memory. |
| Integration | Memory accumulation | Invoke agent twice with a fake LLM; verify `memory.chat_memory.messages` contains both Human/AI message pairs. |
| E2E | Real LLM + populated store | Skip unless `GEMINI_API_KEY` is set; assert Spanish answer references transcript content. |

Fake chat model sketch (tests):

```python
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessage
from langchain_core.outputs import ChatResult, ChatGeneration

class FakeChatModel(BaseChatModel):
    responses: list[str]
    _idx: int = 0
    def _generate(self, messages, stop=None, **kwargs):
        text = self.responses[self._idx % len(self.responses)]
        self._idx += 1
        return ChatResult(generations=[ChatGeneration(message=AIMessage(content=text))])
```

## Package Dependencies

Add to `requirements.txt`:

```text
langchain-classic==1.0.8
langchain-core==1.4.8
langchain-google-genai==4.2.5
filetype==1.2.0
```

### Compatibility Matrix

| Package | Required by | Current project | Status |
|---------|-------------|-----------------|--------|
| `google-genai` | `langchain-google-genai` | `2.8.0` | Compatible (requires `>=1.65.0,<3.0.0`). |
| `pydantic` | `langchain-classic`, `langchain-google-genai` | `2.13.4` | Compatible (requires `>=2.0.0,<3.0.0`). |
| `langchain-core` | `langchain-classic`, `langchain-google-genai` | absent | Add `1.4.8`. |
| `filetype` | `langchain-google-genai` | absent | Add `1.2.0`. |

## Migration / Rollout

No migration required. Existing ingestion, `rag_test.py`, and ChromaDB data remain untouched.

## Open Questions

- None.
