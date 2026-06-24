# Migrant Archive — Narratives That Resist

**Agent name: Cero**

Multimodal RAG chatbot that answers questions about YouTube video content.
Built on the FILMIG / Plataforma Cero channel (Spanish).

---

## Development Timeline

| Week | Steps | Focus | Status |
|------|-------|-------|--------|
| 1 | 1–2 | Ingestion + Processing — dual transcription, chunking, embeddings, ChromaDB | Done |
| 2 | 3–4 | Agents + Testing — LangChain agent with tools/memory, test suite | Done |
| 3 | 5–6 | API + Evaluation — FastAPI REST wrapper done, LangSmith tracing complete | In progress |
| 4 | 7–8 | Frontend + Deploy — Web Speech API voice input, presentation | Pending |

---

> **Week 1 checkpoint (completed):** Live vector DB Q&A demo + sample extraction.
> - **Interactive RAG query:** `backend/scripts/rag_test.py` — query ChromaDB directly with Spanish questions about the transcribed videos
> - **Data extraction:** `backend/scripts/extract_sample.py` — dump first 5,000 characters from ChromaDB and/or JSON sources to prove data is stored and retrievable

---

## Pipeline Architecture

```
FILMIG / Plataforma Cero (YouTube)
         │
         ▼
   ┌─ S 01 ──────────────────────────────────────────┐
   │  Video Ingestion — 3 strategies                 │
   │  A: YouTube auto-captions (instant, free)       │
   │  B: faster-whisper CPU (small, ~2 min/4min vid) │
   │  B GPU: Colab large-v3 (~15 s/4min vid)         │
   │  Output: {video_id}.json (Spanish transcript)   │
   └──────────────────────┬─────────────────────────┘
                          │
                          ▼
   ┌─ S 02 ──────────────────────────────────────────┐
   │  Text Chunking + Embedding                      │
   │  Chunk: 1,000 tokens / 200 overlap (20%)        │
   │  Enriched text: title + description + [MM:SS]   │
   │  Embed: Gemini (3072d) | BGE-M3 (1024d)         │
   │  Output: chunks + vector embeddings             │
   └──────────────────────┬─────────────────────────┘
                          │
                          ▼
   ┌─ S 03 ──────────────────────────────────────────┐
   │  ChromaDB Vector Store                          │
   │  Persistent storage, semantic search            │
   │  top_k retrieval with metadata                  │
   │  Output: queryable knowledge base               │
   └──────────────────────┬─────────────────────────┘
                          │
               ┌───────────┴───────────┐
               ▼                       ▼
        ┌─ S 04 ──────────┐     ┌─ S 05 ──────────┐
        │  RAG Test       │     │  Sample Extract │
        │  Interactive QA │     │  First 5K chars │
        │  ChromaDB direct│     │  ChromaDB + JSON│
        │  Week 1 demo    │     │  Roundtrip      │
        └────────┬────────┘     └────────┬────────┘
                 │                       │
                 └───────────┬───────────┘
                             ▼
                        ┌─ S 06  ───────────────────────────────┐
                         │  LangChain Agent                      │
                        │  Tools: search_transcripts            │
                        │  Memory: InMemoryChatMessageHistory   │
                        │  Agent: create_tool_calling_agent     │
                        │  16/16 agent tests                    │
                        │  Status: Complete                     │
                       └───────────────────┬───────────────────┘
                                           ▼
                                 ┌─ S 07 ───────────────────────┐
                                  │  API + Chat Widget                 │
                                 │  FastAPI REST wrapper        │
                                 │  Status: API Complete        │
                                 │  LangSmith: Complete         │
                                └──────────────┬───────────────┘
                                               ▼
                                      ┌─ S 08 ───────────────────────┐
                                       │  Frontend + Deploy                 │
                                      │  Web Speech API voice input  │
                                      │  HTML presentation slides    │
                                      │  Multimodal RAG chatbot      │
                                      └──────────────────────────────┘
```

