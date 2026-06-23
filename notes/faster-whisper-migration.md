# Transcription Model Decision: faster-whisper over WhisperX

**Status**: final — 23 June 2026.

## TL;DR

We use **faster-whisper** (large-v3) for all transcription — local CPU and Colab GPU.
We evaluated WhisperX for speaker diarisation but abandoned it after a 10-day investigation
confirmed it is fundamentally incompatible with Google Colab as of mid-2026.

---

## The original plan

| Environment | Tool | Why |
|-------------|------|-----|
| Local CPU | faster-whisper (small) | Lightweight, ~2 min per 4-min video |
| Colab T4 GPU | WhisperX (large-v3) | GPU speed + speaker diarisation for multi-speaker content |

The idea was that faster-whisper handles solo transcripts, and WhisperX adds speaker
labels for interviews, panels, and debates — exactly the kind of content FILMIG produces.

---

## What we discovered

WhisperX is incompatible with Colab. We spent 10 debugging sessions (June 2026) tracing
the issue through multiple layers:

### Dependency chain that breaks

```
whisperx → transformers → tensorflow → scipy → numpy._core.umath._center
                                                                      💥 removed in numpy ≥2.1
```

WhisperX 3.8.6 requires `numpy>=2.1.0`. Colab ships with scipy and tensorflow compiled
against older numpy ABIs. The result is a cascade of import errors:

1. `cannot import name '_center' from 'numpy._core.umath'` — numpy 2.1+ removed this internal
2. `'_blas_supports_fpe' has no attribute` — same class of ABI break with numpy 2.5+
3. `ValueError: All ufuncs must have type numpy.ufunc` — reported on Kaggle too ([#1267](https://github.com/m-bain/whisperX/issues/1267))

Pin older numpy? Can't — WhisperX demands `>=2.1.0`. Pin older scipy? Breaks other packages.
Create a venv? Colab doesn't let you.

### CUDA mismatch

WhisperX requires CUDA 12.8. Colab runs CUDA 12.2. Even if the Python imports worked,
the compiled CUDA kernels would fail at runtime.

### The project knows

Multiple open GitHub issues with zero fixes:

| Issue | Date | Error |
|-------|------|-------|
| [#1244](https://github.com/m-bain/whisperX/issues/1244) | Oct 2025 | `_center` import error on Colab |
| [#1302](https://github.com/m-bain/whisperX/issues/1302) | Nov 2025 | "colab issues" — torchvision circular import |
| [#1140](https://github.com/m-bain/whisperX/issues/1140) | 2025 | "How to run whisperx in Google colab?" — no working answer |
| [#905](https://github.com/m-bain/whisperX/issues/905) | 2025 | "whisperX not working with Google Colab?" |
| [#1027](https://github.com/m-bain/whisperX/issues/1027) | 2025 | `libcudnn_ops_infer.so.8` — CUDA library mismatch |
| [#901](https://github.com/m-bain/whisperX/issues/901) | 2025 | `libcudnn_ops.so.9` — same CUDA issue |

The PyPI release history shows the volatility: three versions yanked in 2025–2026 for
"dependency issues" and "incompatible torch, torchaudio version."

The official README itself points users to hosted demos ("If you don't have access to
your own GPUs, use the links above to try out WhisperX") — implicitly acknowledging
it does not work reliably on cloud notebooks.

### Where WhisperX DOES work

- **Local machine** with venv + Python 3.10–3.12 + CUDA 12.8
- **Docker** with pinned dependencies (`jim60105/docker-whisperX`)
- **Cloud GPU rentals** (RunPod, Lambda Labs, Vast.ai) where you control the environment

The common thread: you must control the entire dependency stack. Platforms with
pre-installed packages (Colab, Kaggle, Paperspace Gradient) are out.

---

## The decision

**Stay with faster-whisper everywhere.** Same Whisper model (large-v3), same transcription
quality, 4× faster, zero dependency conflicts.

### What we lose

- **Speaker diarisation** — no `[SPEAKER_00]` labels. FILMIG content is predominantly
  single-speaker presentations and monologues, so this is acceptable.
- **Word-level alignment via wav2vec2** — faster-whisper provides segment-level timestamps
  which are sufficient for the RAG pipeline.

### What we gain

- **Stability** — faster-whisper has one dependency (CTranslate2). No transformers, no
  tensorflow, no scipy, no pyannote. It just works.
- **Speed** — 70× real-time on GPU vs WhisperX's 60× (WhisperX spends extra time on
  alignment and diarisation).
- **Colab compatibility** — works on Colab's default CUDA without any special setup.
- **Smaller install** — faster-whisper is a single package. WhisperX pulls in torch,
  torchaudio, transformers, pyannote, and their transitive dependencies.
- **The community agrees** — the 2026 consensus guide states: *"For any local speech-to-text
  deployment in 2026 — Faster-Whisper is the right default. For subtitles / interviews
  with speaker labels: WhisperX."*

### If we ever need diarisation

We can revisit WhisperX if:
1. The project fixes Colab compatibility
2. We move to a controlled environment (Docker, RunPod)
3. We find an alternative diarisation approach that works with faster-whisper

---

## What changed in the codebase

| File | Change |
|------|--------|
| `backend/core/ingestion_audio.py` | `_transcribe_audio` uses `faster_whisper.WhisperModel` instead of `whisperx` |
| `requirements.txt` | `faster-whisper==1.2.1` replaces `whisperx>=3.8.0` |
| `notebooks/transcribe_video_colab.ipynb` | Sections 1, 5, 7 updated; HF token section marked optional |
| `presentation/migrant-archive-slides.html` | Slide 09, toolchain, tech stack updated |
| `notes/faster-whisper-migration.md` | This document — replaces `whisperx-multispeaker.md` |

### Segment output shape (unchanged)

```json
{
  "text": "Bienvenidos a la presentación de FILMIG 2024",
  "start": 0.5,
  "duration": 4.2,
  "speaker": "UNKNOWN"
}
```

The `speaker` field is kept for backward compatibility with the VideoData contract.
It always returns `"UNKNOWN"` since we don't run diarisation.

---

## Other yt-dlp fixes applied during this investigation

While debugging WhisperX, we also fixed the YouTube download pipeline:

- **Two-phase client strategy**: mobile clients (android → ios) without cookies first
  (bypass YouTube's JS challenge), web client with cookies + nodejs v22 as fallback.
- **Post-download verification**: the download function now verifies the file actually
  exists on disk before returning the computed path.
- **NodeSource v22**: Colab's apt nodejs is v12 (too old for yt-dlp challenges).
  NodeSource provides v22 which works.
- **SABR/PO Token warnings**: YouTube is experimenting with new restrictions on mobile
  clients. These warnings are harmless — yt-dlp finds alternative formats.
