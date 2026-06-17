# Audio Ingestion — Full Specification

## Purpose

Transcribe audio/video files into structured text segments with word-level timestamps and optional speaker diarisation. Replaces faster-whisper with WhisperX.

## Requirements

### REQ-WX-001: WhisperX Transcription

`_transcribe_audio()` in `ingestion_audio.py` MUST use WhisperX instead of faster-whisper. Output segments MUST contain `{text, start, duration}` and MAY include a `"speaker"` field.

#### Scenario: Identical segment structure

- GIVEN a valid audio file
- WHEN `_transcribe_audio()` is called
- THEN it returns segments with `text`, `start`, `duration` keys matching the faster-whisper format
- AND each segment MAY include `"speaker"`

### REQ-WX-002: Speaker Diarisation

When `HF_TOKEN` is provided, each segment MUST include `"speaker"` with values `SPEAKER_00`, `SPEAKER_01`, etc. When `HF_TOKEN` is absent, speaker MUST default to `"UNKNOWN"`.

#### Scenario: Diarisation with HF_TOKEN

- GIVEN a Spanish video with 3 speakers and `HF_TOKEN` set
- WHEN `_transcribe_audio()` processes it
- THEN each segment has `"speaker"` matching `SPEAKER_XX`
- AND segments for the same speaker share the same label

#### Scenario: No HF_TOKEN fallback

- GIVEN no `HF_TOKEN` is set
- WHEN `_transcribe_audio()` processes an audio file
- THEN all segments have `"speaker": "UNKNOWN"`
- AND transcription succeeds without error

### REQ-WX-003: Word-Level Alignment

WhisperX MUST perform forced alignment to correct segment timestamps to word-level accuracy.

#### Scenario: Alignment improves precision

- GIVEN an audio file with clear speech
- WHEN the WhisperX `.align()` step runs
- THEN segment `start` and `duration` values reflect word-level boundaries
- AND timestamps are more precise than faster-whisper segment-level output

### REQ-WX-004: Colab Wrapper Forwarding

`ingestion_colab.py` MUST forward `hf_token` to `extract_single_video()` without changing its own logic.

#### Scenario: hf_token forwarded through colab wrapper

- GIVEN `extract_single_video_colab()` is called with `hf_token`
- WHEN it delegates to `extract_single_video()`
- THEN the `hf_token` parameter is passed through unchanged

### REQ-WX-005: Backwards Compatibility

`VideoData` MUST load existing JSON files that lack a `"speaker"` key. `processor.py` and `vector_store.py` MUST work without changes.

#### Scenario: Load legacy JSON without speaker

- GIVEN a saved JSON file from before the migration (no `"speaker"` key)
- WHEN loaded with `VideoData.load_json()`
- THEN it loads without error
- AND all segments are accessible

### REQ-WX-006: Model Cache Removal

`_get_model()` and `_model_cache` in `ingestion_audio.py` MUST be removed. WhisperX manages its own model caching.

#### Scenario: No stale cache references

- GIVEN the updated `ingestion_audio.py`
- WHEN the module is imported
- THEN no `_get_model()` function or `_model_cache` dict exists
- AND WhisperX handles model lifecycle internally