> **How to read this diagram:** each node (`S 01`–`S 08`) represents a processing stage. Nodes connected vertically are sequential; horizontal forks are parallel alternatives or complementary outputs. The pipeline flows top-to-bottom, mirroring the 4-week development timeline above.
>
> **Implementation map:** each stage links to the source file(s) that implement it:
> - **S01 (Ingestion):** [`ingestion.py`](backend/core/ingestion.py) · [`ingestion_audio.py`](backend/core/ingestion_audio.py) · [`ingestion_caption.py`](backend/core/ingestion_caption.py) · [`ingestion_colab.py`](backend/core/ingestion_colab.py)
> - **S02 (Chunking + Embedding):** [`processor.py`](backend/core/processor.py) · [`embedding_gemini.py`](backend/core/embedding_gemini.py) · [`embedding_bge_m3.py`](backend/core/embedding_bge_m3.py)
> - **S03 (ChromaDB):** [`vector_store.py`](backend/core/vector_store.py)
> - **S04–S05 (Scripts):** [`rag_test.py`](backend/scripts/rag_test.py) · [`extract_sample.py`](backend/scripts/extract_sample.py)
> - **S06 (Agent):** [`backend/agents/agent.py`](backend/agents/agent.py) · [`backend/agents/tools.py`](backend/agents/tools.py) · [`backend/scripts/agent_cli.py`](backend/scripts/agent_cli.py)
> - **S07 (API + Chat Widget):** [`backend/api/main.py`](backend/api/main.py) · [`backend/api/routes/chat.py`](backend/api/routes/chat.py) · [`frontend/src/chat-widget.ts`](frontend/src/chat-widget.ts)
> - **S08 (Frontend + Deploy):** [`frontend/src/main.ts`](frontend/src/main.ts) · [`frontend/src/styles.css`](frontend/src/styles.css) · [`presentation/`](presentation/)

---

## Choose Your Environment

This project has two paths. Pick the one that fits your needs.

| | UV (lightweight) | Conda (ML-ready) |
|---|---|---|---|
| **Best for** | Gemini API embeddings | BGE-M3 local embeddings |
| **What you get** | Transcription + Gemini cloud embeddings | Transcription + Gemini + BGE-M3 local |
| **Install size** | ~500 MB | ~4 GB (includes PyTorch) |
| **GPU needed?** | No | No (CPU inference) |
| **Internet required?** | Yes (for Gemini API) | Only for YouTube download |
| **API keys?** | Gemini (free tier) | None for embeddings |

> **Don't know which to choose?**
> Start with UV + Gemini. It's faster to set up and the Gemini free tier covers the entire project's embedding needs (~$0.10 total). You can add Conda later if you want local embeddings.

---

### Option A: UV + Gemini (recommended start)

**What you need:** Python 3.12+, FFmpeg, a Gemini API key.

#### 1. Install UV

```bash
# macOS / Linux
curl -LsSf https://astral.sh/uv/install.sh | sh

# Windows (PowerShell)
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

#### 2. Create the environment

```bash
# macOS / Linux / Windows
uv venv --python 3.12
source .venv/bin/activate      # macOS / Linux
# .venv\Scripts\activate       # Windows (PowerShell)
```

#### 3. Install everything

```bash
uv pip install -r requirements.txt
```

#### 4. Add your Gemini API key

```bash
cp .env.example .env
# Edit .env → set GEMINI_API_KEY=your-key-here
```

Get your free key at [aistudio.google.com/apikey](https://aistudio.google.com/apikey). The free tier is more than enough for this project.

#### 5. Install FFmpeg (system dependency)

```bash
# macOS
brew install ffmpeg

# Ubuntu / Debian
sudo apt-get install ffmpeg

# Windows
winget install ffmpeg
```

---

### Option B: Conda + BGE-M3 (full local stack)

**What you need:** Conda, Python 3.12+, FFmpeg. No API keys required for embeddings.

#### 1. Install Conda

```bash
# macOS / Linux — Miniconda (recommended)
curl -LsSf https://repo.anaconda.com/miniconda/Miniconda3-latest-MacOSX-x86_64.sh -o miniconda.sh
bash miniconda.sh

