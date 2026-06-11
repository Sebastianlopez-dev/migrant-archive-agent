# YouTube → Blog Text (2 Python scripts)

This folder contains **two small, educational scripts** that solve _two different pipelines_:

1. **`youtube_audio_transcribe_channel.py`**  
   For a channel/playlist where videos **do not have captions**, it downloads **audio** and then generates **a transcript** using **local Whisper**.

2. **`youtube_download_captions.py`**  
   For a video that **already has captions**, it downloads the **caption file** (WebVTT) and converts it to **plain text**.

Both scripts are written in Python and include **line-by-line explanations as comments** inside the code.

---

## Quick start (local machine)

### 1) Install dependencies

You need:

- Python 3.10+ (3.11 is fine)
- **FFmpeg** (required for audio extraction in script #1)
- Python packages:
  - `yt-dlp`
  - `openai-whisper` (only needed for script #1)

Install packages:

```bash
pip install yt-dlp openai-whisper
```

Install FFmpeg (examples):

- macOS (Homebrew): `brew install ffmpeg`
- Ubuntu/Debian: `sudo apt-get install ffmpeg`
- Windows: install FFmpeg and make sure `ffmpeg` is in your PATH

---

## Script 1 — Download audio from a channel/playlist and transcribe

### What it does

- Enumerates videos from a **channel or playlist URL**
- Downloads **best audio** for each video and converts it to **MP3**
- Runs **Whisper** locally to generate:
  - a blog-ready `*.txt` transcript
  - optionally a `*.srt` file with timestamps

### Usage

```bash
python youtube_audio_transcribe_channel.py "https://www.youtube.com/@SomeChannel/videos" --output-dir output --whisper-model small
```

Test on only the first 3 videos:

```bash
python youtube_audio_transcribe_channel.py "CHANNEL_OR_PLAYLIST_URL" --limit 3
```

Also save SRT subtitles:

```bash
python youtube_audio_transcribe_channel.py "CHANNEL_OR_PLAYLIST_URL" --save-srt
```

### Output structure

By default, it writes to `./output/`:

- `output/audio/` → downloaded MP3 files
- `output/transcripts/` → Whisper transcripts (`.txt`, and optional `.srt`)

---

## Script 2 — Download captions (subtitles) from a single video

### What it does

- Downloads existing subtitle files from a video (no audio download)
- Converts WebVTT (`.vtt`) to clean plain text (`.txt`)

### Usage

Download English captions:

```bash
python youtube_download_captions.py "https://www.youtube.com/watch?v=VIDEO_ID" --lang en --output-dir output
```

If the video only has **auto-generated captions**, allow them:

```bash
python youtube_download_captions.py "VIDEO_URL" --lang en --allow-auto
```

### Output structure

By default, it writes to:

- `output/captions/`
  - `...<lang>.vtt` (raw captions)
  - `...<lang>.txt` (clean text)

---

## Choosing and creating output paths (and options to store the text)

Both scripts accept `--output-dir`, and they **create directories automatically** using:

- `Path(...).expanduser().resolve()` to normalize the path
- `mkdir(parents=True, exist_ok=True)` to create it safely

Common output directory choices:

1. **Relative folder (default)**: `--output-dir output`  
   Good for quick tests, keeps outputs next to your scripts.

2. **Absolute folder**: `--output-dir /abs/path/to/blog_assets`  
   Good when you want a stable location.

3. **User home subfolder**: `--output-dir ~/blog/youtube`  
   Good if you want it under your user directory.

Different ways to store transcripts/captions (what you might do next):

- **Plain text (`.txt`)**: best for blog drafts (simple, searchable).
- **Markdown (`.md`)**: best if your blog is markdown-based (you might add headings, links, etc.).
- **Subtitle formats (`.srt` / `.vtt`)**: best for editing or reusing in video workflows.
- **JSON**: best when you need structured data (timestamps, segments, speaker labels, etc.).

These scripts write `.txt` by default because it’s the simplest blog-friendly output.

---

## Why these scripts are different from a real production pipeline

These scripts are intentionally **simple** and optimized for learning / small-scale use.

In a real production system, you would typically add:

1. **Queue + workers**  
   Use a job queue (Celery/RQ/SQS) so downloads/transcriptions run asynchronously and can be retried safely.

2. **Idempotency and caching**  
   Avoid re-downloading/transcribing if outputs already exist (store hashes, video IDs, timestamps).

3. **Robust error handling / retries**  
   Network failures, removed videos, geo restrictions, rate limits, FFmpeg issues, partial downloads.

4. **Persistent storage**  
   Store artifacts in object storage (S3/GCS/Azure Blob) rather than local disk.

5. **Observability**  
   Structured logs, metrics, tracing, alerting when jobs fail.

6. **Scalable transcription**
   - GPU-backed Whisper inference, or
   - a dedicated transcription service, or
   - chunking long audio, parallelism, diarization (speaker separation), etc.

7. **Content normalization for publishing**  
   Post-processing: paragraphing, punctuation cleanup, removing filler words, adding headings, turning into Markdown/HTML, linking sources.

8. **Compliance / policy checks**  
   Depending on your context: copyright, usage rights, platform terms, and internal policies.

In short: **these scripts are “single-machine utilities”**. Production systems are usually **distributed**, **observable**, and designed to be **reliable at scale**.

---

## Notes / troubleshooting

- If script #1 fails during audio conversion, verify `ffmpeg -version` works.
- If Whisper is slow, try `--whisper-model tiny` (faster, less accurate).
- If script #2 says subtitles are missing, try another `--lang` or `--allow-auto`.
