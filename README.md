# Migrant Archive — Narratives That Resist

Multimodal RAG chatbot that answers questions about YouTube video content.
Built on the FILMIG / Plataforma Cero channel (Spanish).

---

## Progress Dashboard

| Week | Focus | Done | Pending |
|------|-------|------|---------|
| 1 | Ingestion + Processing | S01–S03 complete | — |
| 2 | Agents + Testing | S04–S06 complete | — |
| 3 | Observability + API | S07 complete | — |
| 4 | Frontend + Deploy | Presentation | Deploy |

---

## Pipeline Architecture

```
FILMIG / Plataforma Cero (YouTube)
         │
         ▼
   ┌─ S01 ──────────────────────┐
   │  Video Ingestion           │
   │  3 strategies (Colab GPU /  │
   │  faster-whisper / captions) │
   └──────────────┬──────────────┘
                  │
                  ▼
   ┌─ S02 ──────────────────────┐
    │  Chunking + Embedding      │
    │  1000tk/200ov · enriched   │
    │  gemini-embedding-2 (3072d) │
   └──────────────┬──────────────┘
                  │
                  ▼
   ┌─ S03 ──────────────────────┐
   │  ChromaDB Vector Store     │
   │  Persistent · semantic     │
   │  search · metadata filters │
   └──────────────┬──────────────┘
                  │
        ┌─────────┴─────────┐
        ▼                   ▼
    ┌─ S04 ──────────┐  ┌─ S05 ──────────┐
    │  Sample        │  │  RAG Test +    │
    │  Extract       │  │  Rebuild       │
    │  5K chars      │  │  Query ChromaDB│
    └──────┬─────────┘  └──────┬─────────┘
          │                  │
          └────────┬─────────┘
                   ▼
          ┌─ S06 ──────────────────────────┐
          │  LangChain Agent (Cero)        │
          │  3 tools · tool-calling        │
          │  message history · sessions    │
          └────────────────┬───────────────┘
                           ▼
                   ┌─ S07 ───────────────────────┐
                   │  LangSmith, API + Chat      │
                   │  Widget · FastAPI           │
                   │  embeddable widget          │
                  └────────────┬────────────────┘
                               ▼
                        ┌─ S08 ──────────────┐
                        │  Frontend + Deploy │
                        │  Presentation      │
                        │  Widget redesigned │
                        │  Voice (Groq)      │
                        │  i18n (6 languages)│
                        └────────────────────┘
```

<details>
<summary>S01 — Video Ingestion: 3 strategies · 4 files · 3 test files · 3 decisions</summary>

**Decisions:**
- 3-strategy approach (Colab GPU / faster-whisper local / captions)
- Strategy Pattern for ingestion
- VideoData JSON as shared contract across all strategies

**Files:** [`ingestion.py`](backend/core/ingestion.py) · [`ingestion_audio.py`](backend/core/ingestion_audio.py) · [`ingestion_caption.py`](backend/core/ingestion_caption.py) · [`ingestion_colab.py`](backend/core/ingestion_colab.py)

**Tests:** `test_ingestion.py` · `test_faster_whisper_audio.py` · `test_faster_whisper_colab.py`

</details>

<details>
<summary>S02 — Chunking + Embedding: 3 decisions · 3 files · 3 test files</summary>

**Decisions:**
- Chunk size 1000 / overlap 200 (optimized for Spanish conversational content)
- Enriched text: title + description + [MM:SS] timestamps per segment
- Dependency Inversion: EmbeddingProvider abstract base class

**Files:** [`embedding.py`](backend/core/embedding.py) · [`processor.py`](backend/core/processor.py) · [`embedding_gemini.py`](backend/core/embedding_gemini.py)

**Tests:** `test_embedding.py` · `test_embedding_gemini.py` · `test_processor.py`

</details>

<details>
<summary>S03 — ChromaDB Vector Store: 1 file · 2 test files</summary>

**Files:** [`vector_store.py`](backend/core/vector_store.py) — persistent storage, semantic search, metadata filters

**Tests:** `test_vector_store.py` · `test_pipeline_e2e.py`

</details>

<details>
<summary>S04–S05 — Sample Extraction + RAG Test: 5 files · 1 test file</summary>

**Files:**
[`quick_search.py`](backend/scripts/quick_search.py) — fast keyword search (no API)
[`rag_test.py`](backend/scripts/rag_test.py) — interactive semantic search
[`backend/scripts/cero-01.py`](backend/scripts/cero-01.py) — conversational RAG with LangChain (ConversationalRetrievalChain + memory + LLM answers)
[`extract_sample.py`](backend/scripts/extract_sample.py) — first-5K extraction from ChromaDB + JSON
[`rebuild_index.py`](backend/scripts/rebuild_index.py) — rebuild ChromaDB index from whisper JSONs

**Tests:** `test_extract_sample.py`

**Memory progression:** `quick_search.py` (no API, no memory) → `rag_test.py` (semantic, no memory) → `backend/scripts/cero-01.py` (buffer window, LLM answers) → `agent_cli.py` (buffer, LLM + tools). Same sliding-window idea, different consumer and capabilities.

</details>

<details>
<summary>S06 — LangChain Agent (Cero): 4 decisions · 3 files · 2 test files (44 tests)</summary>

**Decisions:**
- Native tool calling over ReAct text parsing (eliminated ~30% failure rate on Spanish queries)
- RunnableWithMessageHistory over deprecated ConversationBufferMemory
- Bounded sliding window: `BoundedChatMessageHistory` drops oldest messages at `MAX_HISTORY_MESSAGES=10` (5 Q&A turns)
- faster-whisper over WhisperX (NumPy/CUDA incompatibility on Colab)

**Files:** [`agent.py`](backend/agents/agent.py) · [`tools.py`](backend/agents/tools.py) · [`agent_cli.py`](backend/scripts/agent_cli.py)

**Tests:** `test_agent.py` (34 tests) · `test_speaker_extraction.py` (10 tests)

</details>

<details>
<summary>S07 — LangSmith, API + Chat Widget: 2 decisions · 13 files · 3 test files (57 frontend tests)</summary>

**Decisions:**
- LangSmith zero-code tracing (env-var auto-detection, no application code required)
- YouTube links generated in backend (deterministic, no HTML injection)

**Files:** [`main.py`](backend/api/main.py) · [`models.py`](backend/api/models.py) · [`dependencies.py`](backend/api/dependencies.py) · [`chat.py`](backend/api/routes/chat.py) · [`transcribe.py`](backend/api/routes/transcribe.py) · [`chat-widget.ts`](frontend/src/chat-widget.ts) · [`api-client.ts`](frontend/src/api-client.ts) · [`fab.ts`](frontend/src/fab.ts) · [`panel.ts`](frontend/src/panel.ts) · [`zero-state.ts`](frontend/src/zero-state.ts) · [`input-bar.ts`](frontend/src/input-bar.ts) · [`message-list.ts`](frontend/src/message-list.ts) · [`main.ts`](frontend/src/main.ts)

**Tests:** `test_api.py` · `test_frontend.py` · `test_langsmith.py`

</details>

<details>
<summary>S08 — Frontend + Deploy: 1 decision · 7 completed · 1 pending</summary>

**Decisions:**
- Deploy platform research: Railway, Fly.io, Cloudflare Pages + Workers

**Completed:**
- [`migrant-archive-slides.html`](presentation/migrant-archive-slides.html) — 18-slide HTML deck
- Chat widget redesigned: FAB toggle, side panel (30%), zero-state with 3 clickable suggestions, bottom-anchored input bar with voice button, dark theme, responsive, keyboard navigation, ARIA accessibility
- Voice input is COMPLETE — Groq Whisper API (`whisper-large-v3-turbo`), 30s max recording with countdown, works in all browsers
- Multilingual support: 6 languages (EN/ES/CA/FR/PT/DE) with language selector in panel header
- I18N across all modules: zero-state, input-bar, message-list, FAB, panel
- Custom circular UI: all buttons (send, mic, language, refresh, close) are circular
- New Cero avatar icon (`cero-agent-icon.png`)

**Pending:** deploy to production

</details>

---

## Quick Start Walkthrough

From raw YouTube videos to the chat widget. Each step links to the detailed section.

<details>
<summary>Step 1 — Choose Your Environment (required first)</summary>

### Step 1 — Choose Your Environment

This project uses UV as its package manager.

| | UV (lightweight) |
|---|---|
| **Best for** | Gemini API embeddings |
| **What you get** | Transcription + Gemini cloud embeddings |
| **Install size** | ~500 MB |
| **GPU needed?** | No |
| **Internet required?** | Yes (for Gemini API) |
| **API keys?** | Gemini (free tier) |

> **Embedding provider note:** Only Gemini embeddings are supported. BGE-M3 was removed.

#### UV + Gemini (recommended)

