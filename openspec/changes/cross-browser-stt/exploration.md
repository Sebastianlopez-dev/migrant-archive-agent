# Exploration: Cross-Browser Speech-to-Text Backend

## Current State

The frontend in `frontend/src/input-bar.ts` uses a two-tier voice strategy:

1. **Primary**: Web Speech API (Chrome, Edge, Safari).
2. **Fallback**: `MediaRecorder` that records up to 10 seconds of audio and `POST`s it as `audio/webm` (or `audio/mp4` on Safari) to `/api/transcribe`.

The backend endpoint exists at `backend/api/routes/transcribe.py` but is **not wired into `backend/api/main.py`**. It uses `faster-whisper` (`tiny`, CPU, `int8`) and expects a multipart file upload, returning `TranscribeResponse(text=...)`. On the current Mac server it crashes on startup with `OMP Error #15` because two OpenMP runtimes are loaded into the same process (`torch` + `ctranslate2`). `KMP_DUPLICATE_LIB_OK` was already tried without success.

Goal: provide a backend transcription path that works for Firefox, Brave, and Safari users without crashing the server, is cheap at low volume, and can be demo-ready this week.

## Assumptions

- ~100 transcriptions/month.
- Average recorded clip: ~10 seconds (max 10 s in the frontend).
- Total monthly audio: ~1,000 s ≈ 16.7 min ≈ 0.28 h.
- Spanish-language audio (`language="es"` in the current endpoint).

## Option A — Cloud STT APIs (fully managed)

### A1. Groq Whisper API (Whisper Large v3 / Turbo)

**How it works**: Groq runs open-source Whisper on its own LPU hardware. The API is OpenAI-compatible: upload an audio file and get back text. Supports `mp3`, `mp4`, `mpeg`, `mpga`, `m4a`, `wav`, `webm`, up to 25 MB on the free tier.

**Latency (30 s clip)**: ~0.1–0.4 s end-to-end. Groq benchmarks Whisper Large V3 Turbo at ~228× real-time; a 30 s clip is processed in well under a second, plus network.

**Monthly cost**: $0.04/h (Whisper Large v3 Turbo). For 0.28 h/month → **~$0.01/month**. The free tier allows 2,000 audio requests/day, so this workload is effectively free.

**Integration complexity**: Low. Add `groq` (or just `httpx`/`requests` hitting the OpenAI-compatible endpoint), swap the model call in `transcribe.py`, and register the router in `main.py`. No ffmpeg or model loading needed.

**Browser compatibility**: Excellent. The frontend already sends a webm/mp4 blob; Groq accepts webm directly.

### A2. OpenAI Whisper API

**How it works**: OpenAI-hosted Whisper. Upload audio, get text. Supports `mp3`, `mp4`, `mpeg`, `mpga`, `m4a`, `wav`, `webm`, up to 25 MB.

**Latency (30 s clip)**: ~1–3 s typical.

**Monthly cost**: $0.006/min for `whisper-1`/`gpt-4o-transcribe` ($0.36/h), or $0.003/min for `gpt-4o-mini-transcribe`. For 16.7 min/month → **$0.05–$0.10/month**. New accounts receive $5 in credits.

**Integration complexity**: Low. Official Python SDK; drop-in replacement for the local model.

**Browser compatibility**: Excellent. Accepts webm directly.

### A3. Deepgram Nova-3 / Flux

**How it works**: Managed STT with batch and streaming endpoints. Strong for English-first real-time voice agents.

**Latency (30 s clip)**: Batch ~1–3 s; streaming <1 s.

**Monthly cost**: Batch ~$0.0043/min ($0.258/h) → **~$0.07/month** for 16.7 min. Free tier: $200 credit.

**Integration complexity**: Medium. SDK available, but streaming requires WebSocket handling; batch is simpler.

**Browser compatibility**: Good, but webm may need to be converted to a supported format depending on codec.

### A4. AssemblyAI Universal-3 Pro

**How it works**: Async or streaming transcription with built-in diarization, summarization, and PII redaction.

**Latency (30 s clip)**: Batch ~2–5 s.

**Monthly cost**: Batch starts around $0.0025/min ($0.15/h) → **~$0.04/month**. Free tier: $50 credit.

**Integration complexity**: Medium. Upload and poll or use SDK.

**Browser compatibility**: Good.

