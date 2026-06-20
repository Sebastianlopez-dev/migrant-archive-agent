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
