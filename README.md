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
└── ingestion_colab.py        ← Strategy B (GPU): same logic, Colab-optimised defaults

data/
├── audio/{video_id}.mp3      ← downloaded audio cache (auto-skip re-download)
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
