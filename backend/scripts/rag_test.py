#!/usr/bin/env python3
"""
RAG Test — Interactive vector DB query demo.

Usage:
    python backend/scripts/rag_test.py                # start interactive session
    python backend/scripts/rag_test.py --rebuild       # force re-index
    python backend/scripts/rag_test.py --top-k 5       # show 5 results

Workflow:
  1. Load or rebuild the ChromaDB index from processed video data
  2. Interactive prompt: type or paste a question
  3. Retrieved chunks are shown with similarity scores
  4. Type 'quit' or Ctrl+C to exit

For a live demo, copy-paste questions from notes/rag_test_questions.md
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

DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data"
RAW_DIR = DATA_DIR / "raw" / "whisper"
CHROMA_DIR = DATA_DIR / "chroma"

# ── helpers ────────────────────────────────────────────────────────────────


def find_video_files(raw_dir: Path) -> list[Path]:
    """Find all whisper JSON files waiting to be indexed."""
    if not raw_dir.exists():
        return []
    return sorted(raw_dir.glob("*.json"))


def build_index(provider: GeminiEmbeddingProvider) -> VectorStore:
    """Chunk, embed, and store every whisper JSON into a fresh ChromaDB."""
    store = VectorStore(persist_dir=str(CHROMA_DIR))
    store.delete_collection()
    # Re-create after delete — VectorStore.__init__ handles creation,
    # but delete_collection removes it. Re-init.
    store = VectorStore(persist_dir=str(CHROMA_DIR))

    processor = Processor(provider, chunk_size=1000, overlap=200)
    video_files = find_video_files(RAW_DIR)

    if not video_files:
        print("No whisper JSON files found in", RAW_DIR)
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


# ── main ───────────────────────────────────────────────────────────────────


def main():
    parser = argparse.ArgumentParser(description="Interactive RAG vector DB test")
    parser.add_argument("--rebuild", action="store_true", help="Force re-index all videos")
    parser.add_argument("--top-k", type=int, default=3, help="Number of chunks to retrieve (default: 3)")
    args = parser.parse_args()

    # Check API key
    if not os.getenv("GEMINI_API_KEY"):
        print("ERROR: GEMINI_API_KEY not set in .env")
        sys.exit(1)

    print("Initializing Gemini embedding provider ...")
    provider = GeminiEmbeddingProvider()

    # Load or rebuild index
    chroma_exists = CHROMA_DIR.exists() and any(CHROMA_DIR.iterdir())

    if args.rebuild or not chroma_exists:
        if args.rebuild:
            print("--rebuild flag set: re-indexing all videos ...\n")
        else:
            print("No existing ChromaDB found. Building index ...\n")
        store = build_index(provider)
    else:
        print(f"Using existing ChromaDB at {CHROMA_DIR}\n")
        store = VectorStore(persist_dir=str(CHROMA_DIR))

    print(f"Collection size: {store.count} chunks")
    print(f"Top-K: {args.top_k}")
    print("─" * 60)
    print("Paste or type a question. Type 'quit' to exit.")
    print("Pre-prepared questions: notes/rag_test_questions.md")
    print("─" * 60)

    # Interactive loop
    try:
        while True:
            print()
            query = input("Query> ").strip()
            if not query:
                continue
            if query.lower() in ("quit", "exit", "q"):
                print("Bye.")
                break

            print(f"Embedding query ({provider.dimension}d) ...", end=" ", flush=True)
            query_embedding = provider.embed_query(query)
            print("done.")

            print(f"Searching ChromaDB (top-{args.top_k}) ...", end=" ", flush=True)
            results = store.search(query_embedding, top_k=args.top_k)
            print(f"{len(results)} results.\n")
            print("─" * 60)

            for i, r in enumerate(results, 1):
                distance = r.get("distance", 0)
                similarity = 1 - distance if distance <= 1 else 0
                doc = r.get("document", "")[:300]
                meta = r.get("metadata", {})

                print(f"  #{i}  similarity: {similarity:.4f}  |  distance: {distance:.4f}")
                if meta:
                    chunk_idx = meta.get("chunk_index", "?")
                    print(f"       chunk {chunk_idx}  —  {doc}...")
                else:
                    print(f"       {doc}...")
                print()

            print("─" * 60)

    except KeyboardInterrupt:
        print("\nBye.")


if __name__ == "__main__":
    main()
