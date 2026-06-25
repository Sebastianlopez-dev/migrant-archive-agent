# Design: Enrich ChromaDB Metadata

## Technical Approach

Extend the chunk metadata produced by `Processor.chunk()` to include `channel` and `year` extracted from `VideoData.metadata`. Update `VectorStore.search()` to support compound `where` clauses using ChromaDB's `$and` operator. Add `VectorStore.get_video_metadata()` to derive catalog fields from the first chunk of a video. Refactor the three LangChain tools (`search_transcripts`, `list_videos`, `get_video_info`) to read channel/year from the vector store instead of JSON disk files. Update the agent system prompt to mention the new filter capabilities.

## Architecture Decisions

### Decision: Where to extract channel and year

| Option | Tradeoff | Decision |
|--------|----------|----------|
| Inside `Processor.chunk()` | Keeps SRP; no new module; metadata stays close to chunking | **Chosen** |
| New `MetadataEnricher` class | Extra abstraction for only two fields | Rejected — overkill |
| In ingestion pipeline before processor | Tightens coupling between ingestion and storage | Rejected — breaks existing boundary |

### Decision: Backward compatibility for existing indexed data

| Option | Tradeoff | Decision |
|--------|----------|----------|
| Backfill script | Requires running a migration against production ChromaDB | Rejected — out of scope |
| Graceful degradation (filters return empty when key missing) | No migration needed; re-ingestion unlocks full benefit | **Chosen** |
| Schema versioning in metadata | Adds complexity for a single field addition | Rejected — unnecessary |

### Decision: Compound where clause construction

| Option | Tradeoff | Decision |
|--------|----------|----------|
| ChromaDB native `$and` / `$or` | Standard syntax, no client upgrade needed | **Chosen** |
| Manual post-filtering in Python | Wastes vector search work, breaks top_k | Rejected — inefficient |
| Raw SQL via ChromaDB | Not supported by client API | Rejected — impossible |

### Decision: Speaker extraction location

| Option | Tradeoff | Decision |
|--------|----------|----------|
| Move into `VectorStore` | Store would depend on complex regex and description parsing | Rejected — wrong abstraction |
| Keep in `tools.py` | Complex parsing stays in agent layer; store remains simple | **Chosen** |
| Extract at ingestion time | Would bloat every chunk with speaker strings | Rejected — too heavy |

## Data Flow

```
VideoData (with yt-dlp metadata)
    |
    v
Processor.chunk() ---> adds channel + year to metadata
    |
    v
VectorStore.add() ---> ChromaDB collection
    |
    |---> VectorStore.search(where={$and: [...]}) <--- search_transcripts tool
    |
    |---> VectorStore.get_video_metadata(video_id) <--- get_video_info tool
    |
    +---> VectorStore.get_unique_videos() <--- list_videos tool
```

## File Changes

| File | Action | Description |
|------|--------|-------------|
| `backend/core/processor.py` | Modify | Add `channel` and `year` to chunk metadata dict |
| `backend/core/vector_store.py` | Modify | Compound `where` support via `$and`; add `get_video_metadata()` |
| `backend/agents/tools.py` | Modify | `search_transcripts` gains `year`/`channel` params; `list_videos` and `get_video_info` read from store |
| `backend/agents/agent.py` | Modify | System prompt mentions new `year` and `channel` filters |
| `tests/test_processor.py` | Modify | Assert `channel` and `year` present in chunk metadata |
| `tests/test_vector_store.py` | Modify | Test compound `where` filtering and `get_video_metadata()` |
| `tests/test_agent.py` | Modify | Update tool tests for new signatures and store-backed metadata |

## Interfaces / Contracts

`VectorStore.search()` signature change:

```python
def search(
    self,
    query_embedding: list[float],
    top_k: int = 5,
    video_id: str | None = None,
    year: int | None = None,
    channel: str | None = None,
) -> list[dict]:
```

`VectorStore.get_video_metadata()`:

```python
def get_video_metadata(self, video_id: str) -> dict:
    """Return {video_id, title, year, channel, chunk_count} from first chunk."""
```

Non-obvious pattern: when `video_id` and `year` are both provided, build:

```python
where = {"$and": [
    {"video_id": video_id},
    {"year": year},
]}
```

## Testing Strategy

| Layer | What to Test | Approach |
|-------|-------------|----------|
| Unit | `Processor.chunk()` emits `channel`/`year` | `FakeEmbeddingProvider` + `VideoData` with yt-dlp-style metadata |
| Unit | `VectorStore.get_video_metadata()` returns correct fields | In-memory ChromaDB with seeded chunks |
| Integration | Compound `where` filters (`video_id` + `year`, `year` + `channel`) | In-memory ChromaDB, assert result counts |
| Integration | `search_transcripts` tool with new params | Fake provider + store, invoke with `year`/`channel` |
| Integration | `list_videos` returns channel/year from store, not JSON | Store with metadata, no JSON files |
| E2E | Agent uses filters end-to-end | Real Gemini API (skipped when `GEMINI_API_KEY` absent) |

## Migration / Rollout

No migration script required. Existing ChromaDB collections continue to work; chunks without `channel`/`year` simply fail compound filters gracefully (return empty). To unlock full filtering, re-run the ingestion pipeline on existing JSON files. The JSON files remain as fallback sources during the transition.

## Open Questions

None.
