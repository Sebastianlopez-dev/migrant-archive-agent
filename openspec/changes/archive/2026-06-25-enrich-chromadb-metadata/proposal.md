# Proposal: Enrich ChromaDB Metadata

## Intent
Move `list_videos` and `get_video_info` off disk-based JSON reads by embedding `channel` and `year` metadata into every ChromaDB chunk. This makes the vector store the single source of truth for catalog and info queries, reduces file I/O, and enables compound metadata filters in semantic search.

## Scope

### In Scope
- Add `channel` and `year` to chunk metadata in `processor.py`
- Add compound `where` filter support in `vector_store.py`
- Add `get_video_metadata()` to `vector_store.py`
- Update `search_transcripts`, `list_videos`, `get_video_info` in `tools.py`
- Update agent system prompt in `agent.py`
- Unit/integration tests for metadata and filtering

### Out of Scope
- Removing JSON files entirely
- Changing embedding model or chunking strategy
- Frontend or API endpoint changes beyond tool behavior

## Capabilities

### New Capabilities
- `vector-store-metadata`: Compound metadata filtering and video metadata retrieval from ChromaDB

### Modified Capabilities
- `agent-video-listing`: `list_videos` reads channel/year from ChromaDB instead of JSON; channel filter added
- `agent-video-info`: `get_video_info` reads channel/year from ChromaDB instead of JSON
- `agent-conversation`: `search_transcripts` gains optional `year` and `channel` filters; system prompt updated to expose filters

## Approach
Store `channel` and `year` as ChromaDB metadata fields during ingestion. Build compound `$and`/`$or` `where` clauses in `vector_store.py`. Expose a `get_video_metadata(video_id)` helper that derives title/year/channel/speaker/duration/chunk_count from the collection. Update tools to use vector store methods and add filter parameters. Update the agent prompt so it knows it can filter by year and channel.

## Affected Areas

| Area | Impact | Description |
|------|--------|-------------|
| `backend/core/processor.py` | Modified | Adds `channel` and `year` to chunk metadata |
| `backend/core/vector_store.py` | Modified | Compound `where` filters; new `get_video_metadata()` |
| `backend/agents/tools.py` | Modified | All three tools use ChromaDB metadata |
| `backend/agents/agent.py` | Modified | System prompt mentions new filters |
| `tests/test_processor.py` | Modified | Verify channel/year metadata |
| `tests/test_vector_store.py` | Modified | Test compound where filtering |
| `tests/test_agent.py` | Modified | Update tool metadata tests, add filter tests |

## Risks

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| Existing indexed data lacks new metadata | High | Re-ingest or backfill script; tests use fresh in-memory store |
| Compound where syntax incompatible with ChromaDB client version | Low | Verify against current `chromadb` version in tests |
| Tool signature changes break agent tool calling | Low | Update agent tests and run full agent test suite |

## Rollback Plan
Revert the commit. In-memory tests and CI will fail forward; production data can be rebuilt by re-running the ingestion pipeline on existing JSON files.

## Dependencies
- Current `chromadb` Python client supports metadata filtering
- Existing JSON files remain available as fallback during migration

## Success Criteria
- [ ] `list_videos()` returns channel/year from ChromaDB, not JSON
- [ ] `get_video_info()` returns channel/year from ChromaDB, not JSON
- [ ] `search_transcripts` accepts and applies `year` and `channel` filters
- [ ] `vector_store.py` supports compound `where` filters
- [ ] All tests pass under `uv run python -m pytest tests/ -v`