# Windows — Miniconda
# Download from: https://docs.anaconda.com/miniconda/
```

#### 2. Create the environment

```bash
# macOS / Linux / Windows
conda create -n migrant-archive python=3.12 -y
conda activate migrant-archive
```

#### 3. Install PyTorch (via Conda — handles native compilation)

```bash
conda install pytorch transformers -c defaults -y
```

#### 4. Install the rest (via pip inside Conda)

```bash
pip install sentence-transformers chromadb google-genai pytest python-dotenv yt-dlp youtube-transcript-api faster-whisper
```

#### 5. (Optional) Add Gemini API key

If you want to use Gemini as a cloud alternative: create `.env` with `GEMINI_API_KEY=your-key`. BGE-M3 works without it.

#### 6. Install FFmpeg

Same as Option A above.

---

## Quick Start Walkthrough

This walkthrough shows the step-by-step progression from raw YouTube videos to the chat widget. Each step links to the detailed section where the command is fully explained.

### Step 0 — Ingest videos (transcription)

Download and transcribe YouTube videos. Repeat for each video.

```bash
python backend/core/ingestion_audio.py --url "VIDEO_URL" --lang es
```

Output: `data/raw/whisper/{video_id}.json` (one JSON per video with transcript + metadata).

Full details: [Phase 1 — Video Ingestion](#phase-1--video-ingestion-transcription).

### Step 1 — Build the vector index (embeddings)

Chunk transcript text, generate Gemini embeddings, and store in ChromaDB. Run once after adding new videos.

```bash
python backend/scripts/rag_test.py --rebuild
```

Full details: [Phase 2 — Embeddings + Vector Store](#phase-2--embeddings--vector-store) and [Embeddings Workflow](#embeddings-workflow).

### Step 2 — Query (simple RAG, no memory)

Search ChromaDB directly. No agent, no memory — just semantic search.

```bash
python backend/scripts/rag_test.py
```

Type a question in Spanish. Returns top-k most similar transcript chunks.

Full details: [Scenario 3 — Reading / Querying Embeddings](#scenario-3--reading--querying-embeddings).

### Step 3 — Query with memory (agent CLI)

Same ChromaDB, but with conversation context. The agent remembers previous turns.

```bash
python backend/scripts/agent_cli.py
```

Full details: [S06 — Conversational Agent with Memory](#s06--conversational-agent-with-memory).

### Step 4 — Query through the web widget

Start the API and frontend, then open the browser.

**Terminal 1 — API:**
```bash
uv run uvicorn backend.api.main:app --reload --port 8000
```

**Terminal 2 — Frontend:**
```bash
cd frontend && pnpm install && pnpm dev
```

Open `http://localhost:5173`. Click the blue bubble (bottom-right). The chat panel opens. Full details: [S07 — API + Chat Widget](#s07--api--chat-widget).

### Quick verification checklist