```bash
# 1. Install UV
curl -LsSf https://astral.sh/uv/install.sh | sh

# 2. Create env and install
uv venv --python 3.12 && source .venv/bin/activate
uv pip install -r requirements.txt

# 3. Add API keys (free: aistudio.google.com/apikey, console.groq.com, smith.langchain.com)
cp .env.example .env   # set GEMINI_API_KEY, GROQ_API_KEY, and optionally LANGSMITH_API_KEY / LANGSMITH_PROJECT

# 4. System dependency
brew install ffmpeg     # macOS
```

</details>

<details>
<summary>Step 2 — Ingest videos + transcription</summary>

### Step 2 — Ingest videos + transcription

Download and transcribe YouTube videos. Colab GPU is the best option (fast, free). Local CPU is a fallback for short videos.

**Colab GPU (recommended):** use [`notebooks/transcribe_video_colab.ipynb`](notebooks/transcribe_video_colab.ipynb).

**What to upload to Colab:** `ingestion.py`, `ingestion_colab.py`, `ingestion_audio.py`, cookies file, video links list.

Output: `data/raw/whisper/{video_id}.json` (one JSON per video with transcript + metadata).
```bash
# Local CPU (fallback):
python backend/core/ingestion_audio.py --url "VIDEO_URL" --lang es
```

