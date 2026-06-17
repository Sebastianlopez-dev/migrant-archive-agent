"""Colab-optimised ingestion: same logic as ingestion_audio.py, GPU defaults.

Use this from a Colab notebook or VSCode+Colab runtime.
Overrides defaults for GPU environment and Google Drive output paths.

Best for: videos > 5 minutes, batch processing a full channel,
or anytime you want large-v3 quality without waiting hours on CPU.

Requirements (run in Colab first):
    !pip install yt-dlp whisperx
    from google.colab import drive; drive.mount('/content/drive')
"""

import sys
from pathlib import Path

# Make sibling imports work — assumes this file lives in backend/core/
sys.path.insert(0, str(Path(__file__).parent))

# Import the local strategy unchanged
from ingestion_audio import extract_single_video  # noqa: E402

# ---------------------------------------------------------------------------
# Public API — same function, Colab-friendly defaults
# ---------------------------------------------------------------------------

# Google Drive mount point — set this ONCE at the top of your notebook
#   from google.colab import drive; drive.mount('/content/drive')
DRIVE_ROOT = "/content/drive/MyDrive"

# Separate folders for JSON output and downloaded audio
OUTPUT_DIR = f"{DRIVE_ROOT}/migrant-archive/output"   # JSON transcripts
AUDIO_DIR = f"{DRIVE_ROOT}/migrant-archive/audio"      # downloaded mp3s


def extract_single_video_colab(
    video_url: str,
    languages: list[str] | None = None,
    model_size: str = "large-v3",
    device: str = "cuda",
    output_dir: str = OUTPUT_DIR,
    audio_dir: str = AUDIO_DIR,
    hf_token: str | None = None,
):
    """Identical to ingestion_audio.extract_single_video, but defaults
    are tuned for Colab's free T4 GPU + Google Drive persistence."""
    return extract_single_video(
        video_url,
        languages=languages,
        model_size=model_size,
        device=device,
        output_dir=output_dir,
        audio_dir=audio_dir,
        hf_token=hf_token,
    )


# ---------------------------------------------------------------------------
# CLI entrypoint
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Extract transcript (Colab GPU + Whisper) from a YouTube video"
    )
    parser.add_argument("--url", required=True, help="YouTube video URL")
    parser.add_argument("--lang", default="es")
    parser.add_argument("--model", default="large-v3")
    parser.add_argument("--device", default="cuda", choices=["auto", "cpu", "cuda"])
    parser.add_argument(
        "--output-dir",
        default=OUTPUT_DIR,
        help="Drive path for JSON transcripts",
    )
    parser.add_argument(
        "--audio-dir",
        default=AUDIO_DIR,
        help="Drive path for downloaded mp3 files",
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
    print(f"First 200 chars:\n{data.full_text[:200]}")
