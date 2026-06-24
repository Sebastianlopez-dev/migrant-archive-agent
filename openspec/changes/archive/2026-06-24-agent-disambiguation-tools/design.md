# Design: Agent disambiguation tools

## Technical Approach

Extend the existing single-tool agent into a three-tool agent. `list_videos` and `get_video_info` provide catalog and per-video metadata so the LLM can disambiguate vague references; `search_transcripts` gains an optional `video_id` filter for scoped search. The system prompt is updated to force query reformulation and structured-list output.

Data flow keeps two sources: ChromaDB remains the source of chunk-level truth, while `VideoData` JSON files (`data/raw/whisper/*.json`) remain the source of video-level metadata. No re-indexing is required because `video_id` is already stored on every chunk.

## Architecture Decisions

| Decision | Option chosen | Alternatives | Rationale |
|----------|---------------|--------------|-----------|
| Tool location | Extend `backend/agents/tools.py` | New `disambiguation_tools.py`; `tools/` package | Current file is 50 lines; three small factories fit comfortably. Split only if tools grow past 5–6. |
| `list_videos` source of truth | ChromaDB for video IDs + chunk counts; JSON files for year/speaker | Add year/speaker to every chunk metadata; maintain a separate video index | Avoids re-indexing the existing 220 chunks and keeps video-level metadata in its canonical JSON source. Acceptable for current scale; add cache if listing becomes hot. |
| `get_video_info` source | Read `VideoData` JSON; count chunks via ChromaDB | Store description/duration in every chunk | Duplicating long descriptions per chunk is wasteful; JSON is the authoritative source. |
| Scoped search | ChromaDB `where={"video_id": video_id}` | Post-filter retrieved results | Native metadata filter is exact and efficient; current collection already stores `video_id` on every chunk. |
| Query reformulation | Instruct LLM in system prompt | Separate rewrite model/tool | Cheaper, simpler, and sufficient per spec. The agent itself passes the rewritten string to `search_transcripts`. |
| Summary in `get_video_info` | First 300 characters of `VideoData.full_text` | LLM-based summarisation inside the tool | Deterministic, fast, testable; avoids extra LLM calls in a tool. |

## Data Flow

```
User query
    │
    ▼
┌─────────────┐    reformulate / choose tool    ┌─────────────┐
│  create_agent │ ──────────────────────────────▶ │  Gemini LLM  │
│  (3 tools)    │ ◀────────────────────────────── │              │
└─────────────┘         tool calls                └─────────────┘
       │
       ├── list_videos ──▶ VectorStore.get_unique_videos() + JSON enrichment
       │
       ├── get_video_info ──▶ VideoData.load_json() + VectorStore chunk count
       │
       └── search_transcripts ──▶ embed ──▶ VectorStore.search(video_id=...)
```

## File Changes

| File | Action | Description |
|------|--------|-------------|
| `backend/agents/tools.py` | Modify | Add `make_list_videos` and `make_get_video_info`; extend `make_search_transcripts` with optional `video_id`. |
| `backend/agents/agent.py` | Modify | Register the three tools in `create_agent`; update `SYSTEM_PROMPT` for reformulation, list formatting, and tool inventory. |
| `backend/core/vector_store.py` | Modify | Add `search(query_embedding, top_k, video_id=None)` metadata filter and `get_unique_videos()` aggregation. |
| `tests/test_agent.py` | Modify | New tool unit tests and fake-LLM scenarios for `list_videos`, `get_video_info`, and scoped search; prompt assertions. |
| `tests/test_vector_store.py` | Modify | Tests for `search(video_id=...)` and `get_unique_videos()`. |

Estimated net change: ~340 lines across 4 files. No new files.

## Interfaces / Contracts

