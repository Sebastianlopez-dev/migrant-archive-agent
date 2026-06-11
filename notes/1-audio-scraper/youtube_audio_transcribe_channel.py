#!/usr/bin/env python3

# This script downloads the best available audio from every video in a YouTube channel
# (or playlist) and then transcribes the downloaded audio into blog-ready text.
#
# IMPORTANT:
# - You need FFmpeg installed (yt-dlp uses it to extract/convert audio).
# - You need the "openai-whisper" Python package for local transcription.
# - For large channels, this can take a long time (downloads + transcription).

# We import argparse to parse command-line arguments (URLs, output folder, etc.).
import argparse

# We import os for working with filesystem paths and environment variables.
import os

# We import re to sanitize titles into safe filenames.
import re

# We import sys to exit with a non-zero code on errors.
import sys

# We import Path to create and manipulate filesystem paths in a cross-platform way.
from pathlib import Path

# We import typing helpers for clearer code (not required, but helps readability).
from typing import Iterable, Optional

# We import yt_dlp (the Python API for yt-dlp) to discover videos and download audio.
import yt_dlp

# We import whisper (OpenAI Whisper open-source) to transcribe audio locally.
import whisper


# We define a small helper that converts an arbitrary string into a safe filename.
def slugify(text: str, max_len: int = 120) -> str:
    # We strip leading/trailing whitespace to keep names tidy.
    text = text.strip()
    # We replace path separators just in case (avoid nested/unexpected paths).
    text = text.replace("/", "-").replace("\\", "-")
    # We remove characters that are risky in filenames on common OSes.
    text = re.sub(r"[^a-zA-Z0-9._ -]+", "", text)
    # We collapse repeated spaces/dashes into a single dash for readability.
    text = re.sub(r"[ -]+", "-", text)
    # We trim the filename to a reasonable length.
    return text[:max_len] if text else "untitled"


# We define a helper that yields video entries (each entry is a dict) from a channel/playlist URL.
def iter_channel_videos(channel_or_playlist_url: str) -> Iterable[dict]:
    # We configure yt-dlp to "extract" metadata without downloading files yet.
    ydl_opts = {
        # "extract_flat" tells yt-dlp to list entries quickly (no deep extraction per video yet).
        "extract_flat": True,
        # "skip_download" ensures we do not download during the listing phase.
        "skip_download": True,
        # "quiet" reduces yt-dlp log noise; we will print our own progress lines.
        "quiet": True,
    }

    # We create a YoutubeDL instance with the options above.
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        # We extract info from the channel/playlist URL (returns a dict describing the page).
        info = ydl.extract_info(channel_or_playlist_url, download=False)

    # Some URLs return a single video instead of a playlist; normalize to a list of entries.
    entries = info.get("entries") if isinstance(info, dict) else None

    # If entries is missing, treat the "info" as a single-entry iterable.
    if not entries:
        # We yield the single video-like dict.
        yield info
        # We stop here.
        return

    # We iterate through the flattened entries in the channel/playlist listing.
    for entry in entries:
        # We skip empty items that yt-dlp sometimes produces.
        if not entry:
            continue
        # We yield each entry dict to the caller.
        yield entry


# We define a helper that downloads audio for one video URL and returns the audio file path.
def download_audio(video_url: str, audio_dir: Path) -> Path:
    # We ensure the target audio directory exists (create parents if needed).
    audio_dir.mkdir(parents=True, exist_ok=True)

    # We configure yt-dlp to download best audio and convert it to mp3 via FFmpeg.
    ydl_opts = {
        # "bestaudio/best" picks the best available audio-only format.
        "format": "bestaudio/best",
        # "outtmpl" controls the output filename template (we keep youtube's ID to avoid collisions).
        "outtmpl": str(audio_dir / "%(id)s_%(title)s.%(ext)s"),
        # "noplaylist" forces yt-dlp to treat the URL as a single video.
        "noplaylist": True,
        # "postprocessors" tells yt-dlp to run FFmpeg to extract/convert audio.
        "postprocessors": [
            {
                # This postprocessor extracts audio using FFmpeg.
                "key": "FFmpegExtractAudio",
                # We choose mp3 because it is widely supported by transcription tools and editors.
                "preferredcodec": "mp3",
                # We choose a reasonable bitrate; you can increase for quality, at the cost of size.
                "preferredquality": "192",
            }
        ],
        # "quiet" reduces internal logs.
        "quiet": True,
        # "no_warnings" hides non-critical warnings.
        "no_warnings": True,
    }

    # We create a YoutubeDL instance configured for audio download.
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        # We extract info AND download (because download=True is the default in download()).
        info = ydl.extract_info(video_url, download=True)

    # We compute the expected final filename produced by the postprocessor (mp3).
    video_id = info.get("id", "unknown_id")
    title = slugify(info.get("title", "untitled"))
    audio_path = audio_dir / f"{video_id}_{title}.mp3"

    # We return the path where the mp3 should exist after yt-dlp finishes.
    return audio_path