Full details: [S01 — Video Ingestion](#s01--video-ingestion).

</details>

<details>
<summary>Step 3 — Build the vector index (embeddings)</summary>

### Step 3 — Build the vector index (embeddings)

Chunk transcript text, generate Gemini embeddings, and store in ChromaDB. Run once after adding new videos.

```bash
python backend/scripts/rebuild_index.py
```

Full details: [S02 — Chunking and Embedding](#s02--chunking-and-embedding) and [Embeddings Workflow](#embeddings-workflow).

</details>

<details>
<summary>Step 4 — Query (simple RAG, no memory)</summary>

### Step 4 — Query (RAG, from no memory to conversational)

Three levels of querying ChromaDB, from keyword to semantic to conversational AI.

```bash
# Level 1 — Fast keyword search (no API, no embeddings):
python backend/scripts/quick_search.py "FilmiG"

# Level 2 — Semantic search (API embeddings, no memory):
python backend/scripts/rag_test.py

# Level 3 — Conversational RAG (API embeddings + LLM answers + memory):
uv run python backend/scripts/cero-01.py "¿cómo describen el dolor de migrar?"
uv run python backend/scripts/cero-01.py --verbose "¿qué sentimientos expresan las mujeres?"
uv run python backend/scripts/cero-01.py           # REPL mode
```

| Script | Memory | LLM Answers | API calls | Best for |
|--------|--------|:---:|-----------|----------|
| `quick_search.py` | None | No | 0 | Fast checks, no cost |
| `rag_test.py` | None | No | Embedding only | Exploring the DB |
| **`backend/scripts/cero-01.py`** | **Buffer Window (K=5)** | **Spanish** | **Embedding + Chat** | **Demo, conversational Q&A** |

`backend/scripts/cero-01.py` is a self-contained 123-line conversational RAG built entirely with LangChain (`ConversationalRetrievalChain`, `Chroma`, `GoogleGenerativeAIEmbeddings`, `ChatGoogleGenerativeAI`). It answers questions in Spanish using transcript chunks as context, remembers the last 5 conversation turns, and shows source documents with `--verbose`. Zero imports from `backend/core/`.

Try these questions once inside `rag_test.py` or `backend/scripts/cero-01.py`:

| Question | What it tests |
|----------|---------------|
| `De que trata el video?` | General topic retrieval |
| `Que dice Lucia Mbomio sobre racismo?` | Speaker + topic scoping |
| `Cuales son los videos de 2025?` | Metadata-aware search |

```bash
# Sequential extraction (reads chunks in order):
python backend/scripts/extract_sample.py --source chroma
```

Full details: [Scenario 3 — Reading / Querying Embeddings](#scenario-3--reading--querying-embeddings) and [S05 — RAG Test + Memory](#s05--rag-test--memory).

</details>

<details>
<summary>Step 5 — Query with memory (agent CLI)</summary>

### Step 5 — Query with memory (agent CLI)

Same ChromaDB, but with conversation context. The agent remembers previous turns, disambiguates vague queries by listing videos, and can scope searches to a single video.

```bash
python backend/scripts/agent_cli.py
```

Type `history` to see the last 5 Q&A pairs in the buffer.

Try these questions to exercise each tool:

| Question | Tool tested |
|----------|-------------|
| `Que videos tienes?` | `list_videos` — lists all indexed videos |
| `Dame informacion del video Escrituras Otras` | `get_video_info` — single video detail |
| `Que dice Safia El Aaddam sobre racismo?` | `search_transcripts` — scoped semantic search |
| `Y que libros ha escrito?` | Memory — follow-up on Safia El Aaddam from previous answer |
| `Resume los argumentos principales del video sobre produccion cultural migrante` | `search_transcripts` — synthesis from chunks |
| `Que videos son de 2024?` | `list_videos` — year filter from ChromaDB |
| `Busca testimonios de Plataforma Cero sobre migracion` | `search_transcripts` — channel + semantic filter |
| `En que se diferencia el video de 2024 del de 2025 sobre FILMIG?` | `list_videos` + `search_transcripts` — cross-video comparison |
| `Cuantos de esos videos tienen ponentes?` | Memory — follow-up after `list_videos` |

Full details: [S06 — Conversational Agent with Memory](#s06--conversational-agent-with-memory).

</details>

<details>
<summary>Step 6 — Trace with LangSmith (observability)</summary>

### Step 6 — Trace with LangSmith (observability)

See every agent run live: LLM calls, tool executions, latency, token usage, and cost. Zero application code required — LangChain auto-detects the env vars.

```bash
# Add to your .env file:
LANGSMITH_TRACING=true
LANGSMITH_API_KEY=lsv2_pt...
LANGSMITH_PROJECT=migrant-archive
LANGSMITH_ENDPOINT=https://api.smith.langchain.com
```

Run the agent or API normally. Traces appear at [smith.langchain.com](https://smith.langchain.com).

Full details: [LangSmith Tracing](#langsmith-tracing).

</details>

<details>
<summary>Step 7 — Query through the web widget</summary>

### Step 7 — Query through the web widget

Start the API, then the frontend.

```bash
# Terminal 1 — API:
uv run uvicorn backend.api.main:app --reload --port 8000

# Terminal 2 — Frontend:
cd frontend && pnpm install && pnpm dev
```

Open `http://localhost:5173`. Cero avatar floating bottom-right — click to open.

Full details: [S07 — LangSmith, API + Chat Widget](#s07--langsmith-api--chat-widget).

</details>

---

## Architectural Decisions and Concepts

<details>
<summary>Project Structure</summary>

### Project Structure

```
migrant-archive/
├── .env.example                ← Template for API keys + LangSmith config
├── requirements.txt            ← Python dependencies (uv/pip path)
│
├── backend/
│   ├── api/
│   │   ├── main.py             ← FastAPI app factory
│   │   ├── models.py           ← Pydantic schemas (AskRequest with session_id)
│   │   ├── dependencies.py     ← Agent dependency injection (RunnableWithMessageHistory)
│   │   └── routes/
│   │       ├── chat.py         ← POST /api/ask + DELETE /api/session/{id}
│   │       └── transcribe.py   ← POST /api/transcribe (Groq Whisper)
│   ├── agents/
│   │   ├── __init__.py
│   │   ├── agent.py            ← Tool-calling agent + per-session message history
│   │   └── tools.py            ← 3 tools + speaker extraction
│   ├── core/
│   │   ├── ingestion.py        ← VideoData dataclass + shared helpers
│   │   ├── ingestion_caption.py    ← Strategy A: YouTube auto-captions
│   │   ├── ingestion_audio.py      ← Strategy B: faster-whisper local CPU
│   │   ├── ingestion_colab.py      ← Strategy B GPU: Colab wrapper
│   │   ├── embedding.py            ← EmbeddingProvider (abstract contract)
│   │   ├── embedding_gemini.py     ← Gemini API implementation
│   │   ├── processor.py            ← Chunking (1000tk/200ov) + embedding
│   │   └── vector_store.py         ← ChromaDB persistence
│   ├── scripts/
│   │   ├── agent_cli.py        ← Interactive agent CLI
│   │   ├── cero-01.py          ← Conversational RAG with LangChain (self-contained, 123 lines)
│   │   ├── rag_test.py         ← Interactive RAG pipeline test script
│   │   ├── rebuild_index.py    ← Rebuild ChromaDB index from whisper JSON files
│   │   ├── quick_search.py     ← Keyword search (no API, no embeddings)
│   │   └── extract_sample.py   ← First-5K extraction from ChromaDB + JSON
│
├── frontend/
│   ├── index.html              ← Widget mount point
│   ├── package.json            ← pnpm dependencies
│   ├── vite.config.ts          ← Vite + API proxy config
│   ├── public/
│   │   ├── cero-agent-icon.png     ← Cero avatar (FAB, panel header, zero-state)
│   │   └── cerito-avatar.svg       ← Original vector avatar (legacy)
│   └── src/
│       ├── main.ts             ← Widget bootstrap
│       ├── api-client.ts       ← Typed fetch wrapper for POST /api/ask
│       ├── fab.ts              ← Floating action button (FAB)
│       ├── panel.ts            ← Side panel shell (30% width)
│       ├── zero-state.ts       ← Greeting + 3 suggestion cards
│       ├── input-bar.ts        ← Bottom input toolbar with send/mic/model
│       ├── message-list.ts     ← Conversation rendering + source citations
│       ├── chat-widget.ts      ← Orchestrator wiring all modules together
│       └── styles.css          ← Dark theme CSS custom properties
│
├── tests/
│   ├── conftest.py             ← Shared pytest fixtures + LangSmith guard
│   ├── test_agent.py           ← Agent, tool, memory, CLI tests
│   ├── test_langsmith.py       ← LangSmith tracing + fixture tests
│   ├── test_api.py             ← API models, routes, CORS, errors
│   ├── test_frontend.py        ← Frontend build + widget structure
│   ├── test_embedding.py       ← Contract tests (FakeEmbeddingProvider)
│   ├── test_embedding_gemini.py ← Gemini provider tests
│   ├── test_processor.py       ← Chunking + orchestration tests
│   ├── test_vector_store.py    ← ChromaDB CRUD + relevance tests
│   ├── test_pipeline_e2e.py    ← Full pipeline with real video
│   ├── test_extract_sample.py  ← First-5K extraction + truncation tests
│   ├── test_ingestion.py       ← VideoData + timestamp helper tests
│   ├── test_faster_whisper_audio.py ← faster-whisper strategy tests
│   ├── test_faster_whisper_colab.py ← Colab notebook validation tests
│   ├── test_rebuild_index.py  ← ChromaDB index rebuild tests
│   └── test_speaker_extraction.py  ← Speaker extraction from descriptions
│
├── data/
│   ├── audio/                  ← Downloaded audio cache (gitignored)
│   ├── chroma/                 ← ChromaDB persistent storage (gitignored)
│   └── raw/
│       └── whisper/            ← Whisper strategy JSON output
│
├── models/
│   └── whisper/                ← faster-whisper model files (gitignored)
│
├── presentation/               ← HTML slides for project demo
│
└── notebooks/                  ← Colab notebooks for cloud GPU processing
│   └── transcribe_video_colab.ipynb  ← Transcribe long videos with T4 GPU
```

> The `openspec/` directory contains the full SDD technical documentation (specs, designs, proposals, archives) for anyone who wants to understand the technical decisions behind each feature.

</details>

---

<details>
<summary>S01 — Video Ingestion</summary>

### S01 — Video Ingestion

Once your environment is ready, the first step is extracting text from YouTube videos. You have three strategies — pick based on your needs.

**Quick start (Strategy A, recommended):**
1. Upload files to Colab → `ingestion.py`, `ingestion_colab.py`, cookies, video links
2. Transcribe → `python backend/core/ingestion_colab.py --url "VIDEO_URL" --lang es`
3. Output → `data/raw/whisper/{video_id}.json`
4. Repeat for each video.

#### Strategy comparison

| | A: Colab GPU | B: Whisper local | C: Captions |
|---|---|---|---|
| **Quality** | 5/5 (large-v3) | 4/5 (full sentences) | 2/5 (no punctuation) |
| **Speed** | ~15 sec (4-min video) | ~2 min (4-min video) | Instant |
| **Cost** | $0 (Colab free tier) | $0 | $0 |
| **Best for** | All videos, batches | ≤ 5 min videos | Quick tests, fallback |
| **Hardware** | Google Colab GPU | Intel i9 / 32GB RAM | None |

---

#### Strategy A: Google Colab GPU (recommended)

> **Source:** [`backend/core/ingestion_colab.py`](backend/core/ingestion_colab.py)

Best quality, fastest speed, zero cost. Runs on Colab's free T4 GPU with the `large-v3` model. ~10x faster than local CPU.

```bash
# Upload ingestion.py, ingestion_colab.py, cookies, and video links to Colab, then run:
python backend/core/ingestion_colab.py --url "VIDEO_URL" --lang es
```

Defaults: `large-v3` model, `--device cuda`. Saves to Google Drive (`migrant-archive/output/`).

---

#### Strategy B: faster-whisper (Local CPU)

> **Source:** [`backend/core/ingestion_audio.py`](backend/core/ingestion_audio.py) · shared contract: [`backend/core/ingestion.py`](backend/core/ingestion.py)
>
> **Why faster-whisper over WhisperX?** WhisperX adds speaker diarisation and word-level alignment but is incompatible with Google Colab as of mid-2026 (NumPy/CUDA conflicts). faster-whisper uses the same Whisper large-v3 model with zero dependency issues. FILMIG content is mostly single-speaker. faster-whisper was chosen for its zero dependency issues and Colab compatibility. Full decision: faster-whisper-migration.md.

Good quality at zero cost. Runs entirely on your machine — no API, no uploads. Good fallback for short videos when Colab is unavailable.

```bash
# macOS / Linux
source .venv/bin/activate
python backend/core/ingestion_audio.py --url "VIDEO_URL" --lang es

# Windows (PowerShell)
.venv\Scripts\activate
python backend/core/ingestion_audio.py --url "VIDEO_URL" --lang es
```

**Available flags:**

| Flag | Default | Options |
|------|---------|---------|
| `--url` | (required) | YouTube video URL |
| `--lang` | `es` | `es`, `en`, `ca`, or `""` for auto-detect |
| `--model` | `small` | `tiny`, `base`, `small`, `medium`, `large-v3` |
| `--device` | `auto` | `auto`, `cpu`, `cuda` |
| `--output-dir` | `data/raw/whisper` | Any directory |
| `--audio-dir` | `data/audio` | Any directory |

**Language support:**

| Code | Language | Use case |
|------|----------|----------|
| `es` | Spanish | Default — FILMIG content |
| `en` | English | English videos |
| `ca` | Catalan | Catalan/Spanish code-switching |
| `""` | Auto-detect | Unknown language |

Audio is cached at `data/audio/{video_id}.mp3` — re-running the same video skips the download.

Output: `data/raw/whisper/{video_id}.json`

---

#### Strategy C: YouTube Auto-Captions (fallback)

Instant, free, but captions lack punctuation and may have garbled segments. Use only for quick tests.

```bash
source .venv/bin/activate
python backend/core/ingestion_caption.py --url "VIDEO_URL" --lang es
```

Output: `data/raw/captions/{video_id}.json`

> **Warning:** Captions on Spanish/Catalan code-switching can be broken. Prefer Strategy A or B for production.

</details>


<details>
<summary>S02 — Chunking and Embedding</summary>

### S02 — Chunking and Embedding

Once you have transcriptions (S01), this stage converts text into searchable vector embeddings and stores them in ChromaDB.

**Quick start (Gemini, recommended):**
1. Make sure `.json` files exist in `data/raw/whisper/`
2. Build index → `python backend/scripts/rebuild_index.py`
3. Query → `python backend/scripts/rag_test.py`
4. If you add more videos later → see [Embeddings Workflow](#embeddings-workflow) below.

#### Chunking strategy

> **Source:** [`backend/core/processor.py`](backend/core/processor.py) — `chunk_size=1000, overlap=200`

Before embedding, text is split into overlapping chunks. These values were chosen specifically for Spanish conversational content (interviews, debates).

| Parameter | Value | Why |
|-----------|-------|-----|
| **Chunk size** | 1,000 tokens (~750 words) | Captures ~4-5 min of speech — one complete idea |
| **Overlap** | 200 tokens (20%) | Ensures no idea is cut at chunk boundaries |
| **Token counter** | `len(text) // 4` | Simple estimator — zero dependencies, accurate enough |
| **Enriched text** | title + description + `[MM:SS]` | Gives the embedding model context about the video and segment timestamps |
| **Legacy fallback** | plain `full_text` | JSONs without `transcript_segments` keep working without re-ingestion |
| **1-hour video** | ~12 chunks | vs ~25 with smaller chunks (less API cost, less noise) |

> **Why not smaller chunks?** Spanish sentences are longer than English. A 380-word chunk (512 tokens) cuts ideas in half. 750 words captures a full answer, an anecdote, or a complete argument. The 20% overlap bridges ideas that cross chunk boundaries. This scales from 2-minute clips to 2-hour documentaries without changes.

> **Enriched text:** each chunk is built from `VideoData.enriched_text()`, which prefixes the video title and description and adds `[MM:SS]` (or `[HH:MM:SS]` for videos ≥ 1 hour) to every transcript segment. Legacy JSONs that still have plain `full_text` but also contain `transcript_segments` are enriched automatically at chunk time, so no re-ingestion is required. Each chunk's `metadata["start_time"]` / `metadata["end_time"]` is estimated from the first and last timestamp marker inside that chunk.

---

#### Gemini API Embeddings (default)

> **Source:** [`backend/core/embedding_gemini.py`](backend/core/embedding_gemini.py)

Uses `gemini-embedding-2` — Google's #1 multilingual embedding model (MTEB 69.9). 8,192 token context window, multimodal-ready.

> **Batch limitation:** `gemini-embedding-2` does NOT support batching in the genai SDK. Each text is embedded individually via `embed_content`. For large-scale indexing, use the [Gemini Batch API](https://ai.google.dev/gemini-api/docs/batch) instead.

**Requires:** UV environment + `GEMINI_API_KEY` in `.env`.

```python
from backend.core.embedding_gemini import GeminiEmbeddingProvider
from backend.core.processor import Processor
from backend.core.vector_store import VectorStore
from backend.core.ingestion import VideoData

# Load a transcribed video
video = VideoData.load_json("data/raw/whisper/VIDEO_ID.json")

# Create provider (reads GEMINI_API_KEY from env)
provider = GeminiEmbeddingProvider()
processor = Processor(provider, chunk_size=1000, overlap=200)

# Chunk and embed
chunks, embeddings = processor.process(video)

# Store in ChromaDB
store = VectorStore(persist_dir="data/chroma")
store.add(
    ids=[f"{video.video_id}_chunk_{c.metadata['chunk_index']}" for c in chunks],
    documents=[c.text for c in chunks],
    metadatas=[c.metadata for c in chunks],
    embeddings=embeddings,
)

# Search
query_emb = provider.embed_query("¿De qué trata el video?")
results = store.search(query_emb, top_k=3)
for r in results:
    print(r["document"][:200])
```

---

#### Process all videos in batch

```python
from pathlib import Path

provider = GeminiEmbeddingProvider()
processor = Processor(provider)
store = VectorStore(persist_dir="data/chroma")

for json_file in Path("data/raw/whisper").glob("*.json"):
    video = VideoData.load_json(json_file)
    chunks, embeddings = processor.process(video)
    store.add(
        ids=[f"{video.video_id}_chunk_{c.metadata['chunk_index']}" for c in chunks],
        documents=[c.text for c in chunks],
        metadatas=[c.metadata for c in chunks],
        embeddings=embeddings,
    )
    print(f"[OK] {video.title} — {len(chunks)} chunks stored")
```

---

#### Reset the vector store

> **Source:** [`backend/core/vector_store.py`](backend/core/vector_store.py)

```bash
rm -rf data/chroma/
```

ChromaDB data is gitignored. Deleting the directory starts fresh.

---

#### Embeddings Workflow

> **Scripts:** [`backend/scripts/rag_test.py`](backend/scripts/rag_test.py) · [`backend/scripts/extract_sample.py`](backend/scripts/extract_sample.py) · core: [`backend/core/vector_store.py`](backend/core/vector_store.py)

Three scenarios: first-time creation, adding new videos, and reading stored data.

##### Scenario 1 — First-Time Creation (Initial Embeddings)

**When:** you've transcribed videos in S01 and ChromaDB is empty. This is the first time you're building the vector index.

**Simplest path — use the rebuild script:**

```bash
source .venv/bin/activate

# This chunks, embeds, and stores ALL whisper JSON files
python backend/scripts/rebuild_index.py
```

**What happens under the hood:**

1. `rebuild_index.py` finds every `.json` in `data/raw/whisper/`
2. For each video: `VideoData.load_json()` → `Processor.chunk()` → `Processor.embed_chunks()` → `VectorStore.add()`
3. ChromaDB is created at `data/chroma/` with collection `migrant_archive`

**Expected output:**

```
Initializing Gemini embedding provider ...
Rebuilding index from data/raw/whisper into data/chroma ...

Indexing: APgxfNssxGQ.json  ... 12 chunks
Indexing: XYZ123.json       ... 8 chunks

Indexed 20 chunks from 2 video(s) into ChromaDB.

Collection size: 20 chunks
```

**Alternative — programmatic (full control):**

If you need more control than the script offers (custom chunk size, captions instead of whisper):

```python
from pathlib import Path
from backend.core.embedding_gemini import GeminiEmbeddingProvider
from backend.core.processor import Processor
from backend.core.vector_store import VectorStore
from backend.core.ingestion import VideoData

provider = GeminiEmbeddingProvider()
processor = Processor(provider, chunk_size=1000, overlap=200)
store = VectorStore(persist_dir="data/chroma")

for json_file in Path("data/raw/whisper").glob("*.json"):
    video = VideoData.load_json(json_file)
    chunks, embeddings = processor.process(video)
    store.add(
        ids=[f"{video.video_id}_chunk_{c.metadata['chunk_index']}" for c in chunks],
        documents=[c.text for c in chunks],
        metadatas=[c.metadata for c in chunks],
        embeddings=embeddings,
    )
    print(f"[OK] {video.title} — {len(chunks)} chunks stored")

print(f"\nDone. {store.count} chunks in ChromaDB.")
```

---

##### Scenario 2 — Updating Embeddings (Adding New Videos)

You've already built the index. Now you transcribe a new video and need to add it to ChromaDB WITHOUT losing what's already there. You have three options, depending on how many videos you're adding.

##### Option A: Add a single new video (incremental)

**Best when:** you transcribed one new video and don't want to re-embed everything.

The key insight: ChromaDB IDs are `{video_id}_chunk_{index}`. A new video has a *different* `video_id`, so there's no ID conflict — you can safely call `add()` on the existing collection.

```python
from backend.core.embedding_gemini import GeminiEmbeddingProvider
from backend.core.processor import Processor
from backend.core.vector_store import VectorStore
from backend.core.ingestion import VideoData

provider = GeminiEmbeddingProvider()
processor = Processor(provider, chunk_size=1000, overlap=200)

# WARNING: Do NOT call delete_collection() — use the existing store as-is
store = VectorStore(persist_dir="data/chroma")
print(f"Before: {store.count} chunks in ChromaDB")

# Load the NEW video only
video = VideoData.load_json("data/raw/whisper/NEW_VIDEO_ID.json")
chunks, embeddings = processor.process(video)

store.add(
    ids=[f"{video.video_id}_chunk_{c.metadata['chunk_index']}" for c in chunks],
    documents=[c.text for c in chunks],
    metadatas=[c.metadata for c in chunks],
    embeddings=embeddings,
)
print(f"After:  {store.count} chunks in ChromaDB (+{len(chunks)} from '{video.title}')")
```

> **Warning:** If you accidentally run this on a video that's *already* in ChromaDB, the `add()` call will fail with `IDAlreadyExistsError`. ChromaDB does not silently deduplicate — it rejects duplicate IDs. To re-index a specific video you'd need to delete its chunks first (see Option C).

##### Option B: Rebuild everything (destructive, simplest)

**Best when:** you added multiple new videos, or changed the chunking strategy (size/overlap), or switched embedding providers.

```bash
# This deletes the old ChromaDB index and rebuilds from ALL whisper JSONs
python backend/scripts/rebuild_index.py
```

This is the same command as Scenario 1. `rebuild_index.py` calls `delete_collection()` internally, wiping everything before re-indexing all JSON files found in `data/raw/whisper/`.

> **Tip:** With Gemini API, re-embedding is fast and cheap (~$0 for the entire project). Unless you have 100+ videos, rebuilding is usually the pragmatic choice.

##### Option C: Start completely fresh

```bash
rm -rf data/chroma/
python backend/scripts/rebuild_index.py
```

Manually deleting the directory before rebuilding guarantees a clean slate — useful if you suspect ChromaDB corruption or changed the embedding model.

---

##### Scenario 3 — Reading / Querying Embeddings

Once your vectors are in ChromaDB, there are three ways to access them.

##### Method A: Interactive semantic search (demo / exploration)

```bash
python backend/scripts/rag_test.py
```

This opens an interactive prompt. Type a question in Spanish, and it returns the top-K most semantically similar chunks with similarity scores.

```
Query> ¿De qué trata el video?
Embedding query (3072d) ... done.
Searching ChromaDB (top-3) ... 3 results.
──────────────────────────────────────────────────────────
  #1  similarity: 0.8234  |  distance: 0.1766
       chunk 2  —  hablamos sobre la crisis migratoria en...

  #2  similarity: 0.7891  |  distance: 0.2109
       chunk 5  —  las políticas de frontera han cambiado...
```

Available flags:
| Flag | Default | Effect |
|------|---------|--------|
| `--top-k 5` | 3 | Number of chunks to retrieve per query |

To rebuild the index, use `python backend/scripts/rebuild_index.py` instead.

##### Method B: Sequential extraction (data validation)

```bash
# Both ChromaDB and JSON (default)
python backend/scripts/extract_sample.py

# ChromaDB only
python backend/scripts/extract_sample.py --source chroma

# JSON only (whisper directory)
python backend/scripts/extract_sample.py --source json

# Custom character limit
python backend/scripts/extract_sample.py --chars 2000
```

This reads chunks sequentially from ChromaDB (or raw text from JSON) and prints the first N characters. Useful to verify data roundtripped correctly without writing a query.

##### Method C: Programmatic search (integration)

When you need to query ChromaDB from your own code (e.g., inside a LangChain tool):

```python
from backend.core.embedding_gemini import GeminiEmbeddingProvider
from backend.core.vector_store import VectorStore

provider = GeminiEmbeddingProvider()
store = VectorStore(persist_dir="data/chroma")

query = "¿Qué dice el video sobre migración?"
query_embedding = provider.embed_query(query)
results = store.search(query_embedding, top_k=3)

for r in results:
    print(f"[{r['metadata'].get('title', '?')}] chunk {r['metadata'].get('chunk_index', '?')}")
    print(f"  {r['document'][:200]}...")
    print(f"  similarity: {1 - r['distance']:.4f}")
    print()
```

**What `store.search()` returns:** a list of dicts with keys `id`, `document`, `metadata` (video_id, title, chunk_index, start_time, end_time), and `distance` (cosine distance — lower = more similar).

</details>


<details>
<summary>S03 — ChromaDB Vector Store</summary>

### S03 — ChromaDB Vector Store

> **Source:** [`backend/core/vector_store.py`](backend/core/vector_store.py)

Stores chunk embeddings and retrieves them via semantic search with optional metadata filtering.

**Why ChromaDB over alternatives:**

| | ChromaDB | Pinecone | Weaviate | Qdrant |
|---|---|---|---|---|
| **Deployment** | Local, zero-config | Cloud-only (free tier) | Self-hosted or cloud | Self-hosted or cloud |
| **API keys** | None | Required | Required for cloud | Required for cloud |
| **Python integration** | Native, LangChain built-in | SDK required | SDK required | SDK required |
| **Persistence** | Disk (`data/chroma/`) | Cloud | Disk or cloud | Disk or cloud |
| **Cost** | $0 | Free tier limited | Free tier limited | Free tier limited |

ChromaDB was chosen because it requires no API keys, no external services, and no configuration beyond a directory path. For a solo project with ~200 chunks, a local vector store is sufficient. Pinecone or Weaviate would add operational complexity without benefit at this scale.

**How it works:**

- Collection `migrant_archive` stores documents with 3072d `gemini-embedding-2` vectors and metadata (video_id, title, chunk_index, start_time, end_time, channel, year)
- `store.search(query_embedding, top_k=3)` returns nearest neighbors by cosine distance
- `store.search(query_embedding, top_k=5, video_id="VJqe2h0U1Fs")` scopes results to a single video
- `store.search(query_embedding, top_k=5, year=2024, channel="Plataforma Cero")` combines semantic search with compound metadata filters via ChromaDB's `$and` / `$or` operators
- `store.get_video_metadata("video_id")` returns catalog fields (title, year, channel, chunk_count) from the first chunk, enabling tools to read video metadata without touching JSON files

**Tests:** `test_vector_store.py` (CRUD + relevance) · `test_pipeline_e2e.py` (full pipeline with real video)

</details>


<details>
<summary>S04 — Sample Extraction</summary>

### S04 — Sample Extraction

> **Source:** [`backend/scripts/extract_sample.py`](backend/scripts/extract_sample.py)

Sequentially reads the first 5,000 characters from ChromaDB and raw JSON files to verify the data pipeline roundtripped correctly.

**Why dual-backend extraction:** ChromaDB stores chunked, embedded text. JSON stores raw transcripts. Reading both and comparing confirms that chunking preserved the original content, Spanish characters survived embedding, and metadata (title, timestamps) remained attached to each chunk.

**Key behavior:**
- `--source chroma` extracts from ChromaDB sequentially (not semantically — just reads chunks in order)
- `--source json` extracts from raw JSON files
- `--chars N` sets the character limit (default: 5000)

**Tests:** `test_extract_sample.py` — verifies truncation, dual-backend reads, and character preservation.

</details>


<details>
<summary>S05 — RAG Test + Memory</summary>

### S05 — RAG Test + Memory

> **Sources:** [`backend/scripts/quick_search.py`](backend/scripts/quick_search.py) · [`backend/scripts/rag_test.py`](backend/scripts/rag_test.py) · [`backend/scripts/rebuild_index.py`](backend/scripts/rebuild_index.py) · [`backend/scripts/cero-01.py`](backend/scripts/cero-01.py)

Three entry points that progress from zero-cost keyword search to semantic search to conversational RAG.

```
quick_search.py    →  keyword, no API, no memory
rag_test.py        →  semantic, API embeddings, no memory
rebuild_index.py   →  (re)build the ChromaDB index from whisper JSONs
backend/scripts/cero-01.py → semantic, API embeddings + LLM answers, BUFFER WINDOW memory (K=5)
                                                         ↓
                                               S06: agent_cli.py
                                               (same buffer, LLM reads it + tools)
```

**`quick_search.py` — Fast keyword search (no API, no embeddings)**

The most important verification tool. Searches chunks directly in ChromaDB by keyword — no API key required, no embeddings, no rate limits. If chunking worked, this proves it instantly.

```bash
python backend/scripts/quick_search.py "FilmiG"   # keyword search
python backend/scripts/quick_search.py              # show all chunks
python backend/scripts/quick_search.py --all         # full text dump
```

**`rag_test.py` — Semantic search (embeddings, requires API)**

Interactive script that queries ChromaDB with embeddings. Used to verify the embedding pipeline produces relevant results before building the agent on top. Requires `GEMINI_API_KEY`.

**Why a standalone script:** separating retrieval testing from agent development isolates failures. If semantic search returns irrelevant chunks, the problem is in chunking or embedding — not in the agent's tool-calling logic.

```bash
python backend/scripts/rag_test.py              # interactive Q&A
python backend/scripts/rag_test.py --top-k 5    # custom result count
```

**`rebuild_index.py` — Rebuild the ChromaDB index**

Standalone script that wipes the existing ChromaDB collection and rebuilds it from every whisper JSON found in `data/raw/whisper/`. Run this after adding new videos or changing chunking/embedding settings.

```bash
python backend/scripts/rebuild_index.py
```

**`backend/scripts/cero-01.py` — Conversational RAG with LangChain**

123 lines. The bridge between `rag_test.py` (search only) and `agent_cli.py` (full agent with tools). Built entirely with LangChain: `ConversationalRetrievalChain` orchestrates retrieval + generation, `ConversationBufferWindowMemory` handles the sliding window, `Chroma` + `GoogleGenerativeAIEmbeddings` replace the manual vector store and embedding classes. Zero imports from `backend/core/`.

```bash
uv run python backend/scripts/cero-01.py "¿cómo describen el dolor de migrar?"
uv run python backend/scripts/cero-01.py --verbose "¿qué sentimientos expresan?"  # shows source docs
uv run python backend/scripts/cero-01.py           # REPL mode with history command
```

Key features: answers in Spanish with video/timestamp citations, remembers 5 conversation turns via sliding window buffer, returns source documents with `--verbose`, handles API errors gracefully. The `SYSTEM_PROMPT` is a standalone constant — editable without touching chain logic. See Cero-01-checklist.md for the full evolution from shebang to conversational AI.

</details>


<details>
<summary>S06 — Conversational Agent with Memory</summary>

### S06 — Conversational Agent with Memory

**Agent name: Cero**

> Sources: [`backend/agents/agent.py`](backend/agents/agent.py) · [`backend/agents/tools.py`](backend/agents/tools.py) · [`backend/scripts/agent_cli.py`](backend/scripts/agent_cli.py)

The **Cero** agent answers questions in Spanish using transcripts stored in ChromaDB and remembers conversation context via session-based message history.

**Key decisions:**
- **Native tool calling** (`create_tool_calling_agent`) over ReAct text parsing — eliminated ~30% failure rate on Spanish queries.
- **`RunnableWithMessageHistory`** over deprecated `ConversationBufferMemory` — per-session isolation, cleared on CLI exit and via `DELETE /api/session/{id}`.

#### Agent architecture

```
User → agent_cli.py → Tool Calling Agent (LangChain)
                         ├── list_videos (ChromaDB + JSON fallback)
                         ├── get_video_info (ChromaDB + JSON fallback)
                         ├── search_transcripts (ChromaDB, year/channel filters)
                         ├── Gemini 2.5 Flash (LLM)
                         └── RunnableWithMessageHistory + InMemoryChatMessageHistory
```

##### Agent factory ([`agent.py`](backend/agents/agent.py))

`create_agent()` builds the complete agent pipeline:

1. **LLM**: `ChatGoogleGenerativeAI` with `gemini-2.5-flash` (overridable via
   `GEMINI_MODEL` env var), temperature 0.2, and
   `function_calling_config: { mode: "ANY" }` to force structured tool calls.
2. **Tools**: `list_videos`, `get_video_info`, `search_transcripts` — each
   receives a `Chroma` vector store configured with
   `GoogleGenerativeAIEmbeddings` ("gemini-embedding-2") and the
   `migrant_archive` collection.
3. **Prompt**: `ChatPromptTemplate` with system prompt, optional chat history,
   human input, and agent scratchpad. The `{language}` placeholder is resolved
   at invoke time via `LANGUAGE_NAMES` (ISO code → full name).
4. **Executor**: `AgentExecutor` with `max_iterations=10` and
   `return_intermediate_steps=True` so sources can be parsed from tool
   observations.
5. **Output normalization**: `_normalize_output()` handles Gemini's
   list-of-parts response format, converting it to a plain string for
   downstream consumers.
6. **Memory**: `RunnableWithMessageHistory` wraps the executor, routing each
   `session_id` to its own `BoundedChatMessageHistory` (10 messages = 5 Q&A
   turns). History is stored in-memory (a `dict[str, BoundedChatMessageHistory]`)
   and cleared on CLI exit or `DELETE /api/session/{id}`.

#### Tools and data sources

| Tool | Parameters | Searches in | Purpose |
|------|-----------|-------------|---------|
| `list_videos` | `year=None`, `speaker=None`, `channel=None` | ChromaDB metadata + JSON fallback | List/filter videos — channel/year from store, speakers from JSON |
| `get_video_info` | `video_id` | ChromaDB metadata + JSON fallback | Single video: title, year, channel from store; description, speakers from JSON |
| `search_transcripts` | `query`, `video_id=None`, `year=None`, `channel=None`, `top_k=5` | ChromaDB vector store | Semantic search with optional year/channel compound filters |

- **ChromaDB**: primary data source for channel, year, chunk counts, and semantic search. All three tools read catalog metadata from the vector store.
- **JSON files**: fallback for rich text fields (description, full_text) and speaker extraction. `list_videos` and `get_video_info` only hit disk when the store lacks the requested field.

**Speaker extraction** (`backend/agents/tools.py`): handles 5 description patterns (`Participantes:`, `Nos acompanan:`, `convoca a:`, `Modera:`, title fallback). Unicode math-bold characters normalized to ASCII.

#### Disambiguation flow

The agent does NOT blindly search all transcripts for vague queries — it asks first.

```
User: "De que trata el video?"
Agent: [list_videos] "Tengo 10 videos. Cual te interesa?"
User: "2024"
Agent: [list_videos year=2024] "Uno: Presentacion FILMIG 2024"
User: "ese"
Agent: [search_transcripts video_id="APgxfNssxGQ"] → scoped results
```

#### Query reformulation

Short user questions are rewritten into descriptive English before embedding to improve semantic match quality. "de que va?" → "main topics and key arguments discussed".

#### Memory

The agent keeps the last 5 conversation turns per `session_id` via `BoundedChatMessageHistory` (a subclass of `InMemoryChatMessageHistory` that silently drops the oldest messages when the buffer exceeds `MAX_HISTORY_MESSAGES=10`). Follow-up questions work without repeating context.

```
Pregunta> Que dice Safia El Aaddam sobre racismo?
Agent: [search_transcripts] "Safia El Aaddam argumenta que..."

Pregunta> Y que libros ha escrito?
Agent: [remembers "Safia El Aaddam"] "Ha escrito Hija de inmigrantes..."
```

Type `history` in the CLI to inspect the current message buffer. Each session is isolated — two users won't mix contexts. Memory clears on CLI exit or `DELETE /api/session/{id}`.

#### How to use

```bash
source .venv/bin/activate
python backend/scripts/agent_cli.py
```

Type `history` to inspect the current message buffer and verify the sliding window.

> **Pick your LLM:** defaults to `gemini-2.5-flash`. Change via `GEMINI_MODEL` in `.env`.

#### Tests

```bash
uv run python -m pytest tests/test_agent.py tests/test_speaker_extraction.py -v
```

44 tests: 34 agent (tools, filters, memory, bounded history, disambiguation, scoped search, E2E) + 10 speaker extraction.

</details>


<details>
<summary>S07 — LangSmith, API + Chat Widget</summary>

### S07 — LangSmith, API + Chat Widget

> Sources: [`backend/api/main.py`](backend/api/main.py) · [`backend/api/routes/chat.py`](backend/api/routes/chat.py) · [`frontend/src/chat-widget.ts`](frontend/src/chat-widget.ts) · [`frontend/src/`](frontend/src/) (7 modules)

The **Cero** agent is exposed as a REST API with LangSmith tracing and an embeddable chat widget.

#### LangSmith Tracing

Every agent run traced automatically — zero application code. `langsmith` hooks into LangChain's callback system when it detects `LANGSMITH_TRACING=true` at import time. No changes to `agent.py` required.

```bash
# .env
LANGSMITH_TRACING=true
LANGSMITH_API_KEY=lsv2_pt...
LANGSMITH_PROJECT=migrant-archive
LANGSMITH_ENDPOINT=https://api.smith.langchain.com
```

Traces show: LLM calls, tool executions, latency, token usage, cost. Appear live at [smith.langchain.com](https://smith.langchain.com).

**Test safety:** [`tests/conftest.py`](tests/conftest.py) forces `LANGSMITH_TRACING=false` during pytest via a session-scoped autouse fixture. [`tests/test_langsmith.py`](tests/test_langsmith.py) (3 tests) verifies the guard.

**Free tier:** 5,000 traces/month — well under the project's usage.

#### Architecture

```
Browser widget ──POST /api/ask──► FastAPI ──► Agent (Cero) ──► ChromaDB
                                     │
                                  Gemini LLM
```

#### Start the API

```bash
uv run uvicorn backend.api.main:app --reload --port 8000
```

#### API details

| Endpoint | Method | Request | Response |
|----------|--------|---------|----------|
| `/api/ask` | POST | `{"question": "string", "session_id": "string"}` | `{"answer": "string", "sources": [...]}` |
| `/api/transcribe` | POST | `multipart audio file + optional language query param` | `{"text": "string"}` |
| `/api/session/{session_id}` | DELETE | — | `{"session_id": "string", "cleared": bool}` |

Each source: `video_id`, `title`, `start_time`, `end_time`, `text`. Session defaults to `"default"`. Errors: `422` (empty question), `503` (no API key).

#### Tests

```bash
uv run python -m pytest tests/test_api.py tests/test_frontend.py -v
```

Tests cover API models, routes, session lifecycle, CORS, error handling, source parsing, frontend build, widget structure, and accessibility.

#### Start the chat widget

```bash
cd frontend && pnpm install && pnpm dev
```

Open `http://localhost:5173`. Cero avatar floating bottom-right — click to open the side panel. Zero-state shows a greeting and three clickable suggestion cards. Type a question or click a suggestion. Agent responses include clickable YouTube links inline. Dark theme, responsive (full-width below 640px). Keyboard accessible (Escape to close, Enter to send, Tab navigation).

The widget uses `/cero-agent-icon.png` as the Cero avatar across all states: FAB button, panel header, and zero-state greeting.

#### Frontend Architecture

The chat widget is built as 8 independent ES modules wired together by a single
orchestrator. Each module is a focused, testable unit.

| Module | File | Role |
|--------|------|------|
| Bootstrap | [`main.ts`](frontend/src/main.ts) | Mounts the widget on `DOMContentLoaded` |
| Orchestrator | [`chat-widget.ts`](frontend/src/chat-widget.ts) | State, wiring, session lifecycle, API calls |
| FAB | [`fab.ts`](frontend/src/fab.ts) | Floating action button with avatar + ARIA |
| Panel | [`panel.ts`](frontend/src/panel.ts) | Side panel shell (30%), language selector, refresh |
| Zero-state | [`zero-state.ts`](frontend/src/zero-state.ts) | Greeting + 3 clickable suggestion cards |
| Input bar | [`input-bar.ts`](frontend/src/input-bar.ts) | Text input + send button + voice recording |
| Message list | [`message-list.ts`](frontend/src/message-list.ts) | Conversation rendering + source citations |
| API client | [`api-client.ts`](frontend/src/api-client.ts) | Typed fetch wrapper, 60s timeout, error normalization |

##### Orchestrator ([`chat-widget.ts`](frontend/src/chat-widget.ts))

The `ChatWidget` class manages all widget state and wires modules together.
It does not render UI itself — every module owns its own DOM.

**Session lifecycle:**
- On construction, a `session_id` is generated via `crypto.randomUUID()`
- The language is loaded from `localStorage` (key: `migrant-archive-lang`)
- Changing the language or resetting the conversation generates a new
  `session_id` and clears the backend session via `DELETE /api/session/{id}`
- A confirm dialog (i18n) guards the reset action

**State transitions:**
```
closed ──FAB click──► open (zero-state visible)
                         │
                    suggestion click
                    or typed question
                         │
                         ▼
                      loading (message list visible, input disabled)
                         │
                    API response
                         │
                    ┌────┴────┐
                    ▼         ▼
                 answer    error
                 rendered   message
```

**Key behaviors:**
- FAB is hidden while the panel is open, restored on close
- Escape key closes the panel
- `setLanguage()` propagates to all 6 modules, resets session if conversation has started
- Loading state disables input, send, and voice buttons to prevent double-submit

##### Dev server proxy ([`vite.config.ts`](frontend/vite.config.ts))

The Vite dev server proxies `/api/*` requests to the FastAPI backend at
`localhost:8000` with a 120-second timeout. This means the frontend calls
`/api/ask` and `/api/transcribe` without hardcoded hostnames — the proxy
handles routing in development. The `build.outDir` is `dist/`.

</details>

<details>
<summary>S08 — Frontend + Deploy</summary>

### S08 — Frontend + Deploy

> Sources: [`frontend/src/`](frontend/src/) · [`presentation/migrant-archive-slides.html`](presentation/migrant-archive-slides.html) · [`transcribe.py`](backend/api/routes/transcribe.py) · [`input-bar.ts`](frontend/src/input-bar.ts) · [`main.py`](backend/api/main.py)

The final phase: presentation, deploy, polish, and voice input. See [Progress Dashboard](#progress-dashboard) for current priority order.

#### What's done

- **Chat widget** (`frontend/src/`): FAB toggle, side panel (30%), zero-state with 3 suggestion cards, bottom-anchored input bar with voice button, dark theme, responsive, keyboard/ARIA accessible. YouTube links generated in backend.
- **Presentation** (`presentation/migrant-archive-slides.html`): 18-slide HTML deck
- **Voice input** ([`input-bar.ts`](frontend/src/input-bar.ts) + [`transcribe.py`](backend/api/routes/transcribe.py)): complete via Groq Whisper API (`whisper-large-v3-turbo`), free tier 2000 requests/day. 30-second maximum recording with visual countdown (last 3 seconds). Manual stop or auto-stop at 30s. Error handling for permission denied, network errors, empty speech, and service unavailable. Works in all browsers (Chrome, Firefox, Brave, Safari).
- **Multilingual support**: language selector dropdown in panel header with 6 languages (EN/ES/CA/FR/PT/DE). Type-to-filter and keyboard navigation. Selected language persists in localStorage. Session resets on language change. All UI text translates: greeting, suggestions, input bar, error messages, and confirm dialogs. Backend uses dynamic agent prompt via language parameter and Groq transcription language hint. Agent responds in the selected language.

#### Voice

Voice input is a browser-capture → backend-proxy → Groq transcription pipeline. The browser records audio with `MediaRecorder`, sends it to the FastAPI `/api/transcribe` endpoint, and receives plain text back.

```
Browser                         Backend                        Groq Cloud
───────                         ───────                        ──────────
MediaRecorder ──POST /api/transcribe──► transcribe.py ──► whisper-large-v3-turbo
     ◄────────── { text } ────────────◄──── { text } ────────────◄
```

##### Backend implementation ([`transcribe.py`](backend/api/routes/transcribe.py))

- **File**: [`transcribe.py`](backend/api/routes/transcribe.py) (129 lines)
- **SDK**: uses the `groq` Python package with an `AsyncGroq` client
- **Pattern**: lazy singleton — `_get_client()` creates the `AsyncGroq` instance once and reuses it across requests
- **Model**: `whisper-large-v3-turbo`, response format `json`
- **Flow**: receives a multipart `UploadFile`, validates size (25 MB max), language code, and non-empty payload, then forwards the bytes directly to Groq without writing to disk, and returns `TranscribeResponse { text }`
- **Requirement**: `GROQ_API_KEY` in `.env`

All HTTP errors in the table below are raised from [`transcribe.py`](backend/api/routes/transcribe.py):

| Status | Cause |
|--------|-------|
| `400` | bad request, empty audio, or invalid language |
| `413` | file too large |
| `422` | no speech detected |
| `429` | Groq rate limit |
| `503` | service unavailable or authentication failure |
| `504` | timeout |

##### Frontend implementation ([`input-bar.ts`](frontend/src/input-bar.ts))

- **File**: [`input-bar.ts`](frontend/src/input-bar.ts) (564 lines)
- **Capture**: `MediaRecorder` API with MIME negotiation: `audio/webm;codecs=opus` → `audio/webm` → `audio/mp4` (Safari fallback)
- **State machine**:

  ```
  idle ──click──► listening ──start──► recording ──stop──► processing ──► success
                       │                    │                  │              │
                       ▼                    ▼                  ▼              ▼
                   permission          auto-stop           error hint      text in
                   denied hint         at 30s              displayed       input field
  ```

- **UX details**:
  - visual countdown (last 3 seconds shown in the placeholder)
  - manual stop or auto-stop at 30 seconds
  - success flash (green ring for 2 seconds)
  - error hints: permission denied, no speech, connection error, service unavailable, audio too large
- **Language hint**: passes the selected UI language as a `?language=` query parameter so Groq can optimize transcription

##### Data model ([`models.py`](backend/api/models.py))

- **File**: [`models.py`](backend/api/models.py)
- **`TranscribeResponse`**: `{ text: string }`
- **`ALLOWED_LANGUAGES`**: `{"en", "es", "ca", "fr", "pt", "de"}` — validated on both the frontend (type-to-filter) and the backend (Pydantic validator plus the language check in [`transcribe.py`](backend/api/routes/transcribe.py))

#### Backend API Architecture

The FastAPI backend serves two route groups from a single process. Every request is independent — session state is isolated per `session_id`.

##### App factory ([`main.py`](backend/api/main.py))

- `create_app()` builds the FastAPI instance with CORS middleware (default origins: `localhost:5173` for the Vite dev server)
- mounts two routers under `/api`: `chat` (`POST /api/ask`, `DELETE /api/session/{id}`) and `transcribe` (`POST /api/transcribe`)
- custom validation error handler returns structured 422 responses

##### Agent singleton ([`dependencies.py`](backend/api/dependencies.py))

- `get_agent()` creates the LangChain agent once and caches it globally
- the agent is wrapped with `RunnableWithMessageHistory` so each `session_id` gets its own isolated conversation history
- raises 503 if `GEMINI_API_KEY` is not configured
- the `create_agent()` factory is imported from [`agent.py`](backend/agents/agent.py)

##### Chat route ([`chat.py`](backend/api/routes/chat.py))

- `POST /api/ask` — accepts `AskRequest { question, session_id, language }`, invokes the agent with the session config, returns `AskResponse { answer, sources[] }`
- `DELETE /api/session/{id}` — clears the message history for that session
- YouTube links are generated in the backend (deterministic, no HTML injection)
- sources are parsed from agent intermediate steps and include `video_id`, `title`, `start_time`, `end_time`, and `text`

##### Transcription route ([`transcribe.py`](backend/api/routes/transcribe.py))

- `POST /api/transcribe` — documented in the Voice section above

##### YouTube linkification ([`chat.py`](backend/api/routes/chat.py))

Agent answers contain bare YouTube video IDs. Before the response reaches the
browser, `linkify_answer()` replaces each video ID with a clickable
`<a href="https://www.youtube.com/watch?v=VIDEO_ID&t=SECONDS">` tag while
HTML-escaping all surrounding text. The replacement uses a negative
lookbehind regex to avoid double-linking URLs already present. Each source's
`start_time` is converted to seconds via `_parse_time_to_seconds()` which
handles `HH:MM:SS`, `MM:SS`, and bare-seconds formats.

##### Source parsing ([`chat.py`](backend/api/routes/chat.py))

Agent tool observations (from `search_transcripts`) are plain text blocks.
`parse_sources()` extracts structured `Source` objects via a regex that
matches the `search_transcripts` output format:

```
[N] Title [Speaker] (start–end) | VIDEO_ID
Text content
```

Each extracted source includes `video_id`, `title`, `start_time`, `end_time`,
and `text`. Speaker tags appended by `tools.py` (e.g. `[Lucia Mbomio]`) are
stripped from the title. Empty or missing intermediate steps return an empty
list gracefully.

#### Internationalization

- **Language selector**: dropdown in panel header (ENG circle + chevron)
- **6 languages**: EN/ES/CA/FR/PT/DE with full i18n across zero-state, input-bar (20+ strings), FAB, message-list, and panel
- **Allowed languages**: defined in `ALLOWED_LANGUAGES` in `backend/api/models.py`
- **Flow**: the language parameter flows through `AskRequest.language` → agent prompt → LLM response language
- **Codes**: the language selector uses ISO 639-1 codes (EN, ES, CA, FR, PT, DE)
- **Backend**: dynamic agent prompt via language parameter; Groq transcription receives a language hint
- **Behavior**: agent responds in the selected language; session resets on language change

#### Deploy options (TBD)

| Platform | Pros | Cons |
|----------|------|------|
| **Railway** | Simple, Python-native, free tier | Cold starts on free tier |
| **Fly.io** | Global edge, persistent volumes | More config required |
| **Cloudflare Pages + Workers** | Fast CDN, free tier generous | Need Workers for Python backend |

</details>

---

<details>
<summary>Tests</summary>

### Tests

> Test files: [`tests/`](tests/) — [`test_embedding.py`](tests/test_embedding.py) · [`test_embedding_gemini.py`](tests/test_embedding_gemini.py) · [`test_processor.py`](tests/test_processor.py) · [`test_vector_store.py`](tests/test_vector_store.py) · [`test_pipeline_e2e.py`](tests/test_pipeline_e2e.py) · [`test_extract_sample.py`](tests/test_extract_sample.py) · [`test_ingestion.py`](tests/test_ingestion.py) · [`test_faster_whisper_audio.py`](tests/test_faster_whisper_audio.py) · [`test_faster_whisper_colab.py`](tests/test_faster_whisper_colab.py) · [`test_rebuild_index.py`](tests/test_rebuild_index.py) · [`test_agent.py`](tests/test_agent.py) · [`test_speaker_extraction.py`](tests/test_speaker_extraction.py) · [`test_api.py`](tests/test_api.py) · [`test_frontend.py`](tests/test_frontend.py) · [`test_langsmith.py`](tests/test_langsmith.py)

```bash
# UV environment
source .venv/bin/activate
python -m pytest tests/ -v

```

**Results:** 223 passed, 1 skipped, 0 failed. Conditional skips apply when `GEMINI_API_KEY` is not set or a GPU is unavailable; the E2E layer is skipped without an API key.

| Layer | Tests | Files | What it proves |
|-------|-------|-------|----------------|
| Unit | 53 | `test_embedding.py`, `test_processor.py`, `test_vector_store.py`, `test_ingestion.py` | 53 unit tests covering contract enforcement, chunking logic, CRUD operations, timestamp helpers |
| Integration | 64 | `test_embedding_gemini.py`, `test_extract_sample.py`, `test_faster_whisper_audio.py`, `test_faster_whisper_colab.py`, `test_api.py`, `test_rebuild_index.py` | 64 integration tests covering real providers, extraction from real JSON, audio/colab strategies, API routes, index rebuild |
| Agent | 34 | `test_agent.py` | 3-tool calling agent, disambiguation, scoped search, session memory, prompt assertions, E2E |
| Speaker | 10 | `test_speaker_extraction.py` | Description pattern extraction, math-bold unicode normalization, channel fallback |
| Frontend | 57 | `test_frontend.py` | Vite build, widget modules, API client, FAB, panel, zero-state, input bar, message list, integration, accessibility |
| Observability | 3 | `test_langsmith.py` | Tracing guard fixture, env-var isolation, integration test with fake key |
| E2E | 2 | `test_pipeline_e2e.py` | Full pipeline with Gemini API (needs key) |


</details>

---

<details>
<summary>Saturday Checkpoints</summary>

### Saturday Checkpoints

Weekly presentations to Ironhack instructors. Each checkpoint evaluates specific competencies.

#### Checkpoint 1 — Sat 13 Jun: Project Plan

**Status:** Done

Complete 4-week development plan: architecture, timeline, technology choices, and strategy before any code.

**Evidence:**
- `plan-1.md` — architecture decisions, tech stack, timeline
- `project-3-business-case-multimodal-ai-chatbot-for-yt-video-qa/README.md` — business case and deliverable requirements

#### Checkpoint 2 — Sat 20 Jun: Vector Database Q&A Demo

**Status:** Done

RAG pipeline end-to-end: transcribed video content stored in ChromaDB and retrievable via semantic search. Direct vector DB queries, no agent.

**CLI demo:**

```bash
source .venv/bin/activate
python backend/scripts/rebuild_index.py   # build index (first time)
python backend/scripts/rag_test.py              # interactive Q&A
```

**Pre-verified questions:**

| Question | Expected result |
|----------|----------------|
| "De que trata el video?" | Top-3 chunks with similarity scores, titles, and timestamps |
| "Que dice sobre migracion?" | Chunks about migration with `[MM:SS]` timestamps, similarity > 0.7 |

**Evidence files:**
- `backend/scripts/rag_test.py` — interactive RAG query script
- `backend/scripts/extract_sample.py` — sequential data extraction (data roundtrip)

**Sample extraction usage:**

```bash
python backend/scripts/extract_sample.py               # both backends
python backend/scripts/extract_sample.py --source chroma  # ChromaDB only
python backend/scripts/extract_sample.py --source json    # JSON only
python backend/scripts/extract_sample.py --chars 2000     # custom length
```

**Verified:** data readable in both backends, Spanish characters preserved, ChromaDB chunks maintain title metadata and sequential order.

#### Checkpoint 3 — Sat 27 Jun: Agent, Tools, and Memory

**Status:** Done

Conversational agent (Cero) with 3 tools, disambiguation, scoped semantic search, and session-based memory.

**Evaluated competencies:**
- Native tool calling via Gemini 2.5 Flash (`create_tool_calling_agent`)
- 3 tools: `list_videos` (metadata filter), `get_video_info` (detail), `search_transcripts` (scoped or global)
- Memory: `RunnableWithMessageHistory` + `InMemoryChatMessageHistory` (replaces deprecated `ConversationBufferMemory`)
- Disambiguation: agent resolves ambiguity via `list_videos` before semantic search
- Scoped search: `search_transcripts` with `video_id` uses ChromaDB `where` metadata filter

**Demo:**

```bash
source .venv/bin/activate
python backend/scripts/agent_cli.py
```

**Round 1 — Metadata and disambiguation:**

```
Pregunta> Que videos tienes?
[list_videos → 10 videos with title, year, channel, speakers when available]

Pregunta> Que videos son de 2024?
[list_videos year=2024 → 1 video: Presentacion FILMIG 2024]

Pregunta> Dame informacion del video Escrituras Otras
[get_video_info → channel: Plataforma Cero, speakers: Lucia Mbomio Rubio,
 Safia El Aaddam, Desirée Bela-Lobedde]
```

**Round 2 — Scoped semantic search:**

```
Pregunta> Que dice Safia El Aaddam en Escrituras Otras?
[search_transcripts video_id="VJqe2h0U1Fs" → chunks only from that video,
 bulleted summary with timestamps]

Pregunta> De que trata el conversatorio sobre produccion cultural migrante?
[identifies CTmWjuQcvHY → participants: Vivi Alfonsin, Moha Gerehou,
 Dagmary Olívar, Silvia Ramirez. Topic summary with sources.]
```

**Round 3 — Memory:**

```
Pregunta> Cual es el canal de los videos?
[Plataforma Cero — from channel field]

Pregunta> y cuantos videos tienen ponentes?
[memory from previous context → 4 of 10 videos have identified speakers]
```

**Pre-verified questions:**

| Question | Tool tested | Expected |
|----------|------------|----------|
| "Que videos tienes?" | `list_videos` | 10 videos, numbered list, years, channel |
| "Que videos son de 2024?" | `list_videos` year filter | 1 result: "Presentacion FILMIG 2024" |
| "Dame informacion del video Escrituras Otras" | `get_video_info` | Metadata + 3 speakers |
| "Que dice Safia El Aaddam en Escrituras Otras?" | `search_transcripts` scoped | Chunks from VJqe2h0U1Fs only, bulleted, timestamps |
| "De que trata el conversatorio sobre produccion cultural migrante?" | Disambiguation + scoped search | CTmWjuQcvHY, 4 participants, topic summary |
| "Como describen la experiencia migrante en La Cara B?" | `search_transcripts` scoped | Chunks from Jc1xJ4V4xU4, bulleted, timestamps |
| "Que es FILMIG?" | `get_video_info` | Definition from description |
| "De que va el de Palestina?" | Disambiguation + `get_video_info` | myxPJCDedOE, Nadia Jabr + Mohamad Bitari |
| "y en que minuto mencionaron eso?" | Memory | Follow-up references prior answer |

**Evidence files:**

| File | Role |
|------|------|
| `backend/agents/agent.py` | Agent + system prompt (reformulation, lists, channel/speakers) |
| `backend/agents/tools.py` | 3 tools + speaker extraction (5 patterns, math-bold normalization) |
| `backend/core/vector_store.py` | Scoped search via ChromaDB `where` filter + `get_unique_videos()` |
| `backend/scripts/agent_cli.py` | Interactive CLI with session lifecycle |
| `tests/test_agent.py` | 34 tests: tools, memory, disambiguation, scoped search, E2E |
| `tests/test_speaker_extraction.py` | 10 tests: 5 description patterns, normalization, fallback |

**Design justification:**
- [Native Tool Calling](#s06--conversational-agent-with-memory) — Gemini 2.5 Flash structured `tool_call` objects, zero parsing failures
- [Message History](#s06--conversational-agent-with-memory) — `RunnableWithMessageHistory` replaces deprecated `ConversationBufferMemory`
- [ChromaDB metadata filtering](https://docs.trychroma.com/usage-guide#filtering-by-metadata) — native `where` filter, no post-processing
- [Strategy Pattern](#s01--video-ingestion) — JSON metadata uses same `VideoData` contract as ingestion

#### Checkpoint 4 — Sat 4 Jul: TBD

**Status:** Pending

Criteria not yet defined by Ironhack.

**Ready:**
- LangSmith tracing (auto-tracing via env vars)
- FastAPI REST API (`POST /api/ask`, `DELETE /api/session/{id}`)
- Chat widget (Vite + TypeScript, FAB + side panel, dark theme, 7 modules)
- Presentation slides (`presentation/migrant-archive-slides.html`, 18 slides)
- 223 passed, 1 skipped, 0 failed

</details>
