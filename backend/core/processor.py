"""Document processor: chunking + embedding orchestration.

Receives an EmbeddingProvider via dependency injection. Takes VideoData,
chunks the full_text, and produces embeddings. Does NOT know which
embedding implementation is wired in.
"""

import re
from dataclasses import dataclass, field

from embedding import EmbeddingProvider
from ingestion import VideoData


# ---------------------------------------------------------------------------
# Chunk dataclass
# ---------------------------------------------------------------------------


@dataclass
class Chunk:
    """A single chunk of transcript text with source metadata."""

    text: str
    metadata: dict = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Processor
# ---------------------------------------------------------------------------


class Processor:
    """Orchestrates chunking and embedding of VideoData.

    Constructor receives an EmbeddingProvider — the processor has zero
    knowledge of *which* provider is active (Gemini, BGE-M3, or fake).
    """

    def __init__(
        self,
        provider: EmbeddingProvider,
        chunk_size: int = 1000,
        overlap: int = 200,
    ):
        """Initialise the processor.

        Args:
            provider: Any EmbeddingProvider implementation.
            chunk_size: Target tokens per chunk (estimated as len(text)//4).
            overlap: Token overlap between consecutive chunks.
        """
        self._provider = provider
        self._chunk_size = chunk_size
        self._overlap = overlap

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def process(self, video_data: VideoData) -> tuple[list[Chunk], list[list[float]]]:
        """Full pipeline: chunk then embed.

        Returns:
            (chunks, embeddings) — parallel lists, same length.
        """
        chunks = self.chunk(video_data)
        embeddings = self.embed_chunks(chunks)
        return chunks, embeddings

    def chunk(self, video_data: VideoData) -> list[Chunk]:
        """Split text into overlapping chunks with metadata.

        Uses enriched text (title + description + timestamped segments) when
        transcript segments are available, otherwise falls back to the stored
        full_text. Token estimation: len(text) // 4.
        """
        text = (
            video_data.enriched_text()
            if video_data.transcript_segments
            else video_data.full_text
        )
        if not text or not text.strip():
            return []

        # Convert tokens ↔ characters using 4 chars ≈ 1 token
        chunk_chars = self._chunk_size * 4
        overlap_chars = self._overlap * 4
        step = chunk_chars - overlap_chars

        if step <= 0:
            step = chunk_chars  # safety: avoid infinite loop

        chunks: list[Chunk] = []
        start = 0
        chunk_index = 0

        while start < len(text):
            end = min(start + chunk_chars, len(text))

            # Don't cut mid-word if possible
            if end < len(text):
                # Try to extend to next space for a clean word boundary
                space_idx = text.rfind(" ", start, end)
                if space_idx > start + chunk_chars // 2:
                    end = space_idx

            chunk_text = text[start:end].strip()
            if chunk_text:
                start_time = _parse_timestamp(chunk_text) or 0.0
                end_time = (
                    _parse_timestamp(chunk_text, last=True)
                    or start_time
                )
                metadata = {
                    "video_id": video_data.video_id,
                    "title": video_data.title,
                    "chunk_index": chunk_index,
                    "start_time": start_time,
                    "end_time": end_time,
                    "channel": _channel_from_metadata(video_data.metadata),
                    "year": _year_from_metadata(video_data.metadata),
                    "speaker": _extract_speakers_from_description(
                        video_data.description, video_data.title
                    ),
                }
                chunks.append(Chunk(text=chunk_text, metadata=metadata))
                chunk_index += 1

            start += step

        return chunks

    def embed_chunks(self, chunks: list[Chunk]) -> list[list[float]]:
        """Generate embeddings for a list of chunks."""
        if not chunks:
            return []
        texts = [c.text for c in chunks]
        return self._provider.embed(texts)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _estimate_time(segments: list[dict], char_position: int) -> float:
        """Approximate timestamp for a character position in plain text.

        Walks through transcript segments accumulating character counts
        until reaching the target position, then returns the segment's
        start time. Used as a fallback when chunk text has no timestamp
        markers.
        """
        if not segments:
            return 0.0

        accumulated = 0
        for seg in segments:
            accumulated += len(seg.get("text", "")) + 1  # +1 for space
            if accumulated >= char_position:
                return seg.get("start", 0.0)

        # Past the end — return last segment's end
        last = segments[-1]
        return last.get("start", 0.0) + last.get("duration", 0.0)


def _channel_from_metadata(metadata: dict) -> str:
    """Return channel name from yt-dlp-style metadata."""
    return metadata.get("channel") or metadata.get("uploader") or "unknown"


def _year_from_metadata(metadata: dict) -> int | None:
    """Return upload year from yt-dlp-style metadata."""
    upload_date = metadata.get("upload_date")
    if upload_date and len(str(upload_date)) >= 4:
        try:
            return int(str(upload_date)[:4])
        except ValueError:
            return None
    return None


def _parse_timestamp(text: str, last: bool = False) -> float | None:
    """Parse the first or last [MM:SS] / [HH:MM:SS] marker in text.

    Args:
        text: Chunk text potentially containing timestamp markers.
        last: If True, parse the last marker; otherwise the first.

    Returns:
        Timestamp in seconds, or None if no marker is found.
    """
    matches = list(re.finditer(r"\[(?:(\d{2}):)?(\d{2}):(\d{2})\]", text))
    if not matches:
        return None

    match = matches[-1] if last else matches[0]
    hours = int(match.group(1) or 0)
    minutes = int(match.group(2))
    seconds = int(match.group(3))
    return hours * 3600 + minutes * 60 + seconds


# ---------------------------------------------------------------------------
# Speaker extraction helpers
# ---------------------------------------------------------------------------


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
