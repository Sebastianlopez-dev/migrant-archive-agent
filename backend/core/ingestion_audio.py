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

    Uses torch to probe (WhisperX backend).
    """
    try:
        import torch
        if torch.cuda.is_available():
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
# Public API
# ---------------------------------------------------------------------------

def extract_single_video(
    video_url: str,
    languages: list[str] | None = None,
    model_size: str = "small",
    device: str = "auto",
    output_dir: str = "data/raw/whisper",
    audio_dir: str = "data/audio",
    hf_token: str | None = None,
) -> VideoData:
    """Extract transcript by downloading audio and transcribing locally.

    Args:
        video_url: Full YouTube watch URL.
        languages: Priority list for transcription, e.g. ['es', 'en'].
                   Defaults to ['es'].
        model_size: Whisper model size.
                    Options: tiny, base, small, medium, large-v3.
        device: Inference device. "auto" detects GPU/CPU, or "cpu" / "cuda".
        output_dir: Where to save the resulting JSON.
        audio_dir: Where to save the downloaded mp3.
        hf_token: HuggingFace token for speaker diarisation (optional).

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
        hf_token=hf_token,
    )
    return _build_videodata(info, segments)


def _transcribe_audio(
    audio_path: str | Path,
    language: str,
    model_size: str = "small",
    device: str = "auto",
    hf_token: str | None = None,
) -> list[dict]:
    """Transcribe an audio file with faster-whisper.

    Returns a list of dicts in our standard shape:
        [{text, start, duration, speaker}, ...]

    The ``hf_token`` parameter is kept for backward compatibility but is no
    longer used; faster-whisper does not perform speaker diarisation.
    """
    if device == "auto":
        device = _detect_device()

    compute = _compute_type_for(device)
    audio_file = str(audio_path)

    model = WhisperModel(model_size, device=device, compute_type=compute)
    segments_iter, _info = model.transcribe(
        audio_file, language=language, beam_size=5
    )

    return [
        {
            "text": seg.text.strip(),
            "start": round(seg.start, 1),
            "duration": round(seg.end - seg.start, 1),
            "speaker": "UNKNOWN",
        }
        for seg in segments_iter
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
        help="Whisper model size: tiny, base, small, medium, large-v3",
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
    parser.add_argument(
        "--hf-token",
        default=None,
        help="HuggingFace token for speaker diarisation (optional)",
    )
    args = parser.parse_args()

    data = extract_single_video(
        args.url,
        languages=[args.lang],
        model_size=args.model,
        device=args.device,
        output_dir=args.output_dir,
        audio_dir=args.audio_dir,
        hf_token=args.hf_token,
    )
    saved = data.save_json(output_dir=args.output_dir)
    print(f"Saved: {saved}")
    print(f"Title: {data.title}")
    print(f"Segments: {len(data.transcript_segments)}")
    print(f"Upload date: {data.metadata.get('upload_date')}")
    print(f"Duration: {data.metadata.get('duration')}s")
    print(f"First 200 chars:\n{data.full_text[:200]}")
