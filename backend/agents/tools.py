"""LangChain tools for the migrant-archive agent.

Tools:
  - search_transcripts: embeds a user query and retrieves relevant transcript
    chunks from the ChromaDB-backed VectorStore.
  - list_videos: lists indexed videos with optional year/speaker filters.
  - get_video_info: returns metadata and a short summary for a single video.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

from langchain_core.tools import tool

from core.ingestion import VideoData


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
    def search_transcripts(
        query: str,
        video_id: str | None = None,
        year: int | None = None,
        channel: str | None = None,
    ) -> str:
        """Search archived video transcripts for a given query.

        Args:
            query: Search query.
            video_id: Optional video ID to restrict the search to.
            year: Optional upload year to filter results.
            channel: Optional channel name to filter results.
        """
        if store.count == 0:
            return "No hay transcripciones indexadas aún."

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
        for i, result in enumerate(results, start=1):
            metadata = result.get("metadata", {})
            result_video_id = metadata.get("video_id", "desconocido")
            title = metadata.get("title", result_video_id)
            start = metadata.get("start_time", "?")
            end = metadata.get("end_time", "?")
            document = result.get("document", "")
            blocks.append(
                f"[{i}] {result_video_id} | {title} ({start}–{end})\n{document}"
            )

        return "\n\n".join(blocks)

    return search_transcripts


def _normalize_math_bold(text: str) -> str:
    """Convert Mathematical Alphanumeric Symbols to plain ASCII.

    Covers Mathematical Bold, Italic, and Sans-Serif Bold capitals and
    small letters (U+1D400–U+1D7FF) so names like 𝐍𝐚𝐝𝐢𝐚 become readable.
    """
    result: list[str] = []
    for char in text:
        codepoint = ord(char)
        if 0x1D400 <= codepoint <= 0x1D433:  # Mathematical Bold A-z
            # 0x1D400 -> 'A', 0x1D41A -> 'a'
            result.append(chr((codepoint - 0x1D400) % 26 + (65 if codepoint < 0x1D41A else 97)))
        elif 0x1D434 <= codepoint <= 0x1D467:  # Mathematical Italic A-z
            result.append(chr((codepoint - 0x1D434) % 26 + (65 if codepoint < 0x1D44E else 97)))
        elif 0x1D5D4 <= codepoint <= 0x1D607:  # Mathematical Sans-Serif Bold A-z
            result.append(chr((codepoint - 0x1D5D4) % 26 + (65 if codepoint < 0x1D5EE else 97)))
        elif 0x1D608 <= codepoint <= 0x1D63B:  # Mathematical Sans-Serif Italic A-z
            result.append(chr((codepoint - 0x1D608) % 26 + (65 if codepoint < 0x1D622 else 97)))
        elif 0x1D63C <= codepoint <= 0x1D66F:  # Mathematical Sans-Serif Bold Italic A-z
            result.append(chr((codepoint - 0x1D63C) % 26 + (65 if codepoint < 0x1D656 else 97)))
        elif 0x1D6A8 <= codepoint <= 0x1D6E1:  # Mathematical Bold Greek
            result.append(char)  # leave Greek as-is
        else:
            result.append(char)
    return "".join(result)


# Spanish stop words that should never start a person's name.
_NAME_STOP_WORDS = frozenset({
    "en", "un", "una", "el", "la", "los", "las", "de", "del", "que",
    "por", "para", "como", "hacia", "nos", "se", "su", "con", "sin",
    "este", "esta", "desde", "donde", "cuando", "también",
})


def _looks_like_name(text: str) -> bool:
    """Return True when *text* looks like a person name (2-4 title-case words)."""
    words = text.split()
    if len(words) < 2 or len(words) > 4:
        return False
    if words[0].lower() in _NAME_STOP_WORDS:
        return False
    # Each word must start with an uppercase letter (or be a single
    # uppercase initial like "V.").
    for w in words:
        if not w[0].isupper():
            return False
    return True


def _extract_speakers_from_description(description: str, title: str = "") -> str:
    """Extract participant names from a YouTube video description or title.

    Returns a comma-separated string of names, or an empty string when no
    identifiable pattern is found.
    """
    if not description and not title:
        return ""

    # Normalize mathematical bold/italic glyphs so plain-text regexes and
    # emoji markers can coexist.
    description = _normalize_math_bold(description)

    # Pattern A: "Participantes:" section with 📌 markers.
    if "📌" in description and "participantes" in description.lower():
        names: list[str] = []
        in_section = False
        for line in description.splitlines():
            lower = line.lower()
            if "participantes" in lower:
                in_section = True
                continue
            if in_section and line.strip().startswith("📌"):
                raw = line.lstrip("📌").strip()
                raw = raw.split("(@")[0]
                raw = raw.split("–")[0]
                raw = raw.split("—")[0]
                name = raw.strip()
                if name:
                    names.append(name)
        if names:
            return ", ".join(names)

    # Pattern B: "Nos acompañan:" section with 👉🏾 markers.
    if "👉🏾" in description and "nos acompañan" in description.lower():
        names = []
        in_section = False
        for line in description.splitlines():
            lower = line.lower()
            if "nos acompañan" in lower:
                in_section = True
                continue
            if in_section and "👉🏾" in line:
                raw = line.split("👉🏾", 1)[1].strip()
                raw = raw.split(":")[0]
                name = raw.strip()
                if name:
                    names.append(name)
        if names:
            return ", ".join(names)

    # Pattern C: "convoca a:" comma-separated list.
    convoca_match = re.search(
        r"convoca a:\s*([^\n]+?)(?:\n|$)",
        description,
        flags=re.IGNORECASE,
    )
    if convoca_match:
        raw_list = convoca_match.group(1)
        parts = re.split(r",\s*|\s+y\s+", raw_list)
        names = [
            part.strip() for part in parts
            if part.strip() and _looks_like_name(part.strip())
        ]
        if names:
            return ", ".join(names)

    # Pattern D: "Modera:" / "Moderadora:" marker.
    modera_match = re.search(
        r"(?:moderadora?|modera):\s*([^\n@]+)",
        description,
        flags=re.IGNORECASE,
    )
    if modera_match:
        name = modera_match.group(1).strip()
        if name:
            return name

    # Pattern E: title fallback, e.g. "... con X, Y y Z".
    title = _normalize_math_bold(title)
    title_match = re.search(
        r"\bcon\s+([^|]+?)(?:\||$)",
        title,
        flags=re.IGNORECASE,
    )
    if title_match:
        raw_list = title_match.group(1)
        # Only treat it as a participant list when separators are present.
        if "," in raw_list or " y " in raw_list or " and " in raw_list:
            parts = re.split(r",\s*|\s+y\s+|\s+and\s+", raw_list)
            names = [
                part.strip() for part in parts
                if part.strip() and _looks_like_name(part.strip())
            ]
            if names:
                return ", ".join(names)

    return ""


def _get_channel_and_speakers(
    metadata: dict, description: str = "", title: str = ""
) -> tuple[str, str]:
    """Return (channel, speakers) from yt-dlp metadata and description.

    Channel always comes from the uploader metadata (e.g. "Plataforma Cero").
    Speakers are extracted from the description when a structured pattern is
    found; otherwise empty.

    Returns:
        (channel, speakers) — channel is always populated; speakers may be "".
    """
    channel = metadata.get("channel") or metadata.get("uploader") or "unknown"
    speakers = _extract_speakers_from_description(description, title=title)
    return channel, speakers


def _year_from_metadata(metadata: dict) -> int | None:
    """Extract the upload year from yt-dlp-style metadata.

    yt-dlp stores upload_date as 'YYYYMMDD'.
    """
    upload_date = metadata.get("upload_date")
    if upload_date and len(str(upload_date)) >= 4:
        try:
            return int(str(upload_date)[:4])
        except ValueError:
            return None
    return None


def make_list_videos(video_data_dir: str | Path, store):
    """Create a configured list_videos tool.

    Args:
        video_data_dir: Directory containing VideoData JSON files.
        store: VectorStore with get_unique_videos() -> list[dict].

    Returns:
        A LangChain tool callable.
    """
    data_dir = Path(video_data_dir)

    @tool
    def list_videos(
        year: int | None = None,
        speaker: str | None = None,
        channel: str | None = None,
    ) -> str:
        """List indexed videos, optionally filtered by year, speaker, or channel.

        The *speaker* parameter matches against both the channel name and any
        speakers extracted from the video description.
        """
        catalog = store.get_unique_videos()
        if not catalog:
            return "No hay videos indexados aún."

        enriched: list[dict] = []
        for entry in catalog:
            video_id = entry["video_id"]
            title = entry.get("title", video_id)
            chunk_count = entry.get("chunk_count", 0)

            # Prefer catalog metadata from the vector store.
            store_meta = store.get_video_metadata(video_id) or {}
            video_year = store_meta.get("year")
            video_channel = store_meta.get("channel") or "unknown"
            video_speakers = store_meta.get("speaker") or ""
            duration = store_meta.get("duration")

            # JSON fallback during transition: enrich title, year, channel,
            # and speakers when the store metadata is incomplete.
            json_path = data_dir / f"{video_id}.json"
            if json_path.exists():
                try:
                    video_data = VideoData.load_json(json_path)
                    title = video_data.title or title
                    if video_year is None:
                        video_year = _year_from_metadata(video_data.metadata)
                    if video_channel == "unknown":
                        fallback_channel, fallback_speakers = _get_channel_and_speakers(
                            video_data.metadata,
                            description=video_data.description,
                            title=video_data.title,
                        )
                        video_channel = fallback_channel
                        if not video_speakers:
                            video_speakers = fallback_speakers
                    elif not video_speakers:
                        _, video_speakers = _get_channel_and_speakers(
                            video_data.metadata,
                            description=video_data.description,
                            title=video_data.title,
                        )
                    if duration is None:
                        duration = video_data.metadata.get("duration")
                except Exception:
                    pass

            if year is not None and video_year != year:
                continue
            if channel is not None and channel.lower() != video_channel.lower():
                continue
            if speaker is not None:
                speaker_lower = speaker.lower()
                channel_match = speaker_lower in video_channel.lower()
                speakers_match = speaker_lower in video_speakers.lower()
                if not (channel_match or speakers_match):
                    continue

            entry_dict: dict[str, object] = {
                "video_id": video_id,
                "title": title,
                "year": video_year,
                "channel": video_channel,
                "chunk_count": chunk_count,
            }
            if video_speakers:
                entry_dict["speaker"] = video_speakers
            if duration is not None:
                entry_dict["duration"] = duration
            enriched.append(entry_dict)

        if not enriched:
            return "No se encontraron videos que coincidan con los filtros."

        return json.dumps(enriched, indent=2, ensure_ascii=False)

    return list_videos


def make_get_video_info(video_data_dir: str | Path, store):
    """Create a configured get_video_info tool.

    Args:
        video_data_dir: Directory containing VideoData JSON files.
        store: VectorStore with get_unique_videos() -> list[dict].

    Returns:
        A LangChain tool callable.
    """
    data_dir = Path(video_data_dir)

    @tool
    def get_video_info(video_id: str) -> str:
        """Return metadata and a short summary for a single video."""
        # Prefer vector-store metadata; JSON remains a fallback for description
        # and speaker extraction during the transition.
        store_meta = store.get_video_metadata(video_id)

        json_path = data_dir / f"{video_id}.json"
        if store_meta is None and not json_path.exists():
            return f"Video '{video_id}' no encontrado."

        title = store_meta.get("title") if store_meta else None
        year = store_meta.get("year") if store_meta else None
        channel = store_meta.get("channel") if store_meta else None
        speakers = store_meta.get("speaker") if store_meta else None
        duration = store_meta.get("duration") if store_meta else None
        chunk_count = store_meta.get("chunk_count", 0) if store_meta else 0
        description = ""
        summary = ""

        if json_path.exists():
            try:
                video_data = VideoData.load_json(json_path)
                title = title or video_data.title
                description = video_data.description
                if year is None:
                    year = _year_from_metadata(video_data.metadata)
                if channel is None:
                    channel, fallback_speakers = _get_channel_and_speakers(
                        video_data.metadata,
                        description=video_data.description,
                        title=video_data.title,
                    )
                    if not speakers:
                        speakers = fallback_speakers
                elif not speakers:
                    _, speakers = _get_channel_and_speakers(
                        video_data.metadata,
                        description=video_data.description,
                        title=video_data.title,
                    )
                if duration is None:
                    duration = video_data.metadata.get("duration")
                summary = video_data.full_text[:300]
            except Exception as exc:
                if store_meta is None:
                    return f"No se pudo leer el video '{video_id}': {exc}"

        if not title:
            return f"Video '{video_id}' no encontrado."

        info: dict[str, object] = {
            "video_id": video_id,
            "title": title,
            "description": description,
            "year": year,
            "duration": duration,
            "channel": channel or "unknown",
            "chunk_count": chunk_count,
            "summary": summary,
        }
        if speakers:
            info["speakers"] = speakers
        return json.dumps(info, indent=2, ensure_ascii=False)

    return get_video_info
