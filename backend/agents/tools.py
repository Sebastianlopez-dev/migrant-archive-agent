"""LangChain tools for the migrant-archive agent.

The main tool is `search_transcripts`, which embeds a user query and
retrieves relevant transcript chunks from the ChromaDB-backed VectorStore.
"""

from __future__ import annotations

from langchain_core.tools import tool


def make_search_transcripts(provider, store, top_k: int = 3):
    """Create a configured search_transcripts tool.

    Args:
        provider: EmbeddingProvider with embed_query(text) -> list[float].
        store: VectorStore with search(query_embedding, top_k) -> list[dict].
        top_k: Maximum number of chunks to retrieve.

    Returns:
        A LangChain tool callable.
    """

    @tool
    def search_transcripts(query: str) -> str:
        """Search archived video transcripts for a given query."""
        if store.count == 0:
            return "No hay transcripciones indexadas aún."

        embedding = provider.embed_query(query)
        results = store.search(embedding, top_k=top_k)

        if not results:
            return "No se encontraron resultados relevantes."

        blocks: list[str] = []
        for i, result in enumerate(results, start=1):
            metadata = result.get("metadata", {})
            title = metadata.get("title", metadata.get("video_id", "Desconocido"))
            start = metadata.get("start_time", "?")
            end = metadata.get("end_time", "?")
            document = result.get("document", "")
            blocks.append(
                f"[{i}] {title} ({start}–{end})\n{document}"
            )

        return "\n\n".join(blocks)

    return search_transcripts
