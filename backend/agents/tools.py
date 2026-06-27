"""LangChain tools for the migrant-archive agent.

Tools:
  - search_transcripts: semantic search over transcript text stored in ChromaDB.
  - list_videos: catalog of indexed videos with optional filters.
  - get_video_info: detailed metadata for a single video.
"""

from __future__ import annotations

from langchain_core.tools import tool

from core.embedding import EmbeddingProvider
from core.vector_store import VectorStore


def make_search_transcripts(
    provider: EmbeddingProvider, store: VectorStore, top_k: int = 3
):
    """Create a configured search_transcripts tool.

    Use this tool when the user asks about *content* inside the videos
    (what was said, topics, quotes). For browsing or discovering which
    videos exist, use list_videos first.

    Args:
        provider: EmbeddingProvider with embed_query(text) -> list[float].
        store: VectorStore with search(query_embedding, top_k) -> list[dict].
        top_k: Maximum number of chunks to retrieve.

    Returns:
        A LangChain tool callable.
    """

    @tool
    def search_transcripts(
        query: str,
        video_id: str | None = None,
        year: int | None = None,
        channel: str | None = None,
    ) -> str:
        """Search archived video transcripts using semantic similarity.

        Best for finding what was *said* inside the videos. If you need to
        browse available videos or discover video_ids, use list_videos first.

        Args:
            query: Search query in natural language.
            video_id: Optional video ID to restrict the search to.
            year: Optional upload year to filter results.
            channel: Optional channel name to filter results.
        """
        if store.count == 0:
            return "No hay transcripciones indexadas aun."

        embedding = provider.embed_query(query)
        results = store.search(
            embedding,
            top_k=top_k,
            video_id=video_id,
            year=year,
            channel=channel,
        )

        if not results:
            return "No se encontraron resultados relevantes."

        blocks: list[str] = []
        seen_videos: set[str] = set()
        for i, result in enumerate(results, start=1):
            metadata = result.get("metadata", {})
            result_video_id = metadata.get("video_id", "desconocido")
            title = metadata.get("title", result_video_id)
            speaker = metadata.get("speaker")
            start = metadata.get("start_time", "?")
            end = metadata.get("end_time", "?")
            document = result.get("document", "")

            seen_videos.add(result_video_id)

            header = f"{result_video_id} | {title}"
            if speaker:
                header += f" [{speaker}]"
            header += f" ({start}–{end})"

            blocks.append(f"[{i}] {header}\n{document}")

        summary = f"---\n{len(results)} chunk(s) from {len(seen_videos)} video(s)"
        blocks.append(summary)

        return "\n\n".join(blocks)

    return search_transcripts


def _matches_filters(
    entry: dict,
    year: int | None,
    channel: str | None,
    speaker: str | None,
) -> bool:
    """Return True if entry passes all provided filters."""
    if year is not None and entry.get("year") != year:
        return False
    if channel is not None:
        entry_channel = entry.get("channel") or "unknown"
        if channel.lower() != entry_channel.lower():
            return False
    if speaker is not None:
        speaker_lower = speaker.lower()
        entry_channel = (entry.get("channel") or "").lower()
        entry_speakers = (entry.get("speaker") or "").lower()
        if speaker_lower not in entry_channel and speaker_lower not in entry_speakers:
            return False
    return True


def make_list_videos(store: VectorStore):
    """Create a configured list_videos tool.

    Args:
        store: VectorStore with get_unique_videos() and get_video_metadata().

    Returns:
        A LangChain tool callable.
    """

    @tool
    def list_videos(
        year: int | None = None,
        speaker: str | None = None,
        channel: str | None = None,
    ) -> str:
        """Return the catalog of indexed videos.

        Use this tool first to discover available video_ids before calling
        get_video_info or search_transcripts on a specific video.

        Args:
            year: Filter by upload year.
            speaker: Filter by speaker name (matches channel or speaker field).
            channel: Filter by exact channel name (case-insensitive).
        """
        catalog = store.get_unique_videos()
        if not catalog:
            return "No hay videos indexados aun."

        enriched: list[dict] = []
        for entry in catalog:
            video_id = entry["video_id"]
            store_meta = store.get_video_metadata(video_id) or {}

            enriched_entry: dict[str, object] = {
                "video_id": video_id,
                "title": entry.get("title", video_id),
                "year": store_meta.get("year"),
                "channel": store_meta.get("channel") or "unknown",
                "speaker": store_meta.get("speaker") or "",
                "chunk_count": entry.get("chunk_count", 0),
                "duration": store_meta.get("duration"),
            }

            if _matches_filters(enriched_entry, year, channel, speaker):
                enriched.append(enriched_entry)

        if not enriched:
            return "No se encontraron videos que coincidan con los filtros."

        lines: list[str] = []
        for i, item in enumerate(enriched, start=1):
            line = f"{i}. {item['video_id']} | {item['title']}"
            if item.get("year"):
                line += f" ({item['year']})"
            if item.get("channel") and item["channel"] != "unknown":
                line += f" - {item['channel']}"
            if item.get("speaker"):
                line += f" [{item['speaker']}]"
            line += f" - {item['chunk_count']} chunk(s)"
            if item.get("duration"):
                line += f" - {item['duration']}s"
            lines.append(line)

        lines.append(f"---\n{len(enriched)} video(s)")
        return "\n".join(lines)

    return list_videos


def make_get_video_info(store: VectorStore):
    """Create a configured get_video_info tool.

    Args:
        store: VectorStore with get_video_metadata().

    Returns:
        A LangChain tool callable.
    """

    @tool
    def get_video_info(video_id: str) -> str:
        """Return metadata for a single video.

        Use list_videos first to discover valid video_ids.

        Args:
            video_id: The video identifier.
        """
        store_meta = store.get_video_metadata(video_id)
        if store_meta is None:
            return f"Video '{video_id}' no encontrado."

        lines: list[str] = [
            f"ID: {video_id}",
            f"Title: {store_meta.get('title') or 'N/A'}",
            f"Year: {store_meta.get('year') or 'N/A'}",
            f"Channel: {store_meta.get('channel') or 'unknown'}",
            f"Chunks: {store_meta.get('chunk_count', 0)}",
        ]

        duration = store_meta.get("duration")
        if duration is not None:
            lines.append(f"Duration: {duration}s")

        speakers = store_meta.get("speaker")
        if speakers:
            lines.append(f"Speaker(s): {speakers}")

        return "\n".join(lines)

    return get_video_info
