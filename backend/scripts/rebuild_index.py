#!/usr/bin/env python3
"""
Rebuild Index — Chunk, embed, and store every whisper JSON into a fresh ChromaDB.

This script rebuilds the vector index from scratch. It deletes any existing
ChromaDB collection, then processes every ``.json`` file found in the raw
whisper directory and adds the resulting chunks + embeddings to the store.

Usage:
    python backend/scripts/rebuild_index.py
    python backend/scripts/rebuild_index.py --raw-dir data/raw/whisper/
    python backend/scripts/rebuild_index.py --chroma-dir data/chroma/
    python backend/scripts/rebuild_index.py --raw-dir data/raw/whisper/ --chroma-dir data/chroma/

Defaults:
    --raw-dir   data/raw/whisper/
    --chroma-dir data/chroma/

Requires:
    GEMINI_API_KEY in the environment (or .env file).
"""

import argparse
import os
import sys
from pathlib import Path

# Allow imports from backend/core without installing the package.
# backend/ enables `from core.X import ...`; backend/core/ enables
# `from X import ...` inside processor.py.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "core"))

from dotenv import load_dotenv

load_dotenv()

from core.embedding_gemini import GeminiEmbeddingProvider
from core.vector_store import VectorStore
from core.processor import Processor
from core.ingestion import VideoData

# ── constants ──────────────────────────────────────────────────────────────

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
DEFAULT_RAW_DIR = PROJECT_ROOT / "data" / "raw" / "whisper"
DEFAULT_CHROMA_DIR = PROJECT_ROOT / "data" / "chroma"

# ── helpers ────────────────────────────────────────────────────────────────


def find_video_files(raw_dir: Path) -> list[Path]:
    """Find all whisper JSON files waiting to be indexed."""
    if not raw_dir.exists():
        return []
    return sorted(raw_dir.glob("*.json"))


def build_index(provider: GeminiEmbeddingProvider, raw_dir: Path, chroma_dir: Path) -> VectorStore:
    """Chunk, embed, and store every whisper JSON into a fresh ChromaDB."""
    store = VectorStore(persist_dir=str(chroma_dir))
    store.delete_collection()
    # Re-create after delete — VectorStore.__init__ handles creation,
    # but delete_collection removes it. Re-init.
    store = VectorStore(persist_dir=str(chroma_dir))

    processor = Processor(provider, chunk_size=1000, overlap=200)
    video_files = find_video_files(raw_dir)

    if not video_files:
        print("No whisper JSON files found in", raw_dir)
        print("Run ingestion first: python backend/core/ingestion_audio.py <url>")
        sys.exit(1)

    total_chunks = 0
    for vf in video_files:
        print(f"Indexing: {vf.name}  ...", end=" ", flush=True)
        video_data = VideoData.load_json(vf)
        chunks, embeddings = processor.process(video_data)

        store.add(
            ids=[f"{video_data.video_id}_chunk_{c.metadata['chunk_index']}" for c in chunks],
            documents=[c.text for c in chunks],
            metadatas=[c.metadata for c in chunks],
            embeddings=embeddings,
        )
        total_chunks += len(chunks)
        print(f"{len(chunks)} chunks")

    print(f"\nIndexed {total_chunks} chunks from {len(video_files)} video(s) into ChromaDB.\n")
    return store


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Rebuild the ChromaDB vector index from whisper JSON files"
    )
    parser.add_argument(
        "--raw-dir",
        type=str,
        default=str(DEFAULT_RAW_DIR),
        help="Directory containing whisper JSON files (default: data/raw/whisper/)",
    )
    parser.add_argument(
        "--chroma-dir",
        type=str,
        default=str(DEFAULT_CHROMA_DIR),
        help="Directory where ChromaDB will persist the index (default: data/chroma/)",
    )
    return parser.parse_args(argv)


# ── main ───────────────────────────────────────────────────────────────────


def main():
    args = parse_args()

    if not os.getenv("GEMINI_API_KEY"):
        print("ERROR: GEMINI_API_KEY not set in .env")
        sys.exit(1)

    print("Initializing Gemini embedding provider ...")
    provider = GeminiEmbeddingProvider()

    raw_dir = Path(args.raw_dir)
    chroma_dir = Path(args.chroma_dir)

    print(f"Rebuilding index from {raw_dir} into {chroma_dir} ...\n")
    store = build_index(provider, raw_dir, chroma_dir)

    print(f"Collection size: {store.count} chunks")


if __name__ == "__main__":
    main()
