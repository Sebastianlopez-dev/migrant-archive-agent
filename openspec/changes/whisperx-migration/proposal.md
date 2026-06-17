# Proposal: WhisperX Migration

## Intent

Replace `faster-whisper` with WhisperX in Strategy B (local CPU + Colab GPU) to add word-level timestamps and multi-speaker diarisation via `pyannote/speaker-diarization-3.1`. FILMIG content is interviews and panels — without speaker labels, RAG answers lose critical context ("Who said what?").

## Scope

### In Scope
- `backend/core/ingestion_audio.py`: Swap `WhisperModel` → `whisperx` pipeline (transcribe → align → diarise)
- `backend/core/ingestion_colab.py`: Forward new `hf_token` parameter (wrapper only)
- `VideoData.transcript_segments`: Each segment gains `"speaker"` key (defaults `"UNKNOWN"`)
- New dependency: `whisperx` in requirements / Conda env
- New env var: `HF_TOKEN` (already in `.env.example`)

### Out of Scope
- `VideoData` contract shape, `processor.py`, `vector_store.py`, `ingestion_caption.py`, `ingestion.py` — unchanged
- Colab notebook env-var wiring (separate change)
- Frontend speaker display

## Capabilities

### New Capabilities
- `audio-transcription-diarisation`: WhisperX-based transcription with forced alignment (word timestamps) and speaker diarisation via pyannote. Each segment returns `{text, start, duration, speaker}`.

### Modified Capabilities
- `audio-transcription` (if it exists): transcription engine swaps from faster-whisper to WhisperX; output gains speaker field. If no `audio-transcription` spec exists yet, treat as new.

## Approach

Three-step WhisperX pipeline: (1) `whisperx.load_model` + `.transcribe()` (same Whisper quality underneath), (2) `whisperx.load_align_model` + `.align()` for per-word timestamps, (3) `DiarizationPipeline` + `assign_word_speakers` when `hf_token` is set. Speaker defaults to `"UNKNOWN"` for backwards compatibility. Delete `_get_model()` and `_model_cache` — WhisperX manages its own model caching.

## Affected Areas

| Area | Impact | Description |
|------|--------|-------------|
| `backend/core/ingestion_audio.py` | Modified | Replace `_transcribe_audio()` with WhisperX pipeline |
| `backend/core/ingestion_colab.py` | Modified | Forward `hf_token` param to `extract_single_video` |
| `requirements.txt` | Modified | Replace `faster-whisper` with `whisperx` |
| `.env.example` | Done | `HF_TOKEN` already documented |

## Risks

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| PyTorch dependency (Conda needed) | High | Document Conda setup; verify `whisperx` install in CI |
| RAM increase ~2GB (4GB vs 2GB) | Med | Warn in README; test on target hardware |
| HF model download fails (terms not accepted) | Med | Validate HF_TOKEN + terms acceptance in setup script |
| Speaker accuracy degrades with noise | Low | `"UNKNOWN"` fallback; no pipeline breakage |

## Rollback Plan

1. `git revert` the merge commit for this change
2. Restore `faster-whisper` in `requirements.txt`
3. Restore original `_transcribe_audio()`, `_get_model()`, and `_model_cache`
4. Verify `extract_single_video` works without `hf_token`

## Dependencies

- `whisperx` (PyTorch — Conda environment)
- `pyannote/speaker-diarization-3.1` (downloaded on first run via HF)
- `HF_TOKEN` env var with accepted terms at `hf.co/pyannote/speaker-diarization-3.1`

## Success Criteria

- [ ] `_transcribe_audio()` produces `{text, start, duration, speaker}` per segment
- [ ] Speaker field defaults to `"UNKNOWN"` when `HF_TOKEN` is unset
- [ ] `extract_single_video_colab()` accepts and forwards `hf_token`
- [ ] Transcribed JSON loads into `VideoData` without schema errors
- [ ] Transcription quality matches or exceeds faster-whisper (same underlying model)
