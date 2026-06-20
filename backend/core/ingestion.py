"""Shared ingestion core: VideoData model, metadata fetcher, audio downloader.

Used by both ingestion_caption.py and ingestion_audio.py.
Does NOT chunk, embed, or touch ChromaDB — that's processor.py's job.
"""

import json
from dataclasses import dataclass, field
from pathlib import Path

import yt_dlp


# ---------------------------------------------------------------------------
# VideoData — the single data contract across all ingestion strategies
# ---------------------------------------------------------------------------


@dataclass
class VideoData:
    """Structured result for one video.

    Every ingestion strategy (caption or audio) must return this exact shape
    so processor.py works without knowing the source.
    """

    video_id: str
    title: str
    description: str
    transcript_segments: list[dict]  # [{text, start, duration}, ...]
    full_text: str  # all segments concatenated, ready for chunking
    metadata: dict = field(default_factory=dict)  # raw yt-dlp output

    def enriched_text(self) -> str:
        """Return title, description, and timestamped segments as one string.

        Format:
            Title: {title}
            Description: {description}

            [MM:SS] segment text
            ...

        Timestamps use [HH:MM:SS] when the video duration is one hour or
        longer, otherwise [MM:SS].
        """
        duration = self.metadata.get("duration", 0) if self.metadata else 0
        if not duration and self.transcript_segments:
            duration = max(
                seg.get("start", 0) + seg.get("duration", 0)
                for seg in self.transcript_segments
            )
        use_hours = duration >= 3600

        lines = [f"Title: {self.title}", f"Description: {self.description}", ""]
        for seg in self.transcript_segments:
            start = seg.get("start", 0)
            text = seg.get("text", "")
            lines.append(f"{_format_timestamp(start, use_hours)} {text}")
        return "\n".join(lines)

    def to_dict(self) -> dict:
        """Serialize to plain dict for JSON export."""
        return {
            "video_id": self.video_id,
            "title": self.title,
            "description": self.description,
            "transcript_segments": self.transcript_segments,
            "full_text": self.full_text,
            "metadata": self.metadata,
        }

    def save_json(self, output_dir: str) -> Path:
        """Persist transcript + metadata as a JSON file.

        Args:
            output_dir: Directory to save into (e.g. 'data/raw/whisper').

        Returns the path to the saved file so callers can log or chain.
        """
        path = Path(output_dir)
        path.mkdir(parents=True, exist_ok=True)
        filepath = path / f"{self.video_id}.json"
        filepath.write_text(
            json.dumps(self.to_dict(), indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        return filepath 

    @classmethod
    def load_json(cls, filepath: str | Path) -> "VideoData":
        """Reconstruct VideoData from a previously saved JSON file.

        Useful as a cheap cache: if the JSON already exists, skip re-ingestion.
        """
        data = json.loads(Path(filepath).read_text(encoding="utf-8"))
        return cls(**data)


# ---------------------------------------------------------------------------
# Shared helpers — used by both strategies
# ---------------------------------------------------------------------------


def _format_timestamp(seconds: float, use_hours: bool) -> str:
    """Format a timestamp for enriched text segments.

    Args:
        seconds: Segment start time in seconds.
        use_hours: If True, render as [HH:MM:SS]; otherwise [MM:SS].

    Returns:
        Bracketed timestamp string ready to prefix a transcript segment.
    """
    secs = int(seconds)
    hours, rem = divmod(secs, 3600)
    mins, secs = divmod(rem, 60)
    if use_hours:
        return f"[{hours:02d}:{mins:02d}:{secs:02d}]"
    return f"[{mins:02d}:{secs:02d}]"


def _fetch_metadata(video_url: str) -> dict:
    """Get video metadata via yt-dlp (no download).

    Returns the full info dict: id, title, description, duration,
    upload_date, view_count, channel, and more.
    """
    ydl_opts = {"quiet": True, "skip_download": True}
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        return ydl.extract_info(video_url, download=False)


def _build_videodata(info: dict, segments: list[dict]) -> VideoData:
    """Construct a VideoData from yt-dlp info + transcript segments.

    Single factory so strategies don't repeat the same dict→VideoData mapping.
    Newly ingested videos store the enriched text (title, description, and
    timestamped segments) as full_text so downstream consumers get context
    without re-computing it.
    """
    vd = VideoData(
        video_id=info["id"],
        title=info.get("title", ""),
        description=info.get("description", ""),
        transcript_segments=segments,
        full_text="",
        metadata=info,
    )
    vd.full_text = vd.enriched_text()
    return vd


def _download_audio(video_url: str, output_dir: str = "data/audio") -> Path:
    """Download best audio from a single video, convert to mp3 via FFmpeg.

    Returns the path to the mp3 file.  Skips download if the file already
    exists (cache hit).  FFmpeg must be installed.
    """
    audio_dir = Path(output_dir)
    audio_dir.mkdir(parents=True, exist_ok=True)

    # Compute the expected output path so we can skip re-download
    info = _fetch_metadata(video_url)
    audio_path = audio_dir / f"{info['id']}.mp3"

    if audio_path.exists():
        return audio_path  # cache hit — no re-download

    # Cache miss — download and convert
    ydl_opts = {
        "format": "bestaudio/best",
        "outtmpl": str(audio_dir / "%(id)s.%(ext)s"),
        "noplaylist": True,
        "postprocessors": [
            {
                "key": "FFmpegExtractAudio",
                "preferredcodec": "mp3",
                "preferredquality": "192",
            }
        ],
        "quiet": True,
        "no_warnings": True,
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.extract_info(video_url, download=True)

    return audio_path