# We define a helper that transcribes one audio file and writes the transcript to disk.
def transcribe_audio(
    model: whisper.Whisper,
    audio_path: Path,
    transcript_dir: Path,
    language: Optional[str],
    save_srt: bool,
) -> Path:
    # We ensure the transcript output folder exists.
    transcript_dir.mkdir(parents=True, exist_ok=True)

    # We create a transcript filename that matches the audio filename (but with .txt extension).
    transcript_txt_path = transcript_dir / (audio_path.stem + ".txt")

    # We run Whisper transcription; setting language can improve accuracy and speed.
    result = model.transcribe(str(audio_path), language=language)

    # We write the plain transcript text to a UTF-8 file (good default for blogs).
    transcript_txt_path.write_text(result.get("text", "").strip() + "\n", encoding="utf-8")

    # If the user asked for SRT, we also write a simple subtitle file with timestamps.
    if save_srt:
        # We build the SRT file path.
        transcript_srt_path = transcript_dir / (audio_path.stem + ".srt")
        # We open the file for writing.
        with transcript_srt_path.open("w", encoding="utf-8") as f:
            # We iterate through Whisper's segment list (each segment has start/end/text).
            for i, seg in enumerate(result.get("segments", []), start=1):
                # We define a small helper to format seconds to SRT timestamp format.
                def fmt_srt_time(seconds: float) -> str:
                    # We convert seconds to milliseconds.
                    ms = int(seconds * 1000)
                    # We compute hours.
                    h = ms // 3_600_000
                    # We compute remaining minutes.
                    m = (ms % 3_600_000) // 60_000
                    # We compute remaining seconds.
                    s = (ms % 60_000) // 1000
                    # We compute remaining milliseconds.
                    ms2 = ms % 1000
                    # We return formatted time as HH:MM:SS,mmm.
                    return f"{h:02d}:{m:02d}:{s:02d},{ms2:03d}"

                # We write the SRT index number.
                f.write(f"{i}\n")
                # We write the time range line.
                f.write(f"{fmt_srt_time(seg['start'])} --> {fmt_srt_time(seg['end'])}\n")
                # We write the caption text.
                f.write(seg.get("text", "").strip() + "\n\n")

    # We return the path to the blog-ready .txt transcript.
    return transcript_txt_path


# We define the CLI entrypoint that wires together listing, downloading, and transcription.
def main() -> int:
    # We build an argument parser so the script is easy to run from terminal.
    parser = argparse.ArgumentParser(
        description="Download audio from a YouTube channel/playlist and transcribe it with Whisper."
    )

    # We add the required positional argument for the channel/playlist URL.
    parser.add_argument("url", help="YouTube channel URL or playlist URL")

    # We allow choosing an output directory (defaults to ./output next to where you run the script).
    parser.add_argument(
        "--output-dir",
        default="output",
        help="Root output folder (audio/ and transcripts/ subfolders will be created here)",
    )

    # We allow limiting how many videos to process (useful for testing).
    parser.add_argument(
        "--limit",
        type=int,
        default=0,
        help="Process only the first N videos (0 = no limit)",
    )

    # We allow selecting the Whisper model size (tiny/base/small/medium/large).
    parser.add_argument(
        "--whisper-model",
        default="small",
        help="Whisper model name (tiny, base, small, medium, large). Bigger is slower but often more accurate.",
    )

    # We allow providing an explicit language code (e.g., en, es); empty means auto-detect.
    parser.add_argument(
        "--language",
        default="",
        help="Optional language code for transcription (e.g., en, es). Leave empty for auto-detect.",
    )

    # We allow producing an additional SRT file with timestamps (helpful for editing).
    parser.add_argument(
        "--save-srt",
        action="store_true",
        help="Also save .srt subtitles next to the .txt transcript",
    )

    # We parse the arguments from sys.argv.
    args = parser.parse_args()

    # We resolve the output directory to an absolute path.
    output_dir = Path(args.output_dir).expanduser().resolve()

    # We define subfolders for audio and transcripts, inside the root output folder.
    audio_dir = output_dir / "audio"
    transcript_dir = output_dir / "transcripts"

    # We create the root output folder up-front (and also the subfolders later).
    output_dir.mkdir(parents=True, exist_ok=True)

    # We normalize the language option so that "" becomes None.
    language = args.language.strip() or None

    # We load the Whisper model once (loading it per video would be very slow).
    model = whisper.load_model(args.whisper_model)

    # We iterate through discovered videos from the channel/playlist.
    processed = 0
    for entry in iter_channel_videos(args.url):
        # We respect the --limit option if the user set it.
        if args.limit and processed >= args.limit:
            break

        # We obtain a usable video URL (yt-dlp provides one of these fields).
        video_url = entry.get("url") or entry.get("webpage_url")

        # If yt-dlp provided only an ID, we convert it to a full YouTube watch URL.
        if video_url and not video_url.startswith("http"):
            video_url = f"https://www.youtube.com/watch?v={video_url}"

        # If we still cannot determine a URL, we skip this entry.
        if not video_url:
            continue

        # We print progress to the terminal so you know what is happening.
        title = entry.get("title", "unknown title")
        print(f"\n[1/2] Downloading audio: {title}")

        # We download the audio for this video.
        audio_path = download_audio(video_url, audio_dir)

        # We verify the audio file exists; if not, we stop with an error.
        if not audio_path.exists():
            print(f"ERROR: Expected audio file not found: {audio_path}", file=sys.stderr)
            return 2

        # We print the next step.
        print(f"[2/2] Transcribing audio: {audio_path.name}")

        # We run transcription and save the transcript text.
        transcript_path = transcribe_audio(
            model=model,
            audio_path=audio_path,
            transcript_dir=transcript_dir,
            language=language,
            save_srt=args.save_srt,
        )

        # We report where the transcript was written.
        print(f"Saved transcript: {transcript_path}")

        # We increment the counter after successful processing.
        processed += 1

    # We print a final summary.
    print(f"\nDone. Processed {processed} video(s). Output folder: {output_dir}")

    # We return 0 to indicate success.
    return 0


# This is the standard Python pattern to run main() only when executed as a script.
if __name__ == "__main__":
    # We call main() and exit with its return code.
    raise SystemExit(main())

