# Session 1 — Ingestion Pipeline

**Date**: 10 June 2026
**Goal**: Decide how to extract transcript + metadata from YouTube videos into structured `VideoData`.

## Decision Record

### Approaches Evaluated

| # | Strategy | Library / Model | Cost | Quality | Speed |
|---|----------|----------------|------|---------|-------|
| A | YouTube auto-captions | [`youtube-transcript-api`](https://pypi.org/project/youtube-transcript-api/) | $0 | ⭐⭐ | Instant |
| B | Audio + local Whisper | [`faster-whisper`](https://github.com/SYSTRAN/faster-whisper) + `small` model | $0 | ⭐⭐⭐⭐ | ~2 min (CPU) |
| C | Audio + OpenAI Whisper API | OpenAI Whisper API | ~$0.006/min | ⭐⭐⭐⭐⭐ | ~30s |

### Chosen: **B (local faster-whisper)** with A as fallback

Why: best quality at $0 cost. Runs on Intel i9 + 32GB RAM using CPU inference (`int8` quantisation).

### Comparative Analysis (real test — same video: `APgxfNssxGQ`)

| Metric | Strategy A (Captions) | Strategy B (Whisper) |
|--------|----------------------|----------------------|
| Segments | 76 (micro-cuts) | 34 (full sentences) |
| Characters | 2,560 | 3,126 (+22%) |
| Punctuation | ❌ None | ✅ Periods, commas, ¿? |
| Capitalisation | ❌ None | ✅ Proper nouns, sentence start |
| Garbled segments | ❌ 12 segments illegible | ✅ All coherent |
| Sound labels | `[Música]` noise | Clean text |
| Catalan/Spanish mix | Broken on code-switching | Mostly accurate |

**Verdict**: Whisper output is directly usable for RAG. Captions required heavy post-processing.

---

## Implementation

### Architecture decision: shared core + strategy files

```
core/ingestion.py           ← VideoData dataclass + shared helpers
core/ingestion_caption.py   ← Strategy A: youtube-transcript-api
core/ingestion_audio.py     ← Strategy B: yt-dlp + faster-whisper
```

Both strategies produce identical `VideoData` JSON → `processor.py` doesn't care about the source.

### Discoveries

- **`youtube-transcript-api` v1.2.4** changed API: class method `get_transcript()` → instance method `api.fetch()`
- **`faster-whisper`** on CPU with `int8` quantisation works well on i9/32GB for `small` model (~500MB, ~2 min for 4-min video)
- **yt-dlp filename encoding**: use `%(id)s.%(ext)s` template, not `%(title)s`, to avoid special character mismatches between yt-dlp output and expected path
- **yt-dlp JS challenge warnings** are non-fatal for metadata extraction; they only affect video format availability

### Toolchain

| Tool | Version | Role |
|------|---------|------|
| `yt-dlp` | latest | Metadata + audio download |
| `youtube-transcript-api` | 1.2.4 | YouTube auto-captions (fallback) |
| `faster-whisper` | latest | Local transcription (CTranslate2 backend) |
| `ffmpeg` | 8.1.1 | Audio extraction from video streams |

### Output directory convention

```
data/
├── audio/{video_id}.mp3        ← raw audio (reusable, cache)
├── raw/captions/{video_id}.json ← caption strategy output
└── raw/whisper/{video_id}.json  ← whisper strategy output
```

---

## Code Quality Refactor

After the initial implementation, a review pass fixed:

| Issue | Fix |
|-------|-----|
| Dead code: `_slugify()` | Removed |
| Fragile relative imports | `sys.path.insert(0, Path(__file__).parent)` |
| Duplicated `VideoData` construction | Extracted `_build_videodata()` factory |
| WhisperModel loaded per video call | `_get_model()` singleton with cache |
| `save_json` ambiguous default | Default removed, requires explicit `output_dir` |
| Hardcoded inference settings | Module-level constants `WHISPER_BEAM_SIZE` |

### Device auto-detection

Added `--device` flag with three modes:

```
auto (default) → probes ctranslate2 for CUDA → falls back to CPU
cuda           → forces NVIDIA GPU (float16)
cpu            → forces CPU (int8 quantised)
```

Implementation: `_detect_device()` uses `ctranslate2.get_cuda_device_count()`.  
Compute type auto-selects: `float16` for CUDA, `int8` for CPU.  
Model cache keyed by `(model_size, device)` so switching doesn't reload unnecessarily.

### Model storage location

Whisper models download to `models/whisper/` (gitignored) via `download_root` parameter.
Predictable, visible, and project-local — no hidden `~/.cache/` surprises.

### Audio download cache

`_download_audio()` checks if the mp3 already exists before re-downloading.
Cache hit: ~3s (metadata fetch only). Cache miss: ~20s (download + FFmpeg conversion).
Saves ~15 minutes on a 50-video channel.

### Colab GPU strategy

For videos >5 minutes, `ingestion_colab.py` is a thin wrapper over `ingestion_audio.py`
that overrides three defaults: `large-v3`, `--device cuda`, and Google Drive output paths.
No code duplication — imports `extract_single_video` directly.
10x faster than local CPU for long videos.

---

## Recap — What We Built

Four files, two strategies, one contract:

| File | Lines | Role |
|------|-------|------|
| `ingestion.py` | 134 | `VideoData` dataclass, `_fetch_metadata`, `_build_videodata`, `_download_audio` (cached) |
| `ingestion_caption.py` | 83 | Strategy A: `youtube-transcript-api` → free, fast, lower quality (fallback) |
| `ingestion_audio.py` | 211 | Strategy B: `faster-whisper` local CPU → free, high quality, auto-detect GPU |
| `ingestion_colab.py` | 91 | Strategy B GPU wrapper: same logic, `large-v3` + `--device cuda` defaults |

### Key decisions & pivots
- **Started with youtube-transcript-api** → discovered captions have no punctuation, garbled segments → **pivoted to faster-whisper**
- **Started with openai-whisper** → discovered faster-whisper is 4x faster via CTranslate2 → **switched**
- **Whisper > captions**: 22% more text, proper punctuation, no garbled segments (proven with same test video)
- **Shared core**: `VideoData` contract means `processor.py` won't care about strategy
- **Local > API**: $0 cost, privacy, works offline
- **Device auto-detect**: works on Intel Mac, Apple Silicon, and NVIDIA without config
- **Model cache**: `(model_size, device)` keyed, stored in `models/whisper/` (visible, not hidden in `~/.cache/`)
- **Audio cache**: skips re-download automatically (~3s hit vs ~20s miss)
- **≤5 min vs >5 min split**: local CPU for short videos, Colab GPU for long ones. Same codebase, just different defaults.

### Files changed this session
```
migrant-archive/
├── .gitignore                                     ← new (models, venv, audio, cache)
├── README.md                                      ← setup, flags, lang support, ≤5 vs >5 guide
├── requirements.txt                               ← youtube-transcript-api, yt-dlp, faster-whisper
├── notes/session-1-ingestion.md                   ← new: decision record, pivots, recap
└── backend/core/
    ├── ingestion.py                               ← VideoData + shared helpers
    ├── ingestion_caption.py                       ← Strategy A (fallback)
    ├── ingestion_audio.py                         ← Strategy B local CPU (≤5 min)
    └── ingestion_colab.py                         ← Strategy B GPU wrapper (>5 min)
```

---

## Next Session

- `processor.py`: chunking + OpenAI `text-embedding-3-small`
- `vector_store.py`: ChromaDB persistence
