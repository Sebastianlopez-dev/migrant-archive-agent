# Multimodal AI Chatbot for YouTube Video QA

## Development Timeline

| Step | Week | What | Status |
|------|------|------|--------|
| 1 | 1 | `core/ingestion.py` + dual transcription strategies (caption + faster-whisper + Colab) | ✅ Done |
| 2 | 1 | `core/processor.py` + `core/embedding.py` + `core/vector_store.py` | 🔲 In progress |
| 3 | 2 | `agents/` — LangChain agent with tools and memory | 🔲 Pending |
| 4 | 2 | Testing suite — unit, integration, E2E | 🔲 Pending |
| 5 | 3 | LangSmith evaluation + documentation | 🔲 Pending |
| 6 | 3 | FastAPI wrapper — REST endpoints + CORS | 🔲 Pending |
| 7 | 4 | `frontend/` — UI with text input + voice button (Web Speech API) | 🔲 Pending |
| 8 | 4 | Presentation and final deploy | 🔲 Pending |

> **Checkpoint (end of Week 1):** Live vector DB Q&A demo — query ChromaDB directly with pre-verified questions to prove the RAG pipeline works before moving to agents and API layers.

---

## Architecture Decisions (30 May 2026)

### 2. Fixed Channel
- A **specific YouTube channel** is processed in batch before deployment.
- Videos are transcribed, chunked, embedded, and stored in ChromaDB **once**.
- At runtime, the user simply asks a question → instant response (no processing wait).
- Advantage: faster for the user, cleaner demo, coherent knowledge base.
- The channel is defined in `config.py`.

### 3. Frontend Separate from Backend
- **Backend**: FastAPI exposing REST endpoints (`POST /api/ask`, etc.). Positioned as a wrapper layer (Step 6), not core infrastructure. The architecture emphasizes core-first development.
- **Frontend**: HTML/CSS/JS (starts simple, can migrate to React later without touching the backend).
- Decision motivated by UI/UX control and the ability to develop in parallel.
- The frontend only does `fetch()` to the backend; it knows nothing about RAG logic or ChromaDB.

### 4. Dual Transcription Strategy (updated 12 Jun 2026)
- **Strategy A**: `youtube-transcript-api` → free, instant, medium quality (no punctuation).
- **Strategy B**: `faster-whisper` local CPU → free, high quality, correct punctuation, ~2 min for a 4-min video.
- **Strategy B GPU**: `ingestion_colab.py` for videos >5 min (same logic, defaults `large-v3 --device cuda`).
- Both strategies produce the same `VideoData` contract → the rest of the pipeline doesn't know which one was used.
- **Decision**: faster-whisper as default, captions as fallback. See `notes/session-1-ingestion.md`.

### 5. User Voice Input with Web Speech API
- The user can ask questions **by voice** from the frontend.
- Uses the browser's **Web Speech API** (free, no external API).
- Works in Brave, Chrome, Edge, Opera, Arc (all Chromium-based).
- Transcription happens **in the browser** → the backend receives text, just as if the user typed it.
- **Zero backend changes.** No Whisper or additional endpoint needed.
- Reference code for `frontend/app.js`:
  ```javascript
  const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
  const recognition = new SpeechRecognition();
  recognition.lang = "es-ES";
  recognition.continuous = false;
  recognition.onresult = (event) => {
      const question = event.results[0][0].transcript;
      sendToAPI(question);
  };
  recognition.start();  // on microphone button click
  ```
- If the browser doesn't support Web Speech API, text input still works as fallback.

### 6. Technology Stack (updated 12 Jun 2026)

| Layer | Tool | Note |
|---|---|---|
| Transcription | `youtube-transcript-api` + `faster-whisper` | Dual strategy: Whisper default, captions fallback |
| Embeddings | **Gemini `embedding-001`** (default) | #1 MTEB Multilingual, free tier, $0.15/M tokens |
| Embeddings (local) | **BGE-M3** (alternative) | Open-source, CPU, 100+ languages, $0 |
| Embeddings (optional) | OpenAI `text-embedding-3-small` | Only if OpenAI compatibility is needed |
| Vector DB | ChromaDB (local, no external server) | |
| LLM | OpenAI `gpt-4o-mini` ⚠️ pending review | Migrate to Gemini 2.5 Flash? (Google credits available) |
| Orchestration | LangChain (agents, tools, RAG chains) | |
| Backend API | FastAPI | |
| Frontend | HTML + CSS + vanilla JS | |
| Voice input | Web Speech API (browser, free) | |
| Evaluation | LangSmith | |

