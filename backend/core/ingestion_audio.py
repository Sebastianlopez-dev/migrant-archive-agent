"""Audio-based ingestion: downloads audio and transcribes locally.

Strategy: yt-dlp (audio download) → faster-whisper (local transcription).
Higher quality than auto-captions: proper punctuation, capitalisation, and
better accuracy on challenging audio.  Requires FFmpeg and CPU/GPU time.
Cost: $0 (runs entirely on your machine).

Device auto-detection: tries CUDA first, falls back to CPU.
Override with --device cpu | cuda | auto.

Best for: videos ≤ 5 minutes on local CPU.
For longer videos, use ingestion_colab.py (free Colab GPU, 10x faster).
"""

import sys
from pathlib import Path

# Make sibling imports work regardless of where the script is invoked from
sys.path.insert(0, str(Path(__file__).parent))

from faster_whisper import WhisperModel

from ingestion import VideoData, _build_videodata, _download_audio, _fetch_metadata


# ---------------------------------------------------------------------------
# Device detection — auto or manual
# ---------------------------------------------------------------------------

def _detect_device() -> str:
    """Return 'cuda' if a CUDA-capable GPU is available, else 'cpu'.

    Uses ctranslate2 (faster-whisper's backend) to probe.
    """
    try:
        import ctranslate2
        if ctranslate2.get_cuda_device_count() > 0:
            return "cuda"
    except (ImportError, RuntimeError):
        pass
    return "cpu"


def _compute_type_for(device: str) -> str:
    """Return the matching compute type for the given device.

    CUDA → float16 (fast, GPU-accelerated)
    CPU  → int8    (quantised, RAM-efficient)
    """
    return "float16" if device == "cuda" else "int8"


# ---------------------------------------------------------------------------
# Module-level model cache — loaded once, reused across videos
# ---------------------------------------------------------------------------

WHISPER_BEAM_SIZE = 5       # wider beam = more accurate, slightly slower
WHISPER_MODEL_DIR = "models/whisper"  # local download cache (gitignored)

# Cache keyed by (model_size, device) so switching devices reloads correctly
_model_cache: dict[tuple[str, str], WhisperModel] = {}


def _get_model(model_size: str, device: str) -> WhisperModel:
    """Return a cached WhisperModel, loading it only on first call per device.

    Models are stored under WHISPER_MODEL_DIR so you always know
    where they live and when they change.
    """
    key = (model_size, device)
    if key not in _model_cache:
        Path(WHISPER_MODEL_DIR).mkdir(parents=True, exist_ok=True)
        _model_cache[key] = WhisperModel(
            model_size,
            device=device,
            compute_type=_compute_type_for(device),
            download_root=WHISPER_MODEL_DIR,
        )
    return _model_cache[key]


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def extract_single_video(
    video_url: str,
    languages: list[str] | None = None,
    model_size: str = "small",
    device: str = "auto",
    output_dir: str = "data/raw/whisper",
    audio_dir: str = "data/audio",
) -> VideoData:
    """Extract transcript by downloading audio and transcribing locally.

    Args:
        video_url: Full YouTube watch URL.
        languages: Priority list for transcription, e.g. ['es', 'en'].
                   Defaults to ['es'].
        model_size: faster-whisper model size.
                    Options: tiny, base, small, medium, large-v3.
        device: Inference device. "auto" detects GPU/CPU, or "cpu" / "cuda".
        output_dir: Where to save the resulting JSON.
        audio_dir: Where to save the downloaded mp3.

    Returns:
        VideoData with transcript segments and metadata.
    """
    if languages is None:
        languages = ["es"]

    if device == "auto":
        device = _detect_device()

    info = _fetch_metadata(video_url)
    audio_path = _download_audio(video_url, output_dir=audio_dir)
    segments = _transcribe_audio(
        audio_path,
        language=languages[0],
        model_size=model_size,
        device=device,
    )
    return _build_videodata(info, segments)


def _transcribe_audio(
    audio_path: str | Path,
    language: str,
    model_size: str = "small",
    device: str = "auto",
) -> list[dict]:
    """Transcribe an audio file with faster-whisper.

    Returns a list of dicts in our standard shape:
        [{text, start, duration}, ...]

    faster-whisper returns start/end; we convert end → duration.
    """
    if device == "auto":
        device = _detect_device()

    model = _get_model(model_size, device)

    segments_out, _info = model.transcribe(
        str(audio_path),
        language=language,
        beam_size=WHISPER_BEAM_SIZE,
        vad_filter=True,
    )

    return [
        {
            "text": seg.text.strip(),
            "start": round(seg.start, 1),
            "duration": round(seg.end - seg.start, 1),
        }
        for seg in segments_out
    ]


# ---------------------------------------------------------------------------
# CLI entrypoint
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Extract transcript (audio + Whisper) + metadata from a YouTube video"
    )
    parser.add_argument("--url", required=True, help="YouTube video URL")
    parser.add_argument(
        "--lang",
        default="es",
        help="Language code for transcription (e.g. es, en, ca)",
    )
    parser.add_argument(
        "--model",
        default="small",
        help="faster-whisper model size: tiny, base, small, medium, large-v3",
    )
    parser.add_argument(
        "--device",
        default="auto",
        choices=["auto", "cpu", "cuda"],
        help="Inference device: auto (detect), cpu (Intel/Apple Silicon), cuda (NVIDIA GPU)",
    )
    parser.add_argument(
        "--output-dir",
        default="data/raw/whisper",
        help="Where to save the JSON output",
    )
    parser.add_argument(
        "--audio-dir",
        default="data/audio",
        help="Where to save the downloaded mp3",
    )
    args = parser.parse_args()

    data = extract_single_video(
        args.url,
        languages=[args.lang],
        model_size=args.model,
        device=args.device,
        output_dir=args.output_dir,
        audio_dir=args.audio_dir,
    )
    saved = data.save_json(output_dir=args.output_dir)
    print(f"Saved: {saved}")
    print(f"Title: {data.title}")
    print(f"Segments: {len(data.transcript_segments)}")
    print(f"Upload date: {data.metadata.get('upload_date')}")
    print(f"Duration: {data.metadata.get('duration')}s")
    print(f"First 200 chars:\n{data.full_text[:200]}")
