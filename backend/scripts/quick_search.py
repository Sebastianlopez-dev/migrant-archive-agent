#!/usr/bin/env python3
"""
Quick chunk search — NO API CALLS. Works with existing ChromaDB.

Reads chunks by keyword or dumps all. Zero cost, zero rate limits.

Usage:
    source .venv/bin/activate
    python backend/scripts/quick_search.py              # show all chunks
    python backend/scripts/quick_search.py "FILMIG"      # keyword search
    python backend/scripts/quick_search.py --all          # full text dump
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "core"))

from core.vector_store import VectorStore

CHROMA_DIR = Path(__file__).resolve().parent.parent.parent / "data" / "chroma"


def show_chunks(store: VectorStore, keyword: str | None = None):
    """Retrieve and display chunks directly from ChromaDB — no embeddings."""
    result = store._collection.get(include=["documents", "metadatas"])
    documents = result.get("documents", [])
    metadatas = result.get("metadatas", [])
    ids = result.get("ids", [])

    matched = 0
    for i, doc in enumerate(documents):
        if keyword and keyword.lower() not in doc.lower():
            continue
        matched += 1
        meta = metadatas[i] if i < len(metadatas) else {}
        print(f"\n{'─' * 60}")
        print(f"  Chunk: {ids[i]}")
        print(f"  Video: {meta.get('title', '?')}")
        print(f"  Time:  {meta.get('start_time', 0):.0f}s → {meta.get('end_time', 0):.0f}s")
        print(f"{'─' * 60}")
        print(doc[:500])  # first 500 chars
        if len(doc) > 500:
            print(f"\n  ... ({len(doc) - 500} more chars)")

    if keyword:
        print(f"\n🔍 {matched} chunks matched '{keyword}' out of {len(documents)} total.")
    else:
        print(f"\n📄 {len(documents)} chunks total.")


def main():
    parser = argparse.ArgumentParser(description="Search ChromaDB chunks by keyword (no API)")
    parser.add_argument("query", nargs="?", default=None, help="Keyword to search for")
    parser.add_argument("--all", action="store_true", help="Show full text of all chunks")
    args = parser.parse_args()

    store = VectorStore(persist_dir=str(CHROMA_DIR))
    print(f"Collection: {store.count} chunks loaded.\n")

    if args.query:
        show_chunks(store, keyword=args.query)
    else:
        show_chunks(store)


if __name__ == "__main__":
    main()
