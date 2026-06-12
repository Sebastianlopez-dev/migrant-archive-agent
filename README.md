# Migrant Archive — Narratives That Resist

**Agent name: Cero**

Multimodal RAG chatbot that answers questions about YouTube video content.
Built on the FILMIG / Plataforma Cero channel.

## System Requirements

| Tool | Why | Install |
|------|-----|---------|
| **[uv](https://docs.astral.sh/uv/)** | Fast Python package & environment manager | `curl -LsSf https://astral.sh/uv/install.sh \| sh` |
| **Python 3.12+** | Runtime | `uv python install 3.12` |
| **FFmpeg** | Audio extraction for Whisper ingestion | `brew install ffmpeg` (macOS) |

## Setup

```bash
uv venv --python 3.12
source .venv/bin/activate
uv pip install -r requirements.txt
```

Dependencies (see `requirements.txt`):
- `youtube-transcript-api` — YouTube auto-captions (Strategy A)
- `yt-dlp` — metadata + audio download
- `faster-whisper` — local Whisper transcription (Strategy B)

## Project Structure

```
backend/core/
├── ingestion.py              ← VideoData model + shared helpers
├── ingestion_caption.py      ← Strategy A: YouTube auto-captions
├── ingestion_audio.py        ← Strategy B: yt-dlp → faster-whisper (local CPU)
├── ingestion_colab.py        ← Strategy B (GPU): same logic, Colab-optimised defaults
├── embedding.py              ← EmbeddingProvider (abstract contract)
├── embedding_gemini.py       ← Gemini API implementation (default, 3072-dim)
├── embedding_bge_m3.py       ← BGE-M3 local implementation (1024-dim, conda env)
├── processor.py              ← Chunking (1000tk/200ov) + embedding orchestration
└── vector_store.py           ← ChromaDB persistence (add, search, delete)

tests/
├── test_embedding.py         ← Unit: contract + FakeEmbeddingProvider
├── test_embedding_gemini.py  ← Unit: Gemini provider
├── test_embedding_bge_m3.py  ← Unit: BGE-M3 provider (conda env)
├── test_processor.py         ← Unit: chunking + orchestration
├── test_vector_store.py      ← Integration: ChromaDB CRUD + Gemini relevance
└── test_pipeline_e2e.py      ← E2E: full pipeline with real video

data/
├── audio/{video_id}.mp3      ← downloaded audio cache (auto-skip re-download)
├── chroma/                   ← ChromaDB persistent storage (gitignored)
├── raw/captions/{id}.json    ← caption strategy output
└── raw/whisper/{id}.json     ← whisper strategy output

models/
└── whisper/                  ← faster-whisper model files (auto-downloaded, gitignored)
```

## Ingestion

Two strategies, same `VideoData` JSON output. **Which one to use:**

| Video length | Use | Command |
|-------------|-----|---------|
| ≤ 5 min | Local CPU | `ingestion_audio.py --model small` |
| > 5 min | Colab GPU | `ingestion_colab.py --model large-v3` |

### Language support

faster-whisper supports 99 languages via the `--lang` flag. Default: `es`.

| Code | Language | Relevance |
|------|----------|-----------|
| `es` | Spanish | Default — content is primarily Spanish |
| `en` | English | Fallback for English videos |
| `ca` | Catalan | Useful for Catalan/Spanish code-switching |

For auto-detection (no `--lang` flag), pass `--lang ""` (faster-whisper auto-detects).

```bash
python backend/core/ingestion_audio.py --url "VIDEO_URL" --lang es
```

Available flags:
```
--url URL         YouTube video URL (required)
--lang LANG       Language code: es, en, ... (default: es)
--model MODEL     faster-whisper size: tiny, base, small, medium, large-v3 (default: small)
--device DEVICE   auto (detect), cpu (Intel/Apple Silicon), cuda (NVIDIA GPU) — default: auto
--output-dir DIR  Where to save the JSON (default: data/raw/whisper)
--audio-dir DIR   Where to save the mp3 (default: data/audio)
```

Audio is cached at `data/audio/{video_id}.mp3` — re-running skips download automatically.

### Strategy B (GPU) — videos > 5 min / batch processing

```bash
python backend/core/ingestion_colab.py --url "VIDEO_URL" --lang es
```

Same logic, defaults to `large-v3 --device cuda`. Saves to `migrant-archive/output/` and `migrant-archive/audio/` in Google Drive. 10x faster than local CPU.

---

## Phase 2 — Embedding + Vector Store

Generates embeddings from transcribed videos and stores them in ChromaDB for semantic search.

### Dependencies

**Option A — uv/pip (Gemini only, no BGE-M3):**

```bash
source .venv/bin/activate
uv pip install -r requirements.txt
```

**Option B — conda (Gemini + BGE-M3 local):**

```bash
conda create -n migrant-archive python=3.12 -y
conda activate migrant-archive
conda install pytorch transformers -c defaults -y
pip install sentence-transformers chromadb google-genai pytest python-dotenv yt-dlp youtube-transcript-api faster-whisper
```

> BGE-M3 requires PyTorch ≥ 2.4 with correct NumPy linkage. Conda handles this automatically. uv/pip does not — use conda for the full local embedding stack.

### Environment

Copy `.env.example` to `.env` and add your Gemini API key:

```bash
cp .env.example .env
# Edit .env → set GEMINI_API_KEY=your-key
```

Get your key at: [aistudio.google.com/apikey](https://aistudio.google.com/apikey)

### Architecture

```
core/embedding.py            ← EmbeddingProvider (abstract contract)
core/embedding_gemini.py     ← Gemini API (cloud, default, 3072-dim)
core/embedding_bge_m3.py     ← BGE-M3 local (CPU, requires conda env)
core/processor.py            ← Chunking (1000tk/200 overlap) + embedding
core/vector_store.py         ← ChromaDB persistence
```

The embedding layer uses **Strategy + Dependency Inversion**: `processor.py` receives an `EmbeddingProvider` via constructor and doesn't know which implementation is active. Switching from Gemini to BGE-M3 is one config change.

### Embedding provider

| Provider | Quality | Cost | Requires |
|----------|---------|------|----------|
| **Gemini** (default) | #1 MTEB Multilingual | Free tier (~$0 for project) | `GEMINI_API_KEY` |
| BGE-M3 (local) | Excellent Spanish | $0 | conda env (torch ≥ 2.4) |

### Process a single video (Python API)

```bash
source .venv/bin/activate
```

```python
from backend.core.ingestion import VideoData
from backend.core.embedding_gemini import GeminiEmbeddingProvider
from backend.core.processor import Processor
from backend.core.vector_store import VectorStore

# Load a previously transcribed video
video = VideoData.load_json("data/raw/whisper/VIDEO_ID.json")

# Create provider and processor
provider = GeminiEmbeddingProvider()  # reads GEMINI_API_KEY from env
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
    print(r["document"][:200], "...")
```

> 📦 Batch processing script coming in Phase 3 (`scripts/ingest_channel.py`).

### Process all cached videos (Python loop)

```python
from pathlib import Path
from backend.core.ingestion import VideoData
from backend.core.embedding_gemini import GeminiEmbeddingProvider
from backend.core.processor import Processor
from backend.core.vector_store import VectorStore

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
    print(f"✅ {video.title} — {len(chunks)} chunks stored")
```

### Run tests

```bash
source .venv/bin/activate && python -m pytest tests/ -v
```

| Layer | Tests | Requires |
|-------|-------|----------|
| Unit | Contract + chunking + CRUD | Nothing |
| Integration | Gemini relevance search | `GEMINI_API_KEY` |
| E2E | Full pipeline with real video | `GEMINI_API_KEY` + cached VideoData |

### Vector store location

ChromaDB persists to `data/chroma/` (gitignored). Delete the directory to reset:

```bash
rm -rf data/chroma/
```
