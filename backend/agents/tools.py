"""LangChain tools for the migrant-archive agent.

Tools:
  - search_transcripts: semantic search over transcript text stored in ChromaDB.
  - list_videos: catalog of indexed videos with optional filters.
  - get_video_info: detailed metadata for a single video.

All factories receive a langchain_chroma.Chroma instance and return a
@tool-decorated function. There are no dependencies on backend/core/.
"""

from __future__ import annotations

import re

from langchain_core.documents import Document
from langchain_core.tools import tool


def make_search_transcripts(store, top_k: int = 3):
    """Create a search_transcripts tool using Chroma's built-in retriever."""

    @tool
    def search_transcripts(
        query: str,
        video_id: str | None = None,
        year: int | None = None,
        channel: str | None = None,
    ) -> str:
        """Search transcript text for ANY topic, feeling, person, or theme.

        Always call this tool first when the user asks about content,
        experiences, emotions, or what was said inside the videos. If
        results are empty, try rephrasing the query with different keywords
        or check list_videos to see available video_ids.

        Args:
            query: Search query in natural language.
            video_id: Optional video ID to restrict the search to.
            year: Optional upload year to filter results.
            channel: Optional channel name to filter results (case-insensitive).
        """
        if store._collection.count() == 0:
            return "No transcripts indexed yet."

        # Build a Chroma ``where`` filter for exact-match metadata fields.
        where_parts: list[dict] = []
        if video_id is not None:
            where_parts.append({"video_id": video_id})
        if year is not None:
            where_parts.append({"year": year})

        if len(where_parts) > 1:
            where_filter = {"$and": where_parts}
        elif where_parts:
            where_filter = where_parts[0]
        else:
            where_filter = None

        docs: list[Document] = store.similarity_search(
            query,
            k=top_k,
            filter=where_filter,
        )

        if channel is not None:
            channel_lower = channel.lower()
            docs = [
                doc
                for doc in docs
                if (doc.metadata.get("channel") or "").lower() == channel_lower
            ]

        if not docs:
            return "No relevant results found."

        blocks: list[str] = []
        seen: set[str] = set()
        for i, doc in enumerate(docs[:top_k], start=1):
            meta = doc.metadata
            vid = meta.get("video_id", "?")
            title = meta.get("title", vid)
            speaker = meta.get("speaker")
            start = meta.get("start_time", "?")
            end = meta.get("end_time", "?")

            seen.add(vid)

            header = title
            if speaker:
                header += f" [{speaker}]"
            header += f" ({start}\u2013{end})"
            header += f" | {vid}"

            blocks.append(f"[{i}] {header}\n{doc.page_content}")

        blocks.append(f"---\n{len(docs[:top_k])} chunk(s) from {len(seen)} video(s)")
        return "\n\n".join(blocks)

    return search_transcripts


def make_list_videos(store):
    """Create a list_videos tool that reads directly from the Chroma collection."""

    @tool
    def list_videos(
        year: int | None = None,
        speaker: str | None = None,
        channel: str | None = None,
    ) -> str:
        """Return the catalog of all indexed videos.

        Use this tool when the user asks what videos exist, how many videos
        there are, or wants to browse the collection. Use the returned
        video_ids to call get_video_info or search_transcripts.
        """
        if store._collection.count() == 0:
            return "No videos indexed yet."

        result = store._collection.get(include=["metadatas"])
        metadatas = result.get("metadatas", [])
        if not metadatas:
            return "No videos indexed yet."

        counts: dict[str, int] = {}
        titles: dict[str, str] = {}
        channels: dict[str, str] = {}
        years: dict[str, int | None] = {}
        speakers: dict[str, str] = {}
        durations: dict[str, int | None] = {}

        for meta in metadatas:
            vid = meta.get("video_id")
            if not vid:
                continue
            counts[vid] = counts.get(vid, 0) + 1
            if vid not in titles:
                titles[vid] = meta.get("title", vid)
                channels[vid] = meta.get("channel", "unknown")
                years[vid] = meta.get("year")
                speakers[vid] = meta.get("speaker", "")
                durations[vid] = meta.get("duration")

        lines: list[str] = []
        shown = 0
        for vid, count in sorted(counts.items()):
            entry_speaker = speakers.get(vid, "")
            entry_channel = channels.get(vid, "unknown")
            entry_year = years.get(vid)

            if year is not None and entry_year != year:
                continue
            if channel is not None and channel.lower() != entry_channel.lower():
                continue
            if speaker is not None:
                s = speaker.lower()
                if s not in entry_channel.lower() and s not in entry_speaker.lower():
                    continue

            shown += 1
            line = f"{shown}. {titles[vid]}"
            if entry_year:
                line += f" ({entry_year})"
            if entry_channel != "unknown":
                line += f" - {entry_channel}"
            if entry_speaker:
                line += f" [{entry_speaker}]"
            line += f" - {count} chunk(s)"
            if durations.get(vid):
                line += f" - {durations[vid]}s"
            line += f" ({vid})"
            lines.append(line)

        if not lines:
            return "No videos matched the filters."

        lines.append(f"---\n{shown} video(s)")
        with_speakers = [vid for vid, s in speakers.items() if s and vid in counts]
        if with_speakers:
            lines.append(f"\nVideos with speakers: {len(with_speakers)}")
        return "\n".join(lines)

    return list_videos


def make_get_video_info(store):
    """Create a get_video_info tool that reads directly from the Chroma collection."""

    @tool
    def get_video_info(video_id: str) -> str:
        """Return metadata and summary for a single video by its ID.

        Use this tool when the user asks for details about a specific video
        or event. Get the video_id from list_videos first. Returns title,
        year, channel, duration, speakers, chunk count, and a text summary
        from the first chunk.
        """
        results = store._collection.get(
            where={"video_id": video_id},
            include=["metadatas", "documents"],
        )
        metadatas = results.get("metadatas", [])
        documents = results.get("documents", [])
        if not metadatas:
            return f"Video '{video_id}' not found."

        first = metadatas[0]
        first_doc = documents[0] if documents else ""
        lines: list[str] = [
            f"Title: {first.get('title') or 'N/A'}",
            f"Year: {first.get('year') or 'N/A'}",
            f"Channel: {first.get('channel') or 'unknown'}",
            f"Chunks: {len(metadatas)}",
        ]

        duration = first.get("duration")
        if duration is not None:
            lines.append(f"Duration: {duration}s")

        speakers = first.get("speaker")
        if speakers:
            lines.append(f"Speaker(s): {speakers}")

        if first_doc:
            # Extract description from enriched text
            desc_match = re.search(r"^Description:\s*(.+?)$", first_doc, re.MULTILINE)
            if desc_match:
                description = desc_match.group(1).strip()
                lines.append(f"Description: {description[:300]}")

            # Get a transcript snippet (text after the description, skipping timestamps)
            content_lines = []
            for line in first_doc.splitlines():
                line = line.strip()
                if not line or line.startswith("Title:") or line.startswith("Description:"):
                    continue
                if line.startswith("[") and "]" in line[:10]:
                    # Timestamp line: keep the text part after the timestamp
                    parts = line.split(" ", 1)
                    if len(parts) > 1:
                        content_lines.append(parts[1])
                else:
                    content_lines.append(line)
            if content_lines:
                snippet = " ".join(content_lines)[:200]
                if snippet:
                    lines.append(f"Transcript: {snippet}...")

        lines.append(f"ID: {video_id}")
        return "\n".join(lines)

    return get_video_info
