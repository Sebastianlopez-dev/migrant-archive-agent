#!/usr/bin/env python3
"""
RAG with query history — minimal memory demo.

One data structure: history = list of past searches.
Two commands: type a query, or type 'history'.

Usage:
    python backend/scripts/rag_memory.py
    python backend/scripts/rag_memory.py --top-k 5
    python backend/scripts/rag_memory.py --verbose    # full pipeline trace
"""

from __future__ import annotations

import argparse
import os
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "core"))

from dotenv import load_dotenv

load_dotenv()

from core.embedding_gemini import GeminiEmbeddingProvider
from core.vector_store import VectorStore

# ── constants ──────────────────────────────────────────────────────────────

CHROMA_DIR = Path(__file__).resolve().parent.parent.parent / "data" / "chroma"
MAX_HISTORY = 5

# ── memory ─────────────────────────────────────────────────────────────────


class SearchRecord:
    """One search saved in history."""

    def __init__(self, query: str, results: list[dict]):
        self.query = query
        self.result_count = len(results)
        self.video_ids: set[str] = set()
        for r in results:
            vid = r.get("metadata", {}).get("video_id")
            if vid:
                self.video_ids.add(vid)


class History:
    """Keeps the last MAX_HISTORY searches."""

    def __init__(self):
        self._searches: list[SearchRecord] = []

    def add(self, query: str, results: list[dict]) -> None:
        self._searches.append(SearchRecord(query, results))
        if len(self._searches) > MAX_HISTORY:
            self._searches.pop(0)

    def show(self) -> None:
        if not self._searches:
            print("No searches yet.")
            return
        print()
        for i, rec in enumerate(self._searches, 1):
            videos = ", ".join(sorted(rec.video_ids)) if rec.video_ids else "—"
            print(f"  [{i}] \"{rec.query}\"")
            print(f"       {rec.result_count} results  |  videos: {videos}")
            print()


# ── display ────────────────────────────────────────────────────────────────


def show_results(results: list[dict]) -> None:
    for i, r in enumerate(results, 1):
        distance = r.get("distance", 0)
        similarity = 1 - distance if distance <= 1 else 0
        doc = r.get("document", "")[:300]
        meta = r.get("metadata", {})
        vid = meta.get("video_id", "?")
        title = meta.get("title", vid)
        start = meta.get("start_time", "?")
        end = meta.get("end_time", "?")
        print(f"  #{i}  sim: {similarity:.4f}")
        print(f"       [{vid}] {title}  ({start}s..{end}s)")
        print(f"       {doc}{'...' if len(r.get('document', '')) > 300 else ''}")
        print()


# ── search ─────────────────────────────────────────────────────────────────


def search(provider, store, query: str, history: History, top_k: int) -> None:
    """Normal mode: minimal output."""
    print(f"Searching: \"{query}\" ...", end=" ", flush=True)
    embedding = provider.embed_query(query)
    results = store.search(embedding, top_k=top_k)
    print(f"{len(results)} results.\n")
    history.add(query, results)
    show_results(results)


