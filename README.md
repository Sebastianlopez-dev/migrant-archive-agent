# Migrant Archive — Narratives That Resist

**Agent name: Cero**

Multimodal RAG chatbot that answers questions about YouTube video content.
Built on the FILMIG / Plataforma Cero channel (Spanish).

---

## Development Timeline

| Week | Steps | Focus |
|------|-------|-------|
| 1 | 1–2 | Ingestion + Processing — dual transcription, chunking, embeddings, ChromaDB |
| 2 | 3–4 | Agents + Testing — LangChain agent with tools/memory, test suite (unit/integration/E2E) |
| 3 | 5–6 | Evaluation + API — LangSmith, FastAPI REST wrapper |
| 4 | 7–8 | Frontend + Deploy — Web Speech API voice input, presentation |

> **Week 1 checkpoint:** Live vector DB Q&A demo — query ChromaDB directly with pre-verified questions. See `backend/scripts/rag_test.py` and `notes/rag_test_questions.md`.

---

## Project Structure

```
migrant-archive/
├── .env.example                ← Template for API keys (copy to .env)
├── requirements.txt            ← Python dependencies (uv/pip path)
│
├── backend/
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
│       └── rag_test.py           ← Standalone RAG pipeline test script
│
├── tests/
│   ├── test_embedding.py       ← Contract tests (FakeEmbeddingProvider)
│   ├── test_embedding_gemini.py ← Gemini provider tests
│   ├── test_embedding_bge_m3.py ← BGE-M3 provider tests
│   ├── test_processor.py       ← Chunking + orchestration tests
│   ├── test_vector_store.py    ← ChromaDB CRUD + relevance tests
│   └── test_pipeline_e2e.py    ← Full pipeline with real video
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
└── notes/                      ← Decision records + research
    ├── session-1-ingestion.md
    ├── session-2-embeddings-research.md
    ├── session-2-chunking-and-testing.md
    └── rag_test_questions.md   ← Pre-verified questions for vector DB demo
```

---

## 0. Choose Your Environment

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

## Phase 1 — Video Ingestion (Transcription)

Once your environment is ready, the first step is extracting text from YouTube videos. You have three strategies — pick based on your needs.

### Strategy comparison

| | A: Captions | B: Whisper local | B GPU: Colab |
|---|---|---|---|
| **Quality** | ⭐⭐ (no punctuation) | ⭐⭐⭐⭐ (full sentences) | ⭐⭐⭐⭐⭐ (large-v3) |
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

> ⚠️ Captions on Spanish/Catalan code-switching can be broken. For production use, prefer Strategy B.

---

### Strategy B: faster-whisper (Local CPU)

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

Same logic as Strategy B, but runs on Colab's free GPU. ~10x faster for long videos.

```bash
# Upload ingestion_colab.py to Colab, then run:
python backend/core/ingestion_colab.py --url "VIDEO_URL" --lang es
```

Defaults: `large-v3` model, `--device cuda`. Saves to Google Drive (`migrant-archive/output/`).

---

## Phase 2 — Embeddings + Vector Store

Once you have transcriptions (Phase 1), this phase converts text into searchable vector embeddings and stores them in ChromaDB.

### Chunking strategy

Before embedding, text is split into overlapping chunks. These values were chosen specifically for Spanish conversational content (interviews, debates).

| Parameter | Value | Why |
|-----------|-------|-----|
| **Chunk size** | 1,000 tokens (~750 words) | Captures ~4-5 min of speech — one complete idea |
| **Overlap** | 200 tokens (20%) | Ensures no idea is cut at chunk boundaries |
| **Token counter** | `len(text) // 4` | Simple estimator — zero dependencies, accurate enough |
| **1-hour video** | ~12 chunks | vs ~25 with smaller chunks (less API cost, less noise) |

> **Why not smaller chunks?** Spanish sentences are longer than English. A 380-word chunk (512 tokens) cuts ideas in half. 750 words captures a full answer, an anecdote, or a complete argument. The 20% overlap bridges ideas that cross chunk boundaries. This scales from 2-minute clips to 2-hour documentaries without changes.

---

### Embedding provider comparison

| | Gemini (cloud) | BGE-M3 (local) |
|---|---|---|
| **Quality** | 🥇 #1 MTEB Multilingual (71.5%) | ⭐⭐⭐⭐ Excellent Spanish |
| **Dimension** | 3072 (Matryoshka-capable) | 1024 |
| **Cost** | Free tier (~$0 for project) | $0 |
| **Speed** | ~1s (API call) | ~2-5s (CPU inference) |
| **Privacy** | Text sent to Google API | Everything stays on your machine |
| **Environment** | UV or Conda | Conda (requires PyTorch) |
| **Best for** | Production, demos, quick setup | Offline, sensitive data, interview portfolio |

---

### Option A: Gemini API Embeddings (default)

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
    print(f"✅ {video.title} — {len(chunks)} chunks stored")
```

---

### Reset the vector store

```bash
rm -rf data/chroma/
```

ChromaDB data is gitignored. Deleting the directory starts fresh.

---

## Tests

```bash
# UV environment
source .venv/bin/activate
python -m pytest tests/ -v

# Conda environment
conda activate migrant-archive
python -m pytest tests/ -v
```

**Results:** 29/29 pass (UV), 31/31 pass (Conda).

| Layer | Tests | What it proves |
|-------|-------|----------------|
| Unit | 18 | Contract enforcement, chunking logic, CRUD operations |
| Integration | 8 | Real BGE-M3 + ChromaDB together |
| E2E | 1 | Full pipeline with Gemini API (needs key) |