### 7. Embedding Strategy with Dependency Inversion (12 Jun 2026)
- **Pattern**: Strategy + Dependency Inversion (same approach as ingestion).
- **Contract**: `core/embedding.py` defines `EmbeddingProvider` (abstract base class).
- **Implementations**:
  - `core/embedding_gemini.py` → Gemini API (cloud, best multilingual quality, generous free tier).
  - `core/embedding_bge_m3.py` → BGE-M3 local (CPU, 568M params, zero cost, sensitive data).
  - `core/embedding_openai.py` → OpenAI API (optional, compatibility with OpenAI ecosystem).
- **`processor.py`** receives an `EmbeddingProvider` via injection — it doesn't know or care which one.
- **`vector_store.py`** only persists vectors — it doesn't know who generated them.
- **Why Gemini and not OpenAI?**:
  - Gemini embedding-001 leads MTEB Multilingual (71.5 vs 39.2 for OpenAI small in Spanish).
  - The channel content is 100% Spanish → multilingual quality is critical.
  - Gemini free tier eliminates cost for the project volume (~$0.10 for the entire channel).
  - OpenAI requires a card and credits; the project already has a Google account with balance.
- **Why BGE-M3 local too?**:
  - Demonstrates understanding of cloud vs local tradeoffs in interviews.
  - Zero dependency on external APIs for embedding generation.
  - Same `EmbeddingProvider` interface → switching from Gemini to BGE-M3 is one config line.
- See full research: `notes/session-2-embeddings-research.md`.

### 8. Chunking Strategy (12 Jun 2026)
- **Chunk size**: 1000 tokens (~750 words, ~4-5 min of Spanish speech).
- **Overlap**: 200 tokens (20%) between consecutive chunks.
- **Token counter**: Simple estimator (4 characters ≈ 1 token). No external dependency.
- **Why 1000/200 and not 512/50?**
  - The content is conversational Spanish (interviews, debates at FILMIG). Spanish has longer sentences than English.
  - 1000 tokens captures a complete answer (~4-5 min of conversation) without breaking ideas.
  - 200 tokens of overlap (20%) ensures that if an idea crosses a chunk boundary, it appears in both.
  - Scales from 2 min to 2 hours of video without changes: a 1-hour video generates ~12 chunks (vs ~25 with 512/50).
  - Fewer chunks = fewer embedding API calls, without losing search precision.
- **Why a simple estimator and not tiktoken?**
  - `tiktoken` counts exact tokens (official OpenAI library). The estimator uses the rule `characters / 4`.
  - The difference between 980 and 1020 real tokens is irrelevant for chunk quality.
  - tiktoken adds an unnecessary dependency — only justified if you need to count API costs to the penny.
  - For chunking, the estimator is more than enough. Zero dependencies, same practical result.
- See full explanation: `notes/session-2-chunking-and-testing.md`.

### 9. Testing Strategy (12 Jun 2026)
- **Three test layers**, each catching different bugs:
  1. **Unit tests** (mock): `FakeEmbeddingProvider` → tests chunking and orchestration logic without external APIs. < 1 second.
  2. **Integration tests** (real): BGE-M3 local + temporary ChromaDB → tests that the pieces fit with REAL components. ~10 seconds, no internet.
  3. **E2E tests** (pipeline): Gemini API + real ChromaDB → tests the full pipeline with one video. ~30 seconds, requires API key.
- **Test structure**:
  ```
  tests/
  ├── test_processor.py         # Unit: chunking + FakeEmbeddingProvider
  ├── test_vector_store.py      # Integration: BGE-M3 + real ChromaDB
  ├── test_embedding.py         # Unit: EmbeddingProvider contracts
  └── test_pipeline_e2e.py      # E2E: full pipeline with Gemini
  ```
- See full explanation: `notes/session-2-chunking-and-testing.md`.

---

## Project Structure (updated 12 Jun 2026)