def verbose_search(provider, store, query: str, history: History, top_k: int) -> None:
    """Verbose mode: full pipeline trace with timing and memory state."""

    bar = "─" * 60

    # ── Header ──────────────────────────────────────────────────────────
    print(f"\n  {bar}")
    print(f"  Input")
    print(f"    query:  \"{query[:80]}{'...' if len(query) > 80 else ''}\"  ({len(query)} chars)")
    print(f"    config: top_k={top_k}, MAX_HISTORY={MAX_HISTORY}")
    print(f"  {bar}")

    # ── Step 1: Embedding ───────────────────────────────────────────────
    print(f"  Step 1 — Embedding (Gemini API)")
    t0 = time.time()
    embedding = provider.embed_query(query)
    t_embed = time.time() - t0
    vector_sample = f"[{embedding[0]:.4f}, {embedding[1]:.4f}, {embedding[2]:.4f}, ..., {embedding[-1]:.4f}]"
    print(f"    model:  models/embedding-001")
    print(f"    dims:   {len(embedding)}")
    print(f"    vector: {vector_sample}")
    print(f"    time:   {t_embed:.2f}s")
    print(f"  {bar}")

    # ── Step 2: Vector Search ───────────────────────────────────────────
    print(f"  Step 2 — Vector Search (ChromaDB)")
    t0 = time.time()
    results = store.search(embedding, top_k=top_k)
    t_search = time.time() - t0
    print(f"    collection: {store.COLLECTION_NAME}")
    print(f"    total docs: {store.count}")
    print(f"    top_k:      {top_k}")
    print(f"    time:       {t_search:.2f}s")
    print(f"    results:")
    if results:
        for i, r in enumerate(results):
            dist = r.get("distance", 0)
            sim = 1 - dist if dist <= 1 else 0
            vid = r.get("metadata", {}).get("video_id", "?")
            chunk = r.get("metadata", {}).get("chunk_index", "?")
            print(f"      [{i}] sim={sim:.4f}  dist={dist:.4f}  |  {vid}  chunk {chunk}")
    else:
        print(f"      (none)")
    print(f"  {bar}")

    # ── Step 3: Memory Update ───────────────────────────────────────────
    print(f"  Step 3 — Memory Update (local)")
    was_full = len(history._searches) == MAX_HISTORY
    dropped_query = history._searches[0].query if was_full else None
    history.add(query, results)

    if was_full:
        print(f"    action:  pop \"{dropped_query[:50]}{'...' if len(dropped_query) > 50 else ''}\"  +  append new")
    else:
        print(f"    action:  append new")
    print(f"    buffer:  {len(history._searches)}/{MAX_HISTORY}")

    if len(history._searches) == MAX_HISTORY:
        next_drop = history._searches[0].query
        print(f"    status:  FULL — next drop: \"{next_drop[:50]}{'...' if len(next_drop) > 50 else ''}\"")
    print(f"  {bar}")

    # ── Summary ─────────────────────────────────────────────────────────
    print(f"  Total time: {t_embed + t_search:.2f}s  (embed: {t_embed:.2f}s  +  search: {t_search:.2f}s)")
    print()

    # ── Normal output ───────────────────────────────────────────────────
    show_results(results)


# ── main ───────────────────────────────────────────────────────────────────


def main():
    parser = argparse.ArgumentParser(description="RAG with query history")
    parser.add_argument("--top-k", type=int, default=3)
    parser.add_argument("--verbose", action="store_true", help="Full pipeline trace with timing and memory state")
    args = parser.parse_args()

    if not os.getenv("GEMINI_API_KEY"):
        print("ERROR: GEMINI_API_KEY not set in .env")
        sys.exit(1)

    if not CHROMA_DIR.exists() or not any(CHROMA_DIR.iterdir()):
        print("No ChromaDB found. Run first: python backend/scripts/rag_test.py --rebuild")
        sys.exit(1)

    print("Loading ...", end=" ", flush=True)
    provider = GeminiEmbeddingProvider()
    store = VectorStore(persist_dir=str(CHROMA_DIR))
    history = History()
    print(f"{store.count} chunks ready.\n")

    if args.verbose:
        print("VERBOSE mode — full pipeline trace enabled.\n")

    print("Type a query to search. 'history' to see past searches. 'quit' to exit.")
    print("=" * 60)

    do_search = verbose_search if args.verbose else search

    try:
        while True:
            raw = input("\n> ").strip()
            if not raw:
                continue
            if raw.lower() in ("quit", "exit", "q"):
                print("Bye.")
                break
            if raw.lower() == "history":
                history.show()
                continue
            do_search(provider, store, raw, history, args.top_k)

    except KeyboardInterrupt:
        print("\nBye.")


if __name__ == "__main__":
    main()
