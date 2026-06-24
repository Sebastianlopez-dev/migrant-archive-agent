# Proposal: Agent disambiguation tools

## Intent

The Cero agent currently has only one tool: `search_transcripts`, which searches all 220 transcript chunks blindly. This causes three failures:

1. **Disambiguation failure** — when a user asks "what is this video about?" with 10+ videos, the agent cannot know which video is meant.
2. **Short-name garbage results** — queries like "Lina" return low-similarity noise because Gemini embeddings lack signal for bare proper names.
3. **Dense output** — results are returned as concatenated text blocks, hard to read.

This change gives the agent explicit metadata tools, query reformulation, and structured-list formatting.

## Scope

### In Scope
- Three agent-callable tools: `list_videos`, `get_video_info`, and scoped `search_transcripts`.
- Optional `video_id` filter for `search_transcripts`.
- System-prompt instruction to reformulate short/vague queries into descriptive English sentences before searching.
- System-prompt instruction to present answers as structured lists.
- Strict-TDD unit and integration tests.

### Out of Scope
- New frontend UI changes.
- API endpoint contract changes beyond tool behaviour.
- Automatic query-rewriting model separate from the agent LLM.
- Speaker enrichment if not already present in metadata.

## Capabilities

### New Capabilities
- `agent-video-listing`: `list_videos(year=None, speaker=None)` returns video_id, title, year, speaker, chunk_count for disambiguation.
- `agent-video-info`: `get_video_info(video_id)` returns full metadata plus a concise summary of one video.

### Modified Capabilities
- `agent-conversation`: add `list_videos` and `get_video_info` tools; extend `search_transcripts` with optional `video_id`; update system prompt for query reformulation and list-formatted responses.

## Approach

1. **VectorStore extensions** — add `get_unique_videos()` and `search(query_embedding, top_k, video_id=None)` using ChromaDB `where` filters.
2. **Tool factories** — keep `make_search_transcripts` and add `make_list_videos` / `make_get_video_info` in `backend/agents/tools.py`.
3. **Agent assembly** — register the three tools in `create_agent()`.
4. **Prompt engineering** — update `SYSTEM_PROMPT` to instruct reformulation and list output.
5. **Testing** — fake-LLM tests for each new tool invocation, plus vector-store filter tests.

## Affected Areas

| Area | Impact | Description |
|------|--------|-------------|
| `backend/agents/tools.py` | Modified + new | `search_transcripts` gains `video_id`; add `list_videos`, `get_video_info`. |
| `backend/agents/agent.py` | Modified | Register new tools; update `SYSTEM_PROMPT`. |
| `backend/core/vector_store.py` | Modified | Add filter helpers for video listing and scoped search. |
| `tests/test_agent.py` | Modified | New tool-calling scenarios and prompt assertions. |
| `tests/test_vector_store.py` | Modified | Scoped search and unique-video listing tests. |

## Risks

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| Speaker metadata missing or inconsistent | Medium | Make `speaker` optional; fall back to `"unknown"`. |
| LLM ignores reformulation instruction | Medium | Add explicit few-shot example in system prompt; test with fake LLM. |
| `list_videos` slow on many chunks | Low | Aggregate from metadata only; cache result per session if needed. |
| `get_video_info` summary is noisy | Low | Summarise from top-K chunks or first/last chunks; keep concise. |

## Rollback Plan

- Revert the commit that introduces the new tools and prompt changes.
- Restore the previous `make_search_transcripts` signature and single-tool agent assembly.
- Re-run `uv run python -m pytest tests/test_agent.py tests/test_vector_store.py -v` to confirm baseline behaviour.

## Dependencies

- None beyond existing ChromaDB and LangChain stack.

## Success Criteria

- [ ] `list_videos` and `get_video_info` are invoked correctly by the agent in fake-LLM tests.
- [ ] `search_transcripts(video_id=...)` returns only chunks from the requested video.
- [ ] Short-name queries are reformulated into descriptive sentences before embedding.
- [ ] Agent answers are formatted as numbered or bulleted lists.
- [ ] All existing agent and vector-store tests still pass.