- [ ] Step 0: `data/raw/whisper/` contains transcribed `.json` files
- [ ] Step 1: `data/chroma/` exists and is populated (run `--rebuild` if not)
- [ ] Step 2: `rag_test.py` returns relevant chunks for a Spanish query
- [ ] Step 3: `agent_cli.py` answers and remembers context across turns
- [ ] Step 4: API returns 200 on `POST /api/ask`, widget renders and sends messages
- [ ] Step 5: Agent traces appear at [smith.langchain.com](https://smith.langchain.com) → project `migrant-archive`

---

## Project Structure

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
│   │       └── chat.py         ← POST /api/ask + DELETE /api/session/{id}
│   ├── agents/
│   │   ├── agent.py            ← Tool-calling agent + per-session message history
│   │   └── tools.py            ← search_transcripts tool
│   ├── core/
│   │   ├── ingestion.py        ← VideoData dataclass + shared helpers
│   │   ├── ingestion_caption.py    ← Strategy A: YouTube auto-captions
│   │   ├── ingestion_audio.py      ← Strategy B: faster-whisper local CPU
│   │   ├── ingestion_colab.py      ← Strategy B GPU: Colab wrapper
│   │   ├── embedding.py            ← EmbeddingProvider (abstract contract)
│   │   ├── embedding_gemini.py     ← Gemini API implementation
│   │   ├── embedding_bge_m3.py     ← BGE-M3 local implementation
│   │   ├── processor.py            ← Chunking (1000tk/200ov) + embedding
│   │   └── vector_store.py         ← ChromaDB persistence
│   └── scripts/
│       ├── agent_cli.py        ← Interactive agent CLI
│       ├── rag_test.py         ← Interactive RAG pipeline test script
│       └── extract_sample.py   ← First-5K extraction from ChromaDB + JSON
│
├── frontend/
│   ├── index.html              ← Widget mount point
│   ├── package.json            ← pnpm dependencies
│   ├── vite.config.ts          ← Vite + API proxy config
│   └── src/
│       ├── main.ts             ← Widget bootstrap
│       ├── chat-widget.ts      ← Chat widget logic
│       └── styles.css          ← Widget styles
│
├── tests/
│   ├── conftest.py             ← Shared pytest fixtures + LangSmith guard
│   ├── test_agent.py           ← Agent, tool, memory, CLI tests
│   ├── test_langsmith.py       ← LangSmith tracing + fixture tests
│   ├── test_api.py             ← API models, routes, CORS, errors
│   ├── test_frontend.py        ← Frontend build + widget structure
│   ├── test_embedding.py       ← Contract tests (FakeEmbeddingProvider)
│   ├── test_embedding_gemini.py ← Gemini provider tests
│   ├── test_embedding_bge_m3.py ← BGE-M3 provider tests
│   ├── test_processor.py       ← Chunking + orchestration tests
│   ├── test_vector_store.py    ← ChromaDB CRUD + relevance tests
│   ├── test_pipeline_e2e.py    ← Full pipeline with real video
│   ├── test_extract_sample.py  ← First-5K extraction + truncation tests
│   ├── test_ingestion.py       ← VideoData + timestamp helper tests
│   ├── test_faster_whisper_audio.py ← faster-whisper strategy tests
│   └── test_faster_whisper_colab.py ← Colab notebook validation tests
│
├── data/
│   ├── audio/                  ← Downloaded audio cache (gitignored)
│   ├── chroma/                 ← ChromaDB persistent storage (gitignored)
│   └── raw/
│       ├── captions/           ← Caption strategy JSON output
│       └── whisper/            ← Whisper strategy JSON output
│
├── models/
│   └── whisper/                ← faster-whisper model files (gitignored)
│
├── presentation/               ← HTML slides for project demo
│
├── notebooks/                  ← Colab notebooks for cloud GPU processing
│   └── transcribe_video_colab.ipynb  ← Transcribe long videos with T4 GPU
│
└── notes/                      ← Decision records + research
    ├── session-1-ingestion.md
    ├── session-2-embeddings-research.md
    ├── session-2-chunking-and-testing.md
    ├── agent-tools-discovery.md
    ├── faster-whisper-migration.md    ← Why faster-whisper over WhisperX
    ├── uv.md
    └── rag_test_questions.md   ← Pre-verified questions for vector DB demo
```

---

## Phase 1 — Video Ingestion (Transcription)

Once your environment is ready, the first step is extracting text from YouTube videos. You have three strategies — pick based on your needs.

**Quick start (Strategy B, recommended):**
1. Activate venv → `source .venv/bin/activate`
2. Transcribe → `python backend/core/ingestion_audio.py --url "VIDEO_URL" --lang es`
3. Output → `data/raw/whisper/{video_id}.json`
4. Repeat for each video.

### Strategy comparison

| | A: Captions | B: Whisper local | B GPU: Colab |
|---|---|---|---|
| **Quality** | 2/5 (no punctuation) | 4/5 (full sentences) | 5/5 (large-v3) |
| **Speed** | Instant | ~2 min (4-min video) | ~15 sec (4-min video) |
| **Cost** | $0 | $0 | $0 (Colab free tier) |
| **Best for** | Quick tests, fallback | ≤ 5 min videos | > 5 min videos, batches |
| **Hardware** | None | Intel i9 / 32GB RAM | Google Colab GPU |

---

### Strategy A: YouTube Auto-Captions

Best for quick tests. Instant, free, but captions lack punctuation and may have garbled segments.

```bash
# macOS / Linux
source .venv/bin/activate                       # or: conda activate migrant-archive
python backend/core/ingestion_caption.py --url "VIDEO_URL" --lang es

# Windows (PowerShell) — same commands, adjust venv path
.venv\Scripts\activate
python backend/core/ingestion_caption.py --url "VIDEO_URL" --lang es
```

Output: `data/raw/captions/{video_id}.json`

> **Warning:** Captions on Spanish/Catalan code-switching can be broken. For production use, prefer Strategy B.

---

### Strategy B: faster-whisper (Local CPU)

> **Source:** [`backend/core/ingestion_audio.py`](backend/core/ingestion_audio.py) · shared contract: [`backend/core/ingestion.py`](backend/core/ingestion.py)
>
> **Why faster-whisper and not WhisperX?** WhisperX adds speaker diarisation and word-level
> alignment, but is incompatible with Google Colab as of mid-2026 (numpy dependency conflicts,
> CUDA version mismatch). faster-whisper uses the same Whisper large-v3 model with zero
> dependency issues. FILMIG content is mostly single-speaker, so diarisation is not critical.
> Full decision record: [`notes/faster-whisper-migration.md`](notes/faster-whisper-migration.md).

Best quality at zero cost. Runs entirely on your machine — no API, no uploads. Recommended default for ≤ 5 minute videos.

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

### Strategy B GPU: Google Colab (videos > 5 min)

> **Source:** [`backend/core/ingestion_colab.py`](backend/core/ingestion_colab.py)

Same logic as Strategy B, but runs on Colab's free GPU. ~10x faster for long videos.

```bash
# Upload ingestion_colab.py to Colab, then run:
python backend/core/ingestion_colab.py --url "VIDEO_URL" --lang es
```

Defaults: `large-v3` model, `--device cuda`. Saves to Google Drive (`migrant-archive/output/`).

---

## Phase 2 — Embeddings + Vector Store

Once you have transcriptions (Phase 1), this phase converts text into searchable vector embeddings and stores them in ChromaDB.

**Quick start (Gemini, recommended):**
1. Make sure `.json` files exist in `data/raw/whisper/`
2. Build index → `python backend/scripts/rag_test.py --rebuild`
3. Query → `python backend/scripts/rag_test.py`
4. If you add more videos later → see [Embeddings Workflow](#embeddings-workflow) below.

### Chunking strategy

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

### Embedding provider comparison

> **Sources:** [`backend/core/embedding.py`](backend/core/embedding.py) (contract) · [`backend/core/embedding_gemini.py`](backend/core/embedding_gemini.py) · [`backend/core/embedding_bge_m3.py`](backend/core/embedding_bge_m3.py)

| | Gemini (cloud) | BGE-M3 (local) |
|---|---|---|
| **Quality** | #1 MTEB Multilingual (71.5%) | Excellent Spanish |
| **Dimension** | 3072 (Matryoshka-capable) | 1024 |
| **Cost** | Free tier (~$0 for project) | $0 |
| **Speed** | ~1s (API call) | ~2-5s (CPU inference) |
| **Privacy** | Text sent to Google API | Everything stays on your machine |
| **Environment** | UV or Conda | Conda (requires PyTorch) |
| **Best for** | Production, demos, quick setup | Offline, sensitive data, interview portfolio |

---

### Option A: Gemini API Embeddings (default)

> **Source:** [`backend/core/embedding_gemini.py`](backend/core/embedding_gemini.py)

Uses `gemini-embedding-001` — Google's #1 multilingual model. Free tier covers the entire project.

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

### Option B: BGE-M3 Local Embeddings

> **Source:** [`backend/core/embedding_bge_m3.py`](backend/core/embedding_bge_m3.py)

Runs entirely on your CPU. No API keys, no internet (after model download). Same interface as Gemini — swap one line to switch.

**Requires:** Conda environment (PyTorch ≥ 2.4).

```python
from backend.core.embedding_bge_m3 import BGEM3EmbeddingProvider

# Same code as Gemini — just swap the provider
provider = BGEM3EmbeddingProvider()  # loads BAAI/bge-m3 on first call
processor = Processor(provider)
# ... rest is identical
```

The model downloads on first use (~2.2 GB, cached locally).

---

### Process all videos in batch

```python
from pathlib import Path

provider = GeminiEmbeddingProvider()  # or BGEM3EmbeddingProvider()
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

### Reset the vector store

> **Source:** [`backend/core/vector_store.py`](backend/core/vector_store.py)

```bash
rm -rf data/chroma/
```

ChromaDB data is gitignored. Deleting the directory starts fresh.

---

### Embeddings Workflow

> **Scripts:** [`backend/scripts/rag_test.py`](backend/scripts/rag_test.py) · [`backend/scripts/extract_sample.py`](backend/scripts/extract_sample.py) · core: [`backend/core/vector_store.py`](backend/core/vector_store.py)

This section covers the three situations you'll encounter when working with embeddings: first-time creation, adding new videos, and reading stored data.

#### Scenario 1 — First-Time Creation (Initial Embeddings)

**When:** you've transcribed videos in Phase 1 and ChromaDB is empty. This is the first time you're building the vector index.

**Simplest path — use the rebuild script:**

```bash
source .venv/bin/activate                          # or: conda activate migrant-archive

# This chunks, embeds, and stores ALL whisper JSON files
python backend/scripts/rag_test.py --rebuild
```

**What happens under the hood:**

1. `rag_test.py` finds every `.json` in `data/raw/whisper/`
2. For each video: `VideoData.load_json()` → `Processor.chunk()` → `Processor.embed_chunks()` → `VectorStore.add()`
3. ChromaDB is created at `data/chroma/` with collection `migrant_archive`

**Expected output:**

```
Initializing Gemini embedding provider ...
--rebuild flag set: re-indexing all videos ...

Indexing: APgxfNssxGQ.json  ... 12 chunks
Indexing: XYZ123.json       ... 8 chunks

Indexed 20 chunks from 2 video(s) into ChromaDB.

Collection size: 20 chunks
Top-K: 3
──────────────────────────────────────────────────────────
Paste or type a question. Type 'quit' to exit.
```

**Alternative — programmatic (full control):**

If you need more control than the script offers (custom chunk size, BGE-M3 provider, captions instead of whisper):

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

#### Scenario 2 — Updating Embeddings (Adding New Videos)

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
python backend/scripts/rag_test.py --rebuild
```

This is the same command as Scenario 1. `--rebuild` calls `delete_collection()` internally, wiping everything before re-indexing all JSON files found in `data/raw/whisper/`.

> **Tip:** With Gemini API, re-embedding is fast and cheap (~$0 for the entire project). Unless you have 100+ videos, rebuilding is usually the pragmatic choice.

##### Option C: Start completely fresh

```bash
rm -rf data/chroma/
python backend/scripts/rag_test.py --rebuild
```

Manually deleting the directory before rebuilding guarantees a clean slate — useful if you suspect ChromaDB corruption or switched between embedding providers (Gemini 3072d vs BGE-M3 1024d are incompatible in the same collection).

---

#### Scenario 3 — Reading / Querying Embeddings

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
| `--rebuild` | off | Force re-index before starting the prompt |
| `--top-k 5` | 3 | Number of chunks to retrieve per query |

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

---

## Checkpoint Demo — Sample Extraction (completed)

> **Source:** [`backend/scripts/extract_sample.py`](backend/scripts/extract_sample.py)

Prove the data pipeline works by extracting the first 5,000 characters from both storage backends.

```bash
# Show first 5K chars from both ChromaDB and JSON sources
python backend/scripts/extract_sample.py

# ChromaDB only
python backend/scripts/extract_sample.py --source chroma

# JSON files only
python backend/scripts/extract_sample.py --source json

# Custom character limit
python backend/scripts/extract_sample.py --chars 2000

# Use captions directory instead of whisper
python backend/scripts/extract_sample.py --source json --raw-dir data/raw/captions
```

**What this proves for the checkpoint:**
- Data is correctly stored in both ChromaDB and raw JSON files
- Video content is readable, searchable, and has the expected structure
- Spanish special characters (¿, ¡, ñ, ó) survive the full pipeline roundtrip
- ChromaDB chunks preserve title metadata and sequential ordering

---

## Architecture Decisions

### Native Tool Calling over ReAct Text Parsing

Gemini 2.5 Flash supports native function calling via structured tool messages.
Using `create_tool_calling_agent` eliminates the text-parsing failures that
plagued the previous ReAct implementation (`Invalid Format: Missing 'Action:'`).

→ [LangChain + Gemini Function Calling Guide](https://www.philschmid.de/gemini-function-calling)

### Message History over ConversationBufferMemory

`ConversationBufferMemory` was deprecated in LangChain 0.3.1. Migrated to
`RunnableWithMessageHistory` + `InMemoryChatMessageHistory` with per-session
isolation. Sessions are cleared on CLI exit and via `DELETE /api/session/{id}`.

```python
from langchain_core.chat_history import InMemoryChatMessageHistory
from langchain_core.runnables.history import RunnableWithMessageHistory

store = {}
def get_session_history(session_id: str):
    if session_id not in store:
        store[session_id] = InMemoryChatMessageHistory()
    return store[session_id]

chain = RunnableWithMessageHistory(agent, get_session_history, ...)
```

→ [LangChain Memory Migration Guide](https://python.langchain.com/docs/versions/migrating_memory/conversation_buffer_memory/)
→ [Conversational Memory in LangChain (Aurelio AI)](https://www.aurelio.ai/learn/langchain-conversational-memory)

---

## S06 — Conversational Agent with Memory (Week 2)

> Sources: [`backend/agents/agent.py`](backend/agents/agent.py) · [`backend/agents/tools.py`](backend/agents/tools.py) · [`backend/scripts/agent_cli.py`](backend/scripts/agent_cli.py)

The **Cero** agent answers questions in Spanish using transcripts stored in ChromaDB and remembers conversation context via session-based message history.

### Agent architecture

```
User → agent_cli.py → Tool Calling Agent (LangChain)
                         ├── search_transcripts (ChromaDB)
                         ├── Gemini 2.5 Flash (LLM) via native function calling
                         └── RunnableWithMessageHistory + InMemoryChatMessageHistory
```

The agent uses `create_tool_calling_agent` with Gemini's native function calling — no text parsing, no `Thought:/Action:` format. Memory is per-session: each `session_id` gets an isolated `InMemoryChatMessageHistory`.

Session history is cleared when:
- **CLI**: user types `quit`/`salir` or presses Ctrl+C (via `try/finally`)
- **API**: `DELETE /api/session/{session_id}` endpoint

### How to use

```bash
source .venv/bin/activate
python backend/scripts/agent_cli.py
```

The CLI loads `GEMINI_API_KEY` from `.env`, initializes the agent with a fresh `cli-session`, and opens an interactive prompt:

```
Bienvenido a Cero, tu asistente sobre testimonios migratorios.
Escribe 'quit' o 'salir' para salir.
────────────────────────────────────────────────────────────
Pregunta> ¿Qué dice el video sobre migración?
[agent answer with sources]
Pregunta> ¿y en qué minuto lo mencionaron?
[answer using memory from previous context]
```

### Query with memory (vs plain RAG)

Unlike `rag_test.py` (which only searches ChromaDB without context), the agent keeps the full conversation in `InMemoryChatMessageHistory` keyed by `session_id`. This enables follow-up questions like "and what else did they say?" without repeating the topic.

### Memory

Uses `RunnableWithMessageHistory` wrapping an `AgentExecutor` with `InMemoryChatMessageHistory` per session. The deprecated `ConversationBufferMemory` was replaced in June 2026. See [Architecture Decisions](#architecture-decisions) above.

> **Pick your LLM:** the agent defaults to `gemini-2.5-flash`. Change it via the `GEMINI_MODEL` variable in `.env`.

### Tests

```bash
uv run python -m pytest tests/test_agent.py -v
```

16 tests: tool, agent, memory isolation, session cleanup, CLI, and E2E (requires GEMINI_API_KEY).

---

## S07 — API + Chat Widget (Week 3)

> Sources: [`backend/api/main.py`](backend/api/main.py) · [`backend/api/routes/chat.py`](backend/api/routes/chat.py) · [`frontend/src/chat-widget.ts`](frontend/src/chat-widget.ts)

The **Cero** agent is exposed as a REST API and embeddable chat widget.

### Architecture

```
Browser widget ──POST /api/ask──► FastAPI ──► Agent (Cero) ──► ChromaDB
                                     │
                                  Gemini LLM
```

### Start the API

```bash
uv run uvicorn backend.api.main:app --reload --port 8000
```

`POST /api/ask` accepts `{"question": "...", "session_id": "..."}` and returns `{"answer": "...", "sources": [...]}`.

### Start the chat widget

```bash
cd frontend && pnpm install && pnpm dev
```

Open `http://localhost:5173`. A blue bubble appears bottom-right. Click to open the chat panel.

### API details

| Endpoint | Method | Request | Response |
|----------|--------|---------|----------|
| `/api/ask` | POST | `{"question": "string", "session_id": "string"}` | `{"answer": "string", "sources": [...]}` |
| `/api/session/{session_id}` | DELETE | — | `{"session_id": "string", "cleared": bool}` |

Each source contains `video_id`, `title`, `start_time`, `end_time`, and `text`.

`session_id` defaults to `"default"` if omitted. The DELETE endpoint clears conversation history for a session, freeing memory.

Errors: `422` for empty question, `503` when `GEMINI_API_KEY` is not configured.

### Tests

```bash
uv run python -m pytest tests/test_api.py tests/test_frontend.py -v
```

25 tests: models, routes, session lifecycle, CORS, error handling, source parsing, frontend build, and widget structure.

### LangSmith Tracing

> Sources: `requirements.txt` (langsmith) · `.env.example` · [`tests/conftest.py`](tests/conftest.py) · [`tests/test_langsmith.py`](tests/test_langsmith.py)

LangSmith provides full observability into every agent run: LLM calls, tool executions (`search_transcripts`), latency, token usage, and cost. Tracing activates **automatically** when `LANGSMITH_TRACING=true` is set — zero changes to `agent.py` were needed.

#### How it works

```
Agent (Cero) ──► AgentExecutor ──► LangSmith (auto-trace)
                     │
         ┌───────────┼───────────┐
         ▼           ▼           ▼
      LLM call   search_transcripts   LLM response
         │           │               │
         └───────────┴───────────────┘
                     │
              Trace: 3 spans, latency, tokens, cost
```

Each trace shows the full chain: `ChatGoogleGenerativeAI` → `search_transcripts` → `ChatGoogleGenerativeAI`, plus session history load/insert and response normalization.

#### Setup

Add your LangSmith API key to `.env`:

```bash
LANGSMITH_TRACING=true
LANGSMITH_API_KEY=lsv2_pt...
LANGSMITH_PROJECT=migrant-archive
LANGSMITH_ENDPOINT=https://api.smith.langchain.com
```

That's it. Run the agent or API normally — traces appear at [smith.langchain.com](https://smith.langchain.com) in the `migrant-archive` project.

#### Test safety

A session-scoped fixture in `tests/conftest.py` forces `LANGSMITH_TRACING=false` during pytest runs so fake LLM traces never pollute the LangSmith project:

```python
@pytest.fixture(autouse=True, scope="session")
def _disable_langsmith_tracing():
    os.environ["LANGSMITH_TRACING"] = "false"
    yield
    os.environ.pop("LANGSMITH_TRACING", None)
```

3 dedicated tests in `tests/test_langsmith.py` verify the fixture works and that the agent produces no traces when tracing is disabled.

#### Free tier

LangSmith's free tier covers **5,000 traces/month** — far more than a solo project needs. The entire Migrant Archive project fits comfortably within the free quota.

---

## Tests

> Test files: [`tests/`](tests/) — [`test_embedding.py`](tests/test_embedding.py) · [`test_embedding_gemini.py`](tests/test_embedding_gemini.py) · [`test_embedding_bge_m3.py`](tests/test_embedding_bge_m3.py) · [`test_processor.py`](tests/test_processor.py) · [`test_vector_store.py`](tests/test_vector_store.py) · [`test_pipeline_e2e.py`](tests/test_pipeline_e2e.py) · [`test_extract_sample.py`](tests/test_extract_sample.py) · [`test_ingestion.py`](tests/test_ingestion.py) · [`test_faster_whisper_audio.py`](tests/test_faster_whisper_audio.py) · [`test_faster_whisper_colab.py`](tests/test_faster_whisper_colab.py) · [`test_agent.py`](tests/test_agent.py) · [`test_api.py`](tests/test_api.py) · [`test_frontend.py`](tests/test_frontend.py) · [`test_langsmith.py`](tests/test_langsmith.py)

```bash
# UV environment
source .venv/bin/activate
python -m pytest tests/ -v

# Conda environment
conda activate migrant-archive
python -m pytest tests/ -v
```

**Results:** 125 tests collected. Conditional skips apply when `GEMINI_API_KEY` is not set or a GPU is unavailable; the E2E layer is skipped entirely without an API key.

| Layer | Tests | Files | What it proves |
|-------|-------|-------|----------------|
| Unit | 40 | `test_embedding.py`, `test_processor.py`, `test_vector_store.py`, `test_ingestion.py` | Contract enforcement, chunking logic, CRUD operations, timestamp helpers |
| Integration | 55 | `test_embedding_gemini.py`, `test_embedding_bge_m3.py`, `test_extract_sample.py`, `test_faster_whisper_audio.py`, `test_faster_whisper_colab.py`, `test_api.py` | Real providers, extraction from real JSON, audio/colab strategies, API routes |
| Agent | 16 | `test_agent.py` | Tool-calling agent, search_transcripts tool, session memory, cleanup, CLI |
| Frontend | 9 | `test_frontend.py` | Vite build, widget class structure, DOM bootstrap, styling |
| Observability | 3 | `test_langsmith.py` | Tracing guard fixture, env-var isolation, integration test with fake key |
| E2E | 2 | `test_pipeline_e2e.py` | Full pipeline with Gemini API (needs key) |
