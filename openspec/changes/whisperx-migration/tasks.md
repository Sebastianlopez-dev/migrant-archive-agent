# Tasks: WhisperX Migration

## Review Workload Forecast

Decision needed before apply: No
Chained PRs recommended: Yes
Chain strategy: feature-branch-chain
400-line budget risk: Low
Tracker branch: `feature/whisperx-migration` (draft, no-merge)

| Unit | Goal | Likely PR | Base Branch | Notes |
|------|------|-----------|-------------|-------|
| 1 | Foundation: deps + RED tests | PR 1 | tracker branch | New `tests/test_whisperx_audio.py`; bump `requirements.txt` |
| 2 | Core implementation | PR 2 | PR 1 branch | Replace `_transcribe_audio()`; add `hf_token`; drop cache; tests GREEN |
| 3 | Colab wrapper | PR 3 | PR 2 branch | Forward `hf_token` through `ingestion_colab.py` |

Estimated diff: ~140-175 lines total.

## Phase 1: Foundation (PR 1 — base: tracker)

- [x] 1.1 In `requirements.txt`: drop `faster-whisper==1.2.1`, add `whisperx==<latest>`
- [x] 1.2 Create `tests/test_whisperx_audio.py` — RED: `_transcribe_audio()` returns `[{text, start, duration, speaker}]`
- [x] 1.3 RED: `hf_token=None` → every segment `speaker == "UNKNOWN"`
- [x] 1.4 RED: `extract_single_video()` accepts `hf_token: str | None = None`
- [x] 1.5 RED: `VideoData.load_json()` loads pre-migration JSON (no `speaker` key) without error
- [x] 1.6 RED: `extract_single_video_colab()` accepts and forwards `hf_token`
- [x] 1.7 Run `pytest tests/test_whisperx_audio.py` — confirm all RED
- [ ] 1.8 Open PR 1 → `feature/whisperx-migration` (draft); title `chore(whisperx): deps + RED tests`

## Phase 2: Core Implementation (PR 2 — base: PR 1)

- [ ] 2.1 In `backend/core/ingestion_audio.py`: swap `from faster_whisper import WhisperModel` → `import whisperx`
- [ ] 2.2 Rewrite `_transcribe_audio()`: `load_model` → `transcribe` → `load_align_model` → `align`
- [ ] 2.3 If `hf_token`: `DiarizationPipeline(use_auth_token=hf_token)` + `assign_word_speakers`; else stamp `speaker="UNKNOWN"`
- [ ] 2.4 Return `[{text, start, duration, speaker}]` with `round(..., 1)` on `start`/`duration`
- [ ] 2.5 Add `hf_token: str | None = None` to `extract_single_video()`; pass through
- [ ] 2.6 Add `--hf-token` argparse flag; forward to `extract_single_video()`
- [ ] 2.7 Delete `_get_model()` and `_model_cache` (REQ-WX-006)
- [ ] 2.8 Remove `WHISPER_BEAM_SIZE` if no longer referenced
- [ ] 2.9 `pytest tests/test_whisperx_audio.py -v` — confirm GREEN
- [ ] 2.10 `pytest tests/` — confirm no regressions
- [ ] 2.11 Open PR 2 → PR 1 branch; title `feat(whisperx): swap faster-whisper for WhisperX`

## Phase 3: Colab Wrapper (PR 3 — base: PR 2)

- [ ] 3.1 In `backend/core/ingestion_colab.py`: add `hf_token: str | None = None` to `extract_single_video_colab()`
- [ ] 3.2 Forward `hf_token=hf_token` to `extract_single_video()`
- [ ] 3.3 Add `--hf-token` argparse flag; forward to `extract_single_video_colab()`
- [ ] 3.4 `pytest tests/test_whisperx_audio.py` — wrapper test stays GREEN
- [ ] 3.5 Open PR 3 → PR 2 branch; title `feat(whisperx): forward hf_token through colab wrapper`

## Phase 4: Verification (after PR 3 → tracker)

- [ ] 4.1 `pytest tests/ -v` from `feature/whisperx-migration` tip
- [ ] 4.2 Smoke: `python -m backend.core.ingestion_audio --url <test>` → JSON with `speaker` field
- [ ] 4.3 Smoke: `--hf-token $HF_TOKEN` → segments carry `SPEAKER_XX` labels
- [ ] 4.4 Regression: `VideoData.load_json()` on one pre-migration JSON from `data/raw/whisper/`
- [ ] 4.5 Merge tracker to main; archive change

## Out of Scope

Colab notebook env-var wiring · Frontend speaker display · Pinning `pyannote.audio` (verify transitive first).
