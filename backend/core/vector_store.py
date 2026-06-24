"""Vector store: ChromaDB persistence layer.

Stores and retrieves document embeddings. Agnostic to the embedding
source — it just receives vectors and metadata.
"""

from __future__ import annotations

import chromadb
from chromadb.config import Settings


class VectorStore:
    """ChromaDB-backed vector store.

    Collection: "migrant_archive"
    Metadata: video_id, title, chunk_index, start_time, end_time
    """

    COLLECTION_NAME = "migrant_archive"

    def __init__(self, persist_dir: str = "data/chroma"):
        """Initialise ChromaDB client.

        Args:
            persist_dir: Directory for persistent storage.
                         Use ":memory:" for in-memory (testing).
        """
        is_memory = persist_dir == ":memory:"
        if is_memory:
            self._client = chromadb.Client(Settings(anonymized_telemetry=False))
        else:
            self._client = chromadb.PersistentClient(
                path=persist_dir,
                settings=Settings(anonymized_telemetry=False),
            )

        # Get or create the collection
        try:
            self._collection = self._client.get_collection(self.COLLECTION_NAME)
        except Exception:
            self._collection = self._client.create_collection(self.COLLECTION_NAME)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def add(
        self,
        ids: list[str],
        documents: list[str],
        metadatas: list[dict],
        embeddings: list[list[float]],
    ) -> None:
        """Add documents with embeddings and metadata to the store.

        Args:
            ids: Unique identifiers (e.g. "{video_id}_chunk_{index}").
            documents: Chunk text content.
            metadatas: Per-document metadata dicts.
            embeddings: Pre-computed embedding vectors.
        """
        self._collection.add(
            ids=ids,
            documents=documents,
            metadatas=metadatas,
            embeddings=embeddings,
        )

    def search(
        self,
        query_embedding: list[float],
        top_k: int = 5,
        video_id: str | None = None,
    ) -> list[dict]:
        """Semantic search for documents similar to query_embedding.

        Args:
            query_embedding: Embedding vector of the search query.
            top_k: Maximum number of results to return.
            video_id: If provided, restrict results to chunks from this video.

        Returns:
            List of dicts with keys: id, document, metadata, distance.
        """
        query_kwargs: dict = {
            "query_embeddings": [query_embedding],
            "n_results": top_k,
            "include": ["documents", "metadatas", "distances"],
        }
        if video_id is not None:
            query_kwargs["where"] = {"video_id": video_id}

        results = self._collection.query(**query_kwargs)

        # Flatten ChromaDB's nested-list response into a list of dicts
        documents = results.get("documents", [[]])[0]
        metadatas = results.get("metadatas", [[]])[0]
        distances = results.get("distances", [[]])[0]
        ids = results.get("ids", [[]])[0]

        output: list[dict] = []
        for i in range(len(ids)):
            output.append({
                "id": ids[i],
                "document": documents[i] if i < len(documents) else "",
                "metadata": metadatas[i] if i < len(metadatas) else {},
                "distance": distances[i] if i < len(distances) else 0.0,
            })
        return output

    def get_unique_videos(self) -> list[dict]:
        """Return every video_id in the collection with its chunk count.

        Returns:
            List of dicts with keys: video_id, title, chunk_count.
            Title is taken from chunk metadata when available.
        """
        if self._collection.count() == 0:
            return []

        results = self._collection.get(include=["metadatas"])
        metadatas = results.get("metadatas", [])
        if not metadatas:
            return []

        counts: dict[str, int] = {}
        titles: dict[str, str] = {}
        for meta in metadatas:
            vid = meta.get("video_id")
            if not vid:
                continue
            counts[vid] = counts.get(vid, 0) + 1
            if vid not in titles:
                titles[vid] = meta.get("title", "")

        return [
            {
                "video_id": vid,
                "title": titles.get(vid, ""),
                "chunk_count": count,
            }
            for vid, count in sorted(counts.items())
        ]

    def delete_collection(self) -> None:
        """Delete the entire collection (reset)."""
        self._client.delete_collection(self.COLLECTION_NAME)
        # Re-create empty collection so the store stays usable
        self._collection = self._client.create_collection(self.COLLECTION_NAME)

    @property
    def count(self) -> int:
        """Number of documents in the collection."""
        return self._collection.count()
