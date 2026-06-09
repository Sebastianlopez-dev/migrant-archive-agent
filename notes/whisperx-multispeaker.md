# Future: Multi-speaker Transcription (WhisperX)

**Status**: not implemented — documented for when needed.

## Problem

Current `faster-whisper` transcribes WHAT is said but not WHO said it.
If the channel has interviews, panels, or debates, RAG answers lose speaker context.

## Solution: WhisperX

[WhisperX](https://github.com/m-bain/whisperX) is a drop-in upgrade over faster-whisper
that adds word-level timestamps and speaker diarisation.

### What it adds

| Feature | faster-whisper (current) | WhisperX (future) |
|---------|--------------------------|-------------------|
| Transcription | ✅ | ✅ (same quality) |
| Word timestamps | ❌ (segment only) | ✅ per-word |
| Speaker labels | ❌ | ✅ `[SPEAKER_00]`, `[SPEAKER_01]` |
| Forced alignment | ❌ | ✅ (corrects timestamps) |

### Setup

```bash
pip install whisperx
```

Requires a free HuggingFace token for diarisation (create at huggingface.co/settings/tokens).

### Code sketch

```python
import whisperx

# Same model as faster-whisper underneath
model = whisperx.load_model("small", device="cpu", compute_type="int8")
audio = whisperx.load_audio("data/audio/VIDEO_ID.mp3")

# Transcribe (same quality)
result = model.transcribe(audio, language="es")

# Align (correct timestamps to word level)
model_a, metadata = whisperx.load_align_model(language_code="es", device="cpu")
result = whisperx.align(result["segments"], model_a, metadata, audio, device="cpu")

# Diarise (assign speakers)
diarize = whisperx.DiarizationPipeline(use_auth_token="YOUR_HF_TOKEN")
diarize_segments = diarize("data/audio/VIDEO_ID.mp3")
result = whisperx.assign_word_speakers(diarize_segments, result)

# Result has speaker in each segment
for seg in result["segments"]:
    print(f"[{seg['start']:.1f}s] {seg.get('speaker', 'UNKNOWN')}: {seg['text']}")
```

### Impact on our codebase

Minimal. Only `ingestion_audio.py` changes.  Here's exactly what to swap:

```python
# ── FILE: backend/core/ingestion_audio.py ──

# 1. Replace the import (line 18)
# BEFORE:
from faster_whisper import WhisperModel

# AFTER:
import whisperx


# 2. Replace _transcribe_audio() (lines 123-156) with this version:
def _transcribe_audio(
    audio_path: str | Path,
    language: str,
    model_size: str = "small",
    device: str = "auto",
    hf_token: str | None = None,                # ← new: HuggingFace token
) -> list[dict]:
    """Transcribe with WhisperX — word timestamps + speaker diarisation."""
    if device == "auto":
        device = _detect_device()

    compute = _compute_type_for(device)
    audio_file = str(audio_path)

    # ── Step 1: transcribe (same as faster-whisper) ──
    model = whisperx.load_model(model_size, device=device, compute_type=compute)
    result = model.transcribe(audio_file, language=language)

    # ── Step 2: align word-level timestamps ──
    align_model, align_meta = whisperx.load_align_model(
        language_code=language, device=device
    )
    result = whisperx.align(
        result["segments"], align_model, align_meta, audio_file, device
    )

    # ── Step 3: assign speakers (skip if no HF token) ──
    if hf_token:
        diarize = whisperx.DiarizationPipeline(use_auth_token=hf_token, device=device)
        diarize_segments = diarize(audio_file)
        result = whisperx.assign_word_speakers(diarize_segments, result)
        speaker_key = lambda s: s.get("speaker", "UNKNOWN")
    else:
        speaker_key = lambda s: "UNKNOWN"

    return [
        {
            "text": seg["text"].strip(),
            "start": round(seg["start"], 1),
            "duration": round(seg["end"] - seg["start"], 1),
            "speaker": speaker_key(seg),           # ← NEW FIELD
        }
        for seg in result["segments"]
    ]


# 3. In extract_single_video() (line 83), add hf_token param:
def extract_single_video(
    video_url: str,
    languages: list[str] | None = None,
    model_size: str = "small",
    device: str = "auto",
    output_dir: str = "data/raw/whisper",
    audio_dir: str = "data/audio",
    hf_token: str | None = None,                   # ← new
) -> VideoData:
    ...
    segments = _transcribe_audio(
        audio_path,
        language=languages[0],
        model_size=model_size,
        device=device,
        hf_token=hf_token,                          # ← new
    )
    ...


# 4. In the CLI block (line 162), add --hf-token flag:
parser.add_argument(
    "--hf-token",
    default=None,
    help="HuggingFace token for speaker diarisation (optional)",
)
# And pass it through:
data = extract_single_video(
    ...,
    hf_token=args.hf_token,
)
```

**That's it.** `VideoData`, `processor.py`, `vector_store.py` — all unchanged.
The `"speaker"` key in each segment dict is backwards-compatible (defaults to `"UNKNOWN"`).
Delete `_get_model()` and `_model_cache` — WhisperX manages its own caching.

### Tradeoffs

| | faster-whisper | WhisperX |
|---|---------------|----------|
| Speed | ~2 min (4 min video) | ~3 min (adds alignment + diarisation) |
| RAM | ~2GB | ~4GB |
| Dependencies | 1 package | 3 packages (whisperx, pyannote, torch) |
| Speaker accuracy | N/A | ~90% (degrades with background noise) |

### When to adopt

When RAG answers need attribution like "Speaker A said X, Speaker B disagreed with Y".
Not needed for single-speaker content (tutorials, keynote talks, monologues).