```
migrant-archive/
├── README.md
├── requirements.txt
├── .env.example
│
├── backend/
│   ├── config.py              # API keys, model, channel, paths
│   ├── main.py                # FastAPI entry point + CORS
│   ├── api/
│   │   ├── __init__.py
│   │   └── routes.py          # POST /api/ask, GET /api/health
│   ├── core/
│   │   ├── __init__.py
│   │   ├── ingestion.py        # VideoData dataclass + shared helpers
│   │   ├── ingestion_caption.py    # Strategy A: YouTube auto-captions
│   │   ├── ingestion_audio.py      # Strategy B: faster-whisper local CPU
│   │   ├── ingestion_colab.py      # Strategy B GPU: Colab wrapper
│   │   ├── embedding.py            # EmbeddingProvider (abstract contract)
│   │   ├── embedding_gemini.py     # Gemini API implementation (default)
│   │   ├── embedding_bge_m3.py     # BGE-M3 local implementation
│   │   ├── embedding_openai.py     # OpenAI implementation (optional)
│   │   ├── processor.py            # Chunking + call to EmbeddingProvider
│   │   ├── vector_store.py         # ChromaDB (save, search, delete)
│   │   ├── rag.py                  # Pipeline: question → retrieve → LLM → answer
│   │   └── prompts.py              # RAG prompt templates
│   ├── agents/
│   │   ├── __init__.py
│   │   ├── tools.py            # Tools for the agent
│   │   └── agent.py            # Agent configuration + memory
│   └── scripts/
│       └── ingest_channel.py   # Batch: processes all videos from the channel
│
├── frontend/
│   ├── index.html
│   ├── style.css
│   └── app.js                  # fetch() → POST /api/ask + Web Speech API (voice)
│
└── tests/
    ├── test_embedding.py       # Unit: EmbeddingProvider contracts
    ├── test_processor.py       # Unit: chunking + FakeEmbeddingProvider
    ├── test_vector_store.py    # Integration: BGE-M3 + real ChromaDB
    └── test_pipeline_e2e.py    # E2E: full pipeline with Gemini
```

---

## Why Each Separation

| File | Responsibility | Changes when... |
|---|---|---|
| `config.py` | Centralized settings | You change API key, model, channel |
| `main.py` | FastAPI server + CORS | You configure middleware, docs |
| `api/routes.py` | REST endpoints | You change the public interface |
| `core/ingestion.py` | VideoData contract + shared helpers | Data schema changes |
| `core/ingestion_caption.py` | Strategy A: YouTube captions | YouTube API changes |
| `core/ingestion_audio.py` | Strategy B: faster-whisper CPU | Whisper model changes |
| `core/embedding.py` | EmbeddingProvider contract (abstract) | Embedding interface changes |
| `core/embedding_gemini.py` | Gemini API implementation | Gemini API changes |
| `core/embedding_bge_m3.py` | BGE-M3 local implementation | Local model changes |
| `core/processor.py` | Chunking (1000tk/200ov) + embedding orchestration | You adjust chunk size or strategy |
| `core/vector_store.py` | ChromaDB CRUD | You migrate to Pinecone |
| `tests/test_embedding.py` | EmbeddingProvider contracts | Interface changes |
| `tests/test_processor.py` | Chunking + FakeEmbeddingProvider | Chunking logic changes |
| `tests/test_vector_store.py` | Integration BGE-M3 + ChromaDB | Provider implementation changes |
| `tests/test_pipeline_e2e.py` | E2E full pipeline | Before deploying |
| `core/rag.py` | Q&A pipeline | You improve answer quality |
| `core/prompts.py` | Prompt templates | You iterate on prompt engineering |
| `agents/tools.py` | Agent tools | You add or remove tools |
| `agents/agent.py` | Agent + memory | You change agent strategy |
| `scripts/ingest_channel.py` | Batch processing | You change channel or ingestion logic |
| `frontend/` | UI/UX + voice input (Web Speech API) | You improve design or change voice engine without touching backend |

---

## Full Flow

```
# ── Setup (once) ──
python -m backend.scripts.ingest_channel
  → YouTube Transcript API downloads 50+ videos from the channel
  → processor.py: chunk + embed
  → vector_store.py: save to ChromaDB

# ── Runtime ──
User speaks (microphone) or types in the frontend
  → Web Speech API transcribes voice → text  (or uses text input directly)
  → frontend/app.js → fetch POST /api/ask { question: "..." }
  → backend/api/routes.py → core/rag.py
  → rag.py: embed question → ChromaDB search → build prompt → LLM
  → API returns { answer: "...", sources: [...] }
  → frontend shows answer + sources
```