```python
# backend/core/vector_store.py
class VectorStore:
    def search(
        self,
        query_embedding: list[float],
        top_k: int = 5,
        video_id: str | None = None,
    ) -> list[dict]: ...

    def get_unique_videos(self) -> list[dict]:
        """Return [{"video_id": str, "title": str, "chunk_count": int}]."""
        ...

# backend/agents/tools.py
def make_search_transcripts(provider, store, top_k: int = 3): ...
# tool signature becomes: search_transcripts(query: str, video_id: str | None = None)

def make_list_videos(
    video_data_dir: Path,
    store,
): ...
# tool signature: list_videos(year: int | None = None, speaker: str | None = None)

def make_get_video_info(
    video_data_dir: Path,
    store,
): ...
# tool signature: get_video_info(video_id: str)
```

`make_list_videos` and `make_get_video_info` receive `video_data_dir` (default `Path("data/raw/whisper")`) so tests can point to a temporary directory.

`get_video_info` returns a JSON string with keys: `video_id`, `title`, `description`, `year`, `duration`, `speaker`, `chunk_count`, `summary`. Missing videos return a Spanish "not found" message.

## System Prompt Change

Current:
```python
SYSTEM_PROMPT = (
    "You are Cero, an assistant that answers questions in Spanish about archived "
    "migrant testimonies. Use the search_transcripts tool to find relevant "
    "transcript fragments. Always respond in Spanish, cite the video and "
    "time range when possible, and do not invent information."
)
```

Updated:
```python
SYSTEM_PROMPT = (
    "You are Cero, an assistant that answers questions in Spanish about archived "
    "migrant testimonies. You have three tools: list_videos, get_video_info, "
    "and search_transcripts. "
    "If a query is vague or a bare proper name (e.g. 'Lina'), use list_videos "
    "or get_video_info to disambiguate, or rewrite the query into a descriptive "
    "English sentence of at least 3-5 words before calling search_transcripts. "
    "When presenting multiple results, steps, or examples, always use a numbered "
    "or bulleted list. Always respond in Spanish, cite the video and time range "
    "when possible, and do not invent information."
)
```

## Testing Strategy

| Layer | What to test | Approach |
|-------|-------------|----------|
| Unit | `VectorStore.search(video_id=...)` | In-memory ChromaDB; assert only matching `video_id` chunks are returned. |
| Unit | `VectorStore.get_unique_videos()` | In-memory store with multiple videos; assert unique IDs and correct chunk counts. |
| Unit | `make_search_transcripts` scoped | Fake provider + in-memory store; invoke with `video_id`. |
| Unit | `make_list_videos` | Temp `VideoData` JSON files + in-memory store; test filter by year/speaker and missing JSON fallback. |
| Unit | `make_get_video_info` | Temp JSON files; assert all fields present and missing video handling. |
| Integration | Agent tool-calling loop | Fake `BaseChatModel` emits `list_videos` / `get_video_info` / `search_transcripts` tool calls; verify intermediate steps. |
| Integration | Prompt assertions | Assert updated `SYSTEM_PROMPT` mentions all tools, reformulation, and list formatting, and lacks ReAct markers. |
| E2E | Real Gemini + in-memory store | Skip if `GEMINI_API_KEY` missing; agent uses scoped search and lists videos. |

## Migration / Rollout

No data migration is required: existing ChromaDB chunks already carry `video_id`, which is sufficient for scoped search and unique-video aggregation. Video-level fields (`description`, `duration`, `year`, `speaker`) are read from `VideoData` JSON files at query time.

Rollout steps:
1. Deploy code changes.
2. Run `uv run python -m pytest tests/test_agent.py tests/test_vector_store.py -v`.
3. Optionally verify with `python backend/scripts/agent_cli.py` using queries such as "list videos" and "tell me about FKymj4_fn3g".

Rollback: revert the commit; the previous single-tool `search_transcripts` and original `SYSTEM_PROMPT` are restored.

## Open Questions

- [ ] Should `speaker` be a single string or a list? Current metadata provides one channel/uploader per video; design uses a string with `"unknown"` fallback.
- [ ] Should `list_videos` cache the JSON scan? For 10 videos it is unnecessary; revisit if catalog grows past a few hundred videos.