### A5. Google Cloud Speech-to-Text

**How it works**: GCP-managed STT with Chirp models and v1/v2 APIs.

**Latency (30 s clip)**: ~1–3 s.

**Monthly cost**: ~$0.016/min for Chirp → **~$0.27/month**. Perpetual free tier: 60 min/month, so 16.7 min is free. New customers also get $300 credits.

**Integration complexity**: Medium. Requires GCP project, authentication, and heavier SDK.

**Browser compatibility**: Good.

## Option B — Serverless Whisper

### B1. Modal

**How it works**: Deploy a containerized Whisper function that scales to zero. You bring the model and code; Modal manages GPU/CPU scheduling.

**Latency (30 s clip)**: ~2–10 s, dominated by cold start if no keep-warm. Warm requests: sub-second.

**Monthly cost**: At ~$0.000306/s for A10G or ~$0.001036/s for A100 40GB, 100 requests/month could be **$0.50–$5.00/month** depending on cold starts and GPU choice. A CPU-only function would be cheaper but slower.

**Integration complexity**: Medium. Requires writing a Modal app, container image, and separate deployment.

**Browser compatibility**: Good — your Modal endpoint can accept whatever multipart file you send.

### B2. RunPod Serverless (faster-whisper template)

**How it works**: Pre-built or custom serverless GPU endpoint. RunPod advertises a faster-whisper endpoint at ~$0.00025/s.

**Latency (30 s clip)**: ~2–10 s including cold start.

**Monthly cost**: Similar to Modal, **$0.50–$5.00/month** for this volume.

**Integration complexity**: Medium. Must configure the endpoint and handle cold-start latency.

**Browser compatibility**: Good.

### B3. Replicate

**How it works**: Hosted model API for Whisper and Whisper Large v3 Turbo.

**Latency (30 s clip)**: ~1–5 s.

**Monthly cost**: ~$0.04–$0.11/h depending on model → **~$0.01–$0.03/month**, but Replicate has a minimum billing/credit model that may dominate at very low volume.

**Integration complexity**: Low-Medium. REST API, but model inputs/outputs are Replicate-specific.

**Browser compatibility**: Good.

### B4. Banana.dev

**How it works**: Serverless GPU platform with Whisper templates.

**Status**: Banana sunset its legacy serverless GPU product; while the domain still exists, it is no longer the reliable option it once was. Not recommended for a demo this week.

## Option C — Separate Transcription Microservice

**How it works**: Run a tiny FastAPI/Flask service in its own process/container that only loads `faster-whisper` or `whisper.cpp`. The main Migrant Archive API proxies audio to it.

**Latency (30 s clip)**: Local CPU faster-whisper tiny: ~1–3 s; whisper.cpp tiny on Apple Silicon: ~0.5–2 s.

**Monthly cost**: If hosted on Railway/Fly.io as a sidecar: **$5–$20/month** for always-on CPU. If left on the same Mac server but in an isolated process: $0, but requires maintenance.

**Integration complexity**: Medium-High. Adds deployment surface, networking, and a second service to monitor.

**Browser compatibility**: Good.

**Does it avoid the OpenMP conflict?** Probably yes if run in a fresh Python environment without `torch` loaded, or if using `whisper.cpp`. The conflict comes from multiple OpenMP runtimes in the same process; a separate process with a minimal dependency set avoids the clash.

## Option D — Fix the Local OpenMP Issue

**Known fixes for `OMP Error #15` with `faster-whisper`**:

- The error means two OpenMP runtimes were loaded (commonly Intel `libiomp5` + LLVM `libomp`, or MKL + PyTorch).
- Common fixes:
  - Set `OMP_NUM_THREADS` and `MKL_NUM_THREADS` consistently.
  - In a Conda environment, install `nomkl` or the `no-mkl` metapackage.
  - Uninstall/reinstall `ctranslate2` and `torch` from the same channel.
  - Use `whisper.cpp` instead of `faster-whisper`; it is a C++ port that avoids the Python OpenMP dependency chain and is optimized for Apple Silicon.
  - Use the original `openai-whisper` package, but it pulls in PyTorch and may hit the same or new MPS issues on Mac.

**Latency (30 s clip)**: `whisper.cpp` tiny on Mac: ~0.5–2 s; `faster-whisper` tiny CPU: ~1–3 s when working.

