# Cero-01 Checklist

Current state of `cero-01.py` and what remains to replicate the full Cero agent (`agent_cli.py`).

---

## What cero-01 has (Session June 27, 2026)

| Category | Item | Status |
|----------|------|:---:|
| **Runtime** | `#!/usr/bin/env python3` | ✅ |
| | `load_dotenv()` + `_ensure_api_key()` | ✅ |
| **Config** | `GEMINI_CHAT_MODEL` (gemini-2.5-flash) | ✅ |
| | `CHROMA_DIR`, `CHROMA_COLLECTION` | ✅ |
| | `TOP_K = 3`, `MAX_TURNS = 5` | ✅ |
| **Embedding** | `GoogleGenerativeAIEmbeddings` (langchain_google_genai) | ✅ |
| **Vector Store** | `Chroma` (langchain_chroma) | ✅ |
| | `_store.as_retriever(search_kwargs={"k": TOP_K})` | ✅ |
| **LLM** | `ChatGoogleGenerativeAI` (temperature=0.2) | ✅ |
| **Chain** | `ConversationalRetrievalChain.from_llm()` | ✅ |
| | Custom prompt ("You are Cero...") | ✅ |
| | `return_source_documents=True` | ✅ |
| **Memory** | `ConversationBufferWindowMemory(k=5)` with `output_key="answer"` | ✅ |
| **REPL** | Single-shot: `python cero-01.py "pregunta"` | ✅ |
| | Interactive REPL: `python cero-01.py` | ✅ |
| | `--verbose` flag (shows source documents) | ✅ |
| | `history` command (shows last N messages) | ✅ |
| | `quit` / `salir` / `q` to exit | ✅ |
| **Architecture** | Read-only (uses existing ChromaDB, no ingestion) | ✅ |
| | Autocontenido (0 imports from `backend/core/`) | ✅ |
| | No comments or docstrings | ✅ |

---

## What's missing to match agent_cli.py

| Category | Item | Priority |
|----------|------|:---:|
| **Tools** | `list_videos` — list indexed videos with filters | High |
| | `get_video_info` — metadata + summary for one video | High |
| | `search_transcripts` — semantic search (already built into chain) | Low |
| **Agent** | `create_tool_calling_agent` — LLM decides which tool to use | High |
| | `AgentExecutor` — tool → think → tool → respond loop | High |
| | `ChatPromptTemplate` with `agent_scratchpad` | High |
| **Memory** | Migrate to `RunnableWithMessageHistory` + `InMemoryChatMessageHistory` | Medium |
| | `BoundedChatMessageHistory` (sliding window with trim) | Medium |
| **Ingestion** | `VideoData` dataclass | Low |
| | `VectorStore.add()` / `build_index()` | Low |
| | `_extract_speakers_from_description()` patterns | Low |

---

## What was deliberately excluded

| Item | Reason |
|------|--------|
| `EmbeddingProvider` (manual class) | Replaced by `GoogleGenerativeAIEmbeddings` |
| `VectorStore` (manual class) | Replaced by `langchain_chroma.Chroma` |
| `_memory` (manual list of dicts) | Replaced by `ConversationBufferWindowMemory` |
| `ask()` wrapper | Replaced by `_chain.invoke()` |
| `genai.Client.generate_content()` | Replaced by LangChain chain |
| `import chromadb` / `from google import genai` | Replaced by LangChain wrappers |
| `yt_dlp`, `faster-whisper`, `youtube-transcript-api` | Read-only mode (ChromaDB pre-built by project) |
| Comments / docstrings | Removed per user preference |

---

## Evolution of cero-01

| Version | Lines | Key change |
|---------|:-----:|------------|
| v1 — Shebang | 1 | Bare executable |
| v2 — RAG core | 144 | Manual EmbeddingProvider + VectorStore + search() |
| v3 — LLM response | 181 | ask() with Gemini generate_content |
| v4 — Sliding memory | 185 | _memory list + MAX_TURNS + REPL |
| v5 — Similarity | 186 | --verbose shows sim scores |
| v6 — LangChain | 114 | ConversationalRetrievalChain replaces manual code |
| v7 — Source docs | 114 | return_source_documents + --verbose |

---

## Comparison with project scripts

| | cero-01 | rag_test | agent_cli |
|---|---|---|---|
| Lines | **114** | 168 | 82 |
| ChromaDB search | ✅ | ✅ | ✅ |
| LLM answers | ✅ | ❌ | ✅ |
| Memory | ✅ | ❌ | ✅ |
| Tools (agent) | ❌ | ❌ | ✅ |
| Self-contained | ✅ | ❌ | ❌ |
| --verbose | ✅ | ❌ | ❌ |
| Source docs | ✅ | ✅ | ❌ |
| Rebuild index | ❌ | ❌ | ❌ |
