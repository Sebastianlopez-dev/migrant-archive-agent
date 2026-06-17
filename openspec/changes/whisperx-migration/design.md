# Design: WhisperX Migration

## Technical Approach

Swap the transcription engine in `ingestion_audio.py` from faster-whisper to WhisperX. The change is isolated to the private `_transcribe_audio()` helper. The public `extract_single_video()` API gains an optional `hf_token` parameter that flows through to the diarisation step. WhisperX's three-step pipeline (transcribe → align → diarise) replaces the single faster-whisper call. The existing `_detect_device()` and `_compute_type_for()` helpers remain because both backends use CTranslate2.

## Architecture Decisions

| Decision | Option | Tradeoff | Choice |
|---|---|---|---|
| Transcription engine | WhisperX | Needs Conda/PyTorch; ~2GB extra RAM; gives word timestamps + diarisation | WhisperX |
| | Keep faster-whisper | No diarisation; simpler install | Rejected — diarisation is required |
| Model caching | Delete `_get_model()` / `_model_cache` | Lose manual cache control; gain simpler code | Delete — WhisperX handles caching internally |
| | Keep custom cache | More code to maintain; no benefit | Rejected |
| HF token handling | Optional `hf_token` param | Caller must provide token; graceful fallback to "UNKNOWN" | Optional param with fallback |
| | Mandatory env var only | Less flexible; breaks without token | Rejected |
| Colab wrapper change | Forward `hf_token` only | Minimal change; no WhisperX import in wrapper | Forward only |
| | Import WhisperX in wrapper | Duplicates logic; violates wrapper purpose | Rejected |

## Data Flow

```
YouTube URL → yt-dlp → audio mp3
                    ↓
            _transcribe_audio(audio_path, hf_token)
                    ↓
            whisperx.load_model(device, compute_type)
                    ↓
            model.transcribe(audio) → segments
                    ↓
            whisperx.load_align_model(language)
                    ↓
            align() → word-level timestamps
                    ↓
            if hf_token:
              DiarizationPipeline(auth_token=hf_token)
                    ↓
              assign_word_speakers() → SPEAKER_XX
            else:
              speaker = "UNKNOWN"
                    ↓
            [{text, start, duration, speaker}, ...]
                    ↓
            _build_videodata() → VideoData → JSON
```

## File Changes

| File | Action | Description |
|------|--------|-------------|
| `backend/core/ingestion_audio.py` | Modify | Replace `_transcribe_audio()` with WhisperX pipeline. Delete `_get_model()` and `_model_cache`. Add `hf_token` param to `extract_single_video()` and CLI `--hf-token`. |
| `backend/core/ingestion_colab.py` | Modify | Add `hf_token` param to `extract_single_video_colab()`. Add `--hf-token` CLI flag. Forward to `extract_single_video()`. |
| `requirements.txt` | Modify | Replace `faster-whisper` with `whisperx`. Add `pyannote.audio` if not pulled transitively. |

## Interfaces / Contracts

```python
def _transcribe_audio(
    audio_path: str | Path,
    language: str,
    model_size: str = "small",
    device: str = "auto",
    hf_token: str | None = None,
) -> list[dict]:
    """
    Returns segments in shape:
        [{text: str, start: float, duration: float, speaker: str}, ...]
    speaker defaults to "UNKNOWN" if hf_token is None or diarisation fails.
    """
```

`extract_single_video(video_url, ..., hf_token: str | None = None)` — new optional parameter.

`VideoData.transcript_segments` remains `list[dict]`. The `"speaker"` key is additive; existing code reading `text`, `start`, `duration` is unaffected.

## Testing Strategy

| Layer | What to Test | Approach |
|-------|-------------|----------|
| Unit | `_transcribe_audio()` returns correct dict shape | Mock whisperx load/align/diarise; assert segment keys and speaker fallback |
| Integration | End-to-end on a 30-second audio file | Run `extract_single_video()` with and without `HF_TOKEN`; verify JSON output |
| Regression | Load legacy JSON (no speaker key) | `VideoData.load_json()` on pre-migration file; assert no errors |

## Migration / Rollout

No data migration required. Existing JSON files load fine because `VideoData.load_json()` unpacks `**data` and `transcript_segments` dicts are untyped. New files will include the `"speaker"` key.

Rollout steps:
1. Install `whisperx` in the active environment (Conda recommended).
2. Set `HF_TOKEN` in `.env` and accept terms at hf.co/pyannote/speaker-diarization-3.1.
3. Run integration test on one short video.
4. Merge and verify CI passes.

Rollback: revert the commit, restore `faster-whisper` in `requirements.txt`, restore old `_transcribe_audio()` / `_get_model()` / `_model_cache`.

## Open Questions

- [ ] Does `whisperx` pull `pyannote.audio` transitively, or should it be pinned in `requirements.txt`?
- [ ] Should we keep `faster-whisper` as a fallback dependency for the UV install path, or switch entirely to Conda?