**Monthly cost**: $0.

**Integration complexity**: Medium. Switching runtimes requires testing audio format handling and ensuring Spanish transcription quality.

**Browser compatibility**: Good.

**Risk**: Debugging OpenMP/library conflicts on a presentation deadline is unpredictable. `KMP_DUPLICATE_LIB_OK` was already tried and did not work.

## Comparison Matrix

| Approach | Category | Latency (30 s) | Monthly Cost (100 × 10 s) | Integration | Browser webm/wav | Demo-ready this week |
| --- | --- | --- | --- | --- | --- | --- |
| Groq Whisper Large v3 Turbo | Cloud API | ~0.1–0.4 s | ~$0.01 (effectively free) | Low | Yes | Yes |
| OpenAI Whisper / GPT-4o-mini-transcribe | Cloud API | ~1–3 s | ~$0.05–$0.10 | Low | Yes | Yes |
| Deepgram Nova-3 batch | Cloud API | ~1–3 s | ~$0.07 | Medium | Yes | Yes |
| AssemblyAI Universal-3 Pro batch | Cloud API | ~2–5 s | ~$0.04 | Medium | Yes | Yes |
| Google Cloud Speech-to-Text | Cloud API | ~1–3 s | Free (≤60 min) | Medium | Yes | Yes |
| Modal serverless Whisper | Serverless | ~2–10 s | ~$0.50–$5.00 | Medium | Yes | Maybe |
| RunPod serverless Whisper | Serverless | ~2–10 s | ~$0.50–$5.00 | Medium | Yes | Maybe |
| Replicate Whisper | Serverless | ~1–5 s | ~$0.01–$0.03 | Low-Medium | Yes | Yes |
| Separate microservice (whisper.cpp) | Decoupled | ~0.5–2 s | $5–$20 hosted / $0 on Mac | Medium-High | Yes | Maybe |
| Fix local OpenMP / whisper.cpp | Local | ~0.5–3 s | $0 | Medium | Yes | Risky |

## Affected Areas

- `backend/api/routes/transcribe.py` — replace or wrap the local model call.
- `backend/api/main.py` — register the `transcribe` router.
- `backend/api/models.py` — `TranscribeResponse` is already correct.
- `frontend/src/input-bar.ts` — no changes required; it already sends `audio/webm`/`audio/mp4` blobs.
- `.env` / environment — add a new API key for the chosen provider.
- `requirements.txt` — add SDK/client for chosen provider if needed.

## Recommendation

**Use the Groq Whisper API (`whisper-large-v3-turbo`) as the backend transcription provider.**

It is the best fit for this project because:

1. **Cost**: At $0.04/hour it is the cheapest managed option, and the free tier covers this workload entirely.
2. **Speed**: ~228× real-time means a 30-second clip returns in well under a second, giving a snappy demo.
3. **Simplicity**: OpenAI-compatible REST API; the existing `transcribe.py` can be adapted in minutes.
4. **Reliability**: No local OpenMP conflict, no model loading, no GPU drivers, no cold starts.
5. **Browser coverage**: Accepts webm directly from `MediaRecorder`, so Firefox, Brave, and Safari fallbacks work unchanged.
6. **Presentation-ready**: Can be integrated and tested today.

**Runner-up**: OpenAI `gpt-4o-mini-transcribe` at $0.003/min is only slightly more expensive and equally simple, but Groq is faster and cheaper.

**Avoid for this week**: fixing the local OpenMP issue or deploying a separate microservice. Both are valid long-term paths but introduce uncertainty before a demo deadline.

## Risks

- **Provider dependency**: Audio leaves the server. For a public archive/chatbot demo this is acceptable, but it should be documented.
- **Free-tier limits**: Groq's free tier is generous (2,000 requests/day), but a spike during a live demo is still well within limits.
- **Network latency**: On a slow connection the upload of a 10-second webm clip can take longer than the transcription itself. The frontend already caps recordings at 10 seconds to mitigate this.
- **Audio format edge cases**: Safari may send `audio/mp4`; Groq accepts mp4, but we should verify with a real Safari recording.

## Ready for Proposal

Yes. The next step is to write a proposal for replacing the local `faster-whisper` call in `backend/api/routes/transcribe.py` with the Groq Whisper API, registering the router in `backend/api/main.py`, and adding the API key to the environment.
