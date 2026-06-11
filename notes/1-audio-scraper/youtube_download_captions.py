#!/usr/bin/env python3

# This script downloads existing human-made captions (subtitles) from a single YouTube video
# and converts them into plain text for easy reuse (e.g., publishing on a blog).
#
# IMPORTANT:
# - This script is for videos that already HAVE captions.
# - If the video only has auto-generated captions, you can enable that with --allow-auto.
# - This script does NOT download audio.

# We import argparse to parse command-line arguments (video URL, language, output folder, etc.).
import argparse

# We import re for simple text cleanup and to detect timestamp lines.
import re

# We import sys to exit with a non-zero code on errors.
import sys

# We import Path to create and manipulate filesystem paths.
from pathlib import Path

# We import typing for optional types.
from typing import Optional

# We import yt_dlp (Python API) to download subtitle files.
import yt_dlp


# We define a small helper to "slugify" a title into a safe filename.
def slugify(text: str, max_len: int = 120) -> str:
    # We trim whitespace.
    text = text.strip()
    # We replace path separators to avoid accidental directories.
    text = text.replace("/", "-").replace("\\", "-")
    # We remove special characters that commonly break filenames.
    text = re.sub(r"[^a-zA-Z0-9._ -]+", "", text)
    # We collapse repeated spaces/dashes.
    text = re.sub(r"[ -]+", "-", text)
    # We ensure a non-empty result.
    return text[:max_len] if text else "untitled"


# We define a basic WebVTT-to-text converter (works for typical .vtt subtitle files).
def vtt_to_text(vtt_content: str) -> str:
    # We split the file into lines to process it line by line.
    lines = vtt_content.splitlines()

    # We prepare a list to collect only the spoken text lines.
    out_lines = []

    # We iterate through each line from the VTT file.
    for line in lines:
        # We strip whitespace so checks are simpler.
        line = line.strip()

        # We skip empty lines.
        if not line:
            continue

        # We skip the "WEBVTT" header.
        if line.upper().startswith("WEBVTT"):
            continue

        # We skip timestamp lines like "00:00:01.000 --> 00:00:04.000".
        if "-->" in line:
            continue

        # We skip cue settings lines (rare, but appear after timestamps sometimes).
        if re.match(r"^(align|position|size|line):", line, flags=re.IGNORECASE):
            continue

        # We remove basic HTML-like tags that sometimes appear in captions.
        line = re.sub(r"<[^>]+>", "", line)

        # We add the cleaned line to our output.
        out_lines.append(line)

    # We join lines and also collapse repeated spaces.
    text = "\n".join(out_lines)
    text = re.sub(r"[ \t]+", " ", text)

    # We return cleaned caption text.
    return text.strip() + "\n"


# We define the script's main entrypoint.
def main() -> int:
    # We create an argument parser for a friendly CLI.
    parser = argparse.ArgumentParser(
        description="Download captions from a YouTube video and convert them to plain text."
    )

    # We add the required positional argument for the video URL.
    parser.add_argument("url", help="YouTube video URL")

    # We allow choosing a subtitles language (e.g., en, es); default is English.
    parser.add_argument(
        "--lang",
        default="en",
        help="Subtitle language code to download (e.g., en, es, fr)",
    )

    # We allow choosing a root output directory (defaults to ./output).
    parser.add_argument(
        "--output-dir",
        default="output",
        help="Root output folder (captions/ subfolder will be created here)",
    )

    # We optionally allow auto-generated captions if human captions are missing.
    parser.add_argument(
        "--allow-auto",
        action="store_true",
        help="Allow auto-generated captions if human-made captions are not available",
    )

    # We parse the arguments.
    args = parser.parse_args()

    # We resolve the output directory to an absolute path.
    output_dir = Path(args.output_dir).expanduser().resolve()

    # We define a dedicated subfolder for captions.
    captions_dir = output_dir / "captions"

    # We create the captions directory (and parents) if it does not exist.
    captions_dir.mkdir(parents=True, exist_ok=True)

    # We configure yt-dlp to download subtitles without downloading the video itself.
    ydl_opts = {
        # We want subtitles (human) if available.
        "writesubtitles": True,
        # If user allows it, we also allow auto subs; otherwise keep it False.
        "writeautomaticsubs": bool(args.allow_auto),
        # We pick which languages we want.
        "subtitleslangs": [args.lang],
        # We use WebVTT because it is easy to parse.
        "subtitlesformat": "vtt",
        # We skip downloading video/audio payload.
        "skip_download": True,
        # We choose an output template (the .vtt extension is chosen by yt-dlp).
        "outtmpl": str(captions_dir / "%(id)s_%(title)s.%(ext)s"),
        # We reduce logs.
        "quiet": True,
        # We hide non-critical warnings.
        "no_warnings": True,
    }

    # We run yt-dlp to fetch metadata and subtitles.
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        # We extract info and perform the subtitle download (because download=True by default here).
        info = ydl.extract_info(args.url, download=True)

    # We compute the base filename we expect.
    video_id = info.get("id", "unknown_id")
    title = slugify(info.get("title", "untitled"))

    # yt-dlp usually writes subtitles as: "<template>.<lang>.vtt" (example: abc_title.en.vtt)
    vtt_path = captions_dir / f"{video_id}_{title}.{args.lang}.vtt"

    # If the expected file does not exist, we fail with a helpful error.
    if not vtt_path.exists():
        # We explain likely causes (no captions, wrong language, restricted video).
        print(
            "ERROR: Subtitle file not found.\n"
            f"Expected: {vtt_path}\n"
            "Possible reasons:\n"
            "- The video has no captions in that language\n"
            "- The captions are restricted/disabled\n"
            "- You need --allow-auto to download auto-generated captions\n",
            file=sys.stderr,
        )
        return 2

    # We read the VTT file as UTF-8 text.
    vtt_content = vtt_path.read_text(encoding="utf-8")

    # We convert VTT to plain text.
    captions_text = vtt_to_text(vtt_content)

    # We define the output .txt file path.
    txt_path = captions_dir / f"{video_id}_{title}.{args.lang}.txt"

    # We write the plain text captions to disk.
    txt_path.write_text(captions_text, encoding="utf-8")

    # We print a short success message showing where outputs are.
    print(f"Saved captions VTT: {vtt_path}")
    print(f"Saved captions TXT: {txt_path}")

    # We return 0 for success.
    return 0


# Standard entrypoint pattern.
if __name__ == "__main__":
    # We run main() and propagate its exit code.
    raise SystemExit(main())


