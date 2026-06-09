"""Caption-based ingestion: uses YouTube auto-generated captions.

Strategy: youtube-transcript-api → transcript segments.
Fast and free, no audio download or GPU needed.
Quality depends entirely on YouTube's built-in ASR — no punctuation,
lowercase-only, occasional garbled segments.
"""

import sys
from pathlib import Path

# Make sibling imports work regardless of where the script is invoked from
sys.path.insert(0, str(Path(__file__).parent))

from youtube_transcript_api import YouTubeTranscriptApi

from ingestion import VideoData, _build_videodata, _fetch_metadata


def extract_single_video(
    video_url: str,
    languages: list[str] | None = None,
    output_dir: str = "data/raw/captions",
) -> VideoData:
    """Extract transcript using YouTube's auto-captions.

    Args:
        video_url: Full YouTube watch URL.
        languages: Priority list, e.g. ['es', 'en']. Defaults to ['es', 'en'].

    Returns:
        VideoData with transcript segments and metadata.
    """
    if languages is None:
        languages = ["es", "en"]

    # Metadata (lightweight, no download) → shared helper in ingestion.py
    info = _fetch_metadata(video_url)

    # Transcript via YouTube's built-in ASR → requires youtube-transcript-api
    api = YouTubeTranscriptApi()
    fetched = api.fetch(info["id"], languages=languages)

    # Normalise to our standard dict shape so processor.py doesn't care
    segments = [
        {"text": s.text, "start": s.start, "duration": s.duration}
        for s in fetched
    ]
    return _build_videodata(info, segments)


# ---------------------------------------------------------------------------
# CLI entrypoint
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Extract transcript (captions) + metadata from a YouTube video"
    )
    parser.add_argument("--url", required=True, help="YouTube video URL")
    parser.add_argument(
        "--lang",
        nargs="*",
        default=["es", "en"],
        help="Language priority (e.g. --lang es en)",
    )
    parser.add_argument(
        "--output-dir",
        default="data/raw/captions",
        help="Where to save the JSON output",
    )
    args = parser.parse_args()

    data = extract_single_video(args.url, languages=args.lang, output_dir=args.output_dir)
    saved = data.save_json(output_dir=args.output_dir)
    print(f"Saved: {saved}")
    print(f"Title: {data.title}")
    print(f"Segments: {len(data.transcript_segments)}")
    print(f"Upload date: {data.metadata.get('upload_date')}")
    print(f"Duration: {data.metadata.get('duration')}s")
    print(f"First 200 chars:\n{data.full_text[:200]}")
