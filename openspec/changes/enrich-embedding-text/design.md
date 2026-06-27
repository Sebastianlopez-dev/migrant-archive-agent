# Design: Enrich Embedding Text with Title, Description, and Timestamps

## Technical Approach

Add `VideoData.enriched_text()` as the single formatter that turns title, description, and timestamped transcript segments into one embedding-ready string. Wire it at ingestion so newly persisted JSONs are already enriched, and wire it in `Processor.chunk()` as a fallback when legacy JSONs still carry plain `full_text` plus `transcript_segments`. Keep the existing `VideoData` schema unchanged so old files remain valid.

## Architecture Decisions

| Decision | Options | Tradeoffs | Choice |
|---|---|---|---|
| Formatter location | VideoData method vs. external helper | Method keeps data + formatting together; helper would add an import everywhere | `VideoData.enriched_text()` in `ingestion.py` |
| Ingestion wiring | Compute string first, then construct; or construct then assign | Construct-then-assign keeps `full_text` required and makes the mutation explicit in `_build_videodata()` | Build `VideoData` with plain text, then `vd.full_text = vd.enriched_text()` |
| Legacy fallback | Always enriched vs. only when segments exist | Always enriched would lose text for files without segments; conditional preserves old behavior | Use `enriched_text()` only when `transcript_segments` is non-empty, else `full_text` |
| Timestamp estimation for enriched chunks | Segment offset map vs. parse markers in chunk text | Offset map is precise but larger; parsing markers is good enough and stays within review budget | Parse first/last `[MM:SS]` / `[HH:MM:SS]` marker in each chunk |
| Long descriptions | Truncate now vs. defer | Current dataset has short descriptions; proposal defers this | Defer; document as known limitation |
| PR split | Single PR vs. stacked PRs | Stacked keeps ingestion and chunking changes isolated and under 400 lines each | Change A (ingestion) then Change B (processor), `stacked-to-main` |

## Data Flow

```
ingestion.py _build_videodata()
        │
        ▼
VideoData(title, description, segments, full_text)
        │
        ├─ enriched_text() ──► full_text (new JSONs)
        │
        ▼
processor.py chunk()
        │
        ├─ segments present?  text = enriched_text()
        └─ no segments?       text = full_text
                    │
                    ▼
            chunks with title/description context + [MM:SS]
```

## File Changes

| File | Action | Description |
|---|---|---|
| `backend/core/ingestion.py` | Modify | Add `VideoData.enriched_text()` and a `_format_timestamp` helper; update `_build_videodata()` to store enriched text |
| `backend/core/processor.py` | Modify | `chunk()` selects enriched text when segments exist; estimate chunk `start_time`/`end_time` from markers in the chunk |
| `tests/test_processor.py` | Modify | Update exact-text assertions; add cases for enriched chunks and empty segments fallback |
| `tests/test_ingestion.py` | Modify/Create | Add `enriched_text()` format tests (sub-hour, hour-long, empty segments) |
| `README.md` | Modify | Document Phase 2 enriched chunking behavior |

## Interfaces / Contracts

```python
# backend/core/ingestion.py

@dataclass
class VideoData:
    ...

    def enriched_text(self) -> str:
        """Return title, description, and timestamped segments.

        Format:
            Title: {title}
            Description: {description}

            [MM:SS] segment text
            ...
        """
        ...


def _build_videodata(info: dict, segments: list[dict]) -> VideoData:
    vd = VideoData(
        video_id=info["id"],
        title=info.get("title", ""),
        description=info.get("description", ""),
        transcript_segments=segments,
        full_text=" ".join(seg["text"] for seg in segments),
        metadata=info,
    )
    vd.full_text = vd.enriched_text()
    return vd
```

```python
# backend/core/processor.py

def chunk(self, video_data: VideoData) -> list[Chunk]:
    text = (
        video_data.enriched_text()
        if video_data.transcript_segments
        else video_data.full_text
    )
    ...
```

Timestamp helper (module-private):

```python
def _format_timestamp(seconds: float, use_hours: bool) -> str:
    secs = int(seconds)
    hours, rem = divmod(secs, 3600)
    mins, secs = divmod(rem, 60)
    if use_hours:
        return f"{hours:02d}:{mins:02d}:{secs:02d}"
    return f"{mins:02d}:{secs:02d}"
```

Hour-format decision is based on total video duration (`max(start + duration)` or `metadata.duration >= 3600`).

## Testing Strategy

| Layer | What to Test | Approach |
|---|---|---|
| Unit | `enriched_text()` format | Assert output contains `Title:`, `Description:`, `[00:00]`, `[01:05]` |
| Unit | Hour-plus timestamp format | Assert segment at 3661s renders as `[01:01:01]` |
| Unit | `_build_videodata()` persistence | Assert saved JSON `full_text` equals `enriched_text()` |
| Integration | `Processor.chunk()` enrichment fallback | Legacy `VideoData` with segments produces chunks containing timestamps |
| Integration | `Processor.chunk()` no-segments fallback | Empty `transcript_segments` uses plain `full_text` |
| E2E | `python backend/scripts/rebuild_index.py` | Rebuild index and verify retrieved chunks include title/description/timestamps |

## Migration / Rollout

No migration required. Legacy JSONs remain valid because `full_text` and `transcript_segments` are preserved. New JSONs are born enriched. Existing ChromaDB collections will pick up enriched text on the next `--rebuild`.

## Open Questions

- None blocking. Long-description truncation (REQ-ENRICH-006) is intentionally deferred per the proposal.
