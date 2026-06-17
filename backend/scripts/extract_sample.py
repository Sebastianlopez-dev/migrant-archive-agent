#!/usr/bin/env python3
"""
Sample Extractor — First 5K from ChromaDB & JSON sources.

Extracts the first N characters of stored video data from two backends:
  - ChromaDB  → reads chunks sequentially from the vector store
  - JSON       → reads raw transcription files directly

Useful for:
  - Checkpoint demos: prove data is stored and retrievable
  - Quick content inspection: see what's in the vector DB without a query
  - Data validation: compare JSON source vs ChromaDB chunks side by side

Usage:
    python backend/scripts/extract_sample.py                     # both sources, 5000 chars
    python backend/scripts/extract_sample.py --source chroma     # ChromaDB only
    python backend/scripts/extract_sample.py --source json       # JSON files only
    python backend/scripts/extract_sample.py --chars 2000        # custom char limit

Output:
    ── ChromaDB (first ~5000 chars from 4 chunks)
    ── JSON (first ~5000 chars from 1 file)
"""

import argparse
import os
import sys
from pathlib import Path

# Allow imports from backend/core without installing the package
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dotenv import load_dotenv

load_dotenv()

from core.vector_store import VectorStore
from core.ingestion import VideoData

# ── constants ──────────────────────────────────────────────────────────────

DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data"
RAW_WHISPER_DIR = DATA_DIR / "raw" / "whisper"
RAW_CAPTIONS_DIR = DATA_DIR / "raw" / "captions"
CHROMA_DIR = DATA_DIR / "chroma"

SEPARATOR = "─" * 60


# ── JSON extraction ────────────────────────────────────────────────────────


def extract_from_json(
    raw_dir: Path, char_limit: int = 5000
) -> dict | None:
    """Read the first available JSON file and return its first `char_limit` chars.

    Returns a dict with keys: source, title, video_id, char_count, preview, file_path.
    Returns None if no JSON files are found.
    """
    json_files = sorted(raw_dir.glob("*.json")) if raw_dir.exists() else []

    if not json_files:
        return None

    file_path = json_files[0]
    video = VideoData.load_json(file_path)
    full_text = video.full_text[:char_limit]

    return {
        "source": f"JSON ({raw_dir.name})",
        "title": video.title,
        "video_id": video.video_id,
        "char_count": min(char_limit, len(video.full_text)),
        "total_chars": len(video.full_text),
        "preview": full_text,
        "file_path": str(file_path),
    }


# ── ChromaDB extraction ────────────────────────────────────────────────────


def extract_from_chroma(char_limit: int = 5000) -> dict | None:
    """Read chunks from ChromaDB sequentially until `char_limit` is reached.

    Since ChromaDB doesn't support offset-based iteration natively,
    we use a semantic search with a neutral query and collect results.
    For a pure sequential read, we iterate the collection via `get()`.

    Returns a dict with keys: source, chunk_count, total_chunks, char_count, preview.
    Returns None if ChromaDB is empty or doesn't exist.
    """
    if not CHROMA_DIR.exists() or not any(CHROMA_DIR.iterdir()):
        return None

    store = VectorStore(persist_dir=str(CHROMA_DIR))

    if store.count == 0:
        return None

    # Get all documents from the collection (sequential read)
    all_data = store._collection.get(
        include=["documents", "metadatas"],
    )

    documents = all_data.get("documents", [])
    metadatas = all_data.get("metadatas", [])

    if not documents:
        return None

    # Accumulate chunks until we reach the character limit
    accumulated = ""
    chunk_count = 0
    titles_seen: set[str] = set()

    for doc, meta in zip(documents, metadatas):
        accumulated += doc + "\n\n"
        chunk_count += 1
        if meta and "title" in meta:
            titles_seen.add(meta["title"])
        if len(accumulated) >= char_limit:
            break

    return {
        "source": "ChromaDB",
        "chunk_count": chunk_count,
        "total_chunks": len(documents),
        "char_count": min(char_limit, len(accumulated)),
        "total_chars": len(accumulated),
        "titles": sorted(titles_seen),
        "preview": accumulated[:char_limit],
    }


# ── display helpers ────────────────────────────────────────────────────────


def print_json_result(result: dict, char_limit: int) -> None:
    """Pretty-print a JSON extraction result."""
    print(SEPARATOR)
    print(f"Source:      {result['source']}")
    print(f"File:        {result['file_path']}")
    print(f"Video:       {result['title']}")
    print(f"Video ID:    {result['video_id']}")
    print(
        f"Characters:  {result['char_count']:,} shown "
        f"(of {result['total_chars']:,} total)"
    )
    print(SEPARATOR)
    print(result["preview"])
    print(SEPARATOR)


def print_chroma_result(result: dict, char_limit: int) -> None:
    """Pretty-print a ChromaDB extraction result."""
    print(SEPARATOR)
    print(f"Source:       {result['source']}")
    print(f"Chunks used:  {result['chunk_count']} (of {result['total_chunks']} total)")
    print(f"Videos:       {', '.join(result['titles']) if result['titles'] else '(unknown)'}")
    print(
        f"Characters:   {result['char_count']:,} shown "
        f"(of {result['total_chars']:,} in selected chunks)"
    )
    print(SEPARATOR)
    print(result["preview"])
    print(SEPARATOR)


# ── main ───────────────────────────────────────────────────────────────────


def main():
    parser = argparse.ArgumentParser(
        description="Extract first N characters from ChromaDB and/or JSON sources"
    )
    parser.add_argument(
        "--source",
        choices=["chroma", "json", "both"],
        default="both",
        help="Which data source to extract from (default: both)",
    )
    parser.add_argument(
        "--chars",
        type=int,
        default=5000,
        help="Number of characters to extract (default: 5000)",
    )
    parser.add_argument(
        "--raw-dir",
        type=str,
        default=None,
        help="Override the JSON source directory (default: data/raw/whisper)",
    )
    args = parser.parse_args()

    char_limit = args.chars

    # ── JSON extraction ──────────────────────────────────────────────────

    if args.source in ("json", "both"):
        raw_dir = Path(args.raw_dir) if args.raw_dir else RAW_WHISPER_DIR

        # Fall back to captions if whisper doesn't have files
        if not (raw_dir.exists() and list(raw_dir.glob("*.json"))):
            if RAW_CAPTIONS_DIR.exists() and list(RAW_CAPTIONS_DIR.glob("*.json")):
                raw_dir = RAW_CAPTIONS_DIR

        json_result = extract_from_json(raw_dir, char_limit)

        if json_result:
            print(f"\n{' JSON Source '.center(60, '=')}\n")
            print_json_result(json_result, char_limit)
        else:
            print(f"\n⚠️  No JSON files found in {raw_dir}")
            print("   Run ingestion first: python backend/core/ingestion_audio.py <url>\n")

    # ── ChromaDB extraction ──────────────────────────────────────────────

    if args.source in ("chroma", "both"):
        chroma_result = extract_from_chroma(char_limit)

        if chroma_result:
            print(f"\n{' ChromaDB Source '.center(60, '=')}\n")
            print_chroma_result(chroma_result, char_limit)
        else:
            print(f"\n⚠️  ChromaDB is empty or doesn't exist at {CHROMA_DIR}")
            print("   Build the index first: python backend/scripts/rag_test.py --rebuild\n")


if __name__ == "__main__":
    main()
