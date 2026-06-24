# Verification Report: agent-disambiguation-tools

## Change
agent-disambiguation-tools — extend the single-tool agent with `list_videos`, `get_video_info`, and scoped `search_transcripts`, plus updated system prompt for query reformulation and list formatting.

## Mode
Strict TDD active. Test runner: `uv run python -m pytest tests/ -v`.

## Completeness Table

| Phase / Artifact | Status | Notes |
|------------------|--------|-------|
| Tasks complete | ✅ PASS | All 12 tasks marked `[x]` in tasks.md / Engram #1135. |
| Spec exists | ✅ PASS | Full spec set (agent-video-listing, agent-video-info, agent-conversation delta). |
| Design exists | ✅ PASS | Design.md / Engram #1134 present and followed. |
| Apply progress exists | ✅ PASS | Apply-progress.md / Engram #1136 present. |
| Implementation inspected | ✅ PASS | Source files read and compared against spec/design. |
| Tests executed | ✅ PASS | Full suite run; targeted tests all pass. |

## Test Results

### Full suite
```
uv run python -m pytest tests/ -v
3 failed, 137 passed, 1 skipped
```

### Targeted tests
```
uv run python -m pytest tests/test_agent.py tests/test_vector_store.py -v
38 passed
```

### Failure detail
The 3 failures are pre-existing and environmental, not caused by this change:

- `tests/test_embedding_bge_m3.py::TestBGEM3EmbeddingProvider::test_embed_batch`
- `tests/test_embedding_bge_m3.py::TestBGEM3EmbeddingProvider::test_embed_query`
- `tests/test_embedding_bge_m3.py::TestBGEM3EmbeddingProvider::test_singleton_caches_model`

Root cause: `transformers` now requires `torch >= 2.6` for `torch.load` due to CVE-2025-32434. The uv environment has an older torch, and BGE-M3 is documented as the conda path.

### Behavioral smoke tests
- `printf 'quit\n' | uv run python backend/scripts/agent_cli.py` — starts correctly, prints welcome, exits cleanly.
- `printf 'quit\n' | uv run python backend/scripts/rag_test.py` — starts correctly, reports `Collection size: 220 chunks`.

## Spec Compliance Matrix

| Requirement / Scenario | Test Evidence | Status |
|------------------------|---------------|--------|
| `list_videos` returns catalog with `video_id`, `title`, `year`, `speaker`, `chunk_count` | `TestListVideosTool::test_list_videos_returns_all_videos` | ✅ PASS |
| Filter `list_videos(year=...)` | `TestListVideosTool::test_list_videos_filters_by_year` | ✅ PASS |
| Filter `list_videos(speaker=...)` | `TestListVideosTool::test_list_videos_filters_by_speaker` | ✅ PASS |
| Combine year + speaker filters | `TestListVideosTool::test_list_videos_combines_filters` | ✅ PASS |
| `get_video_info` returns metadata + summary | `TestGetVideoInfoTool::test_get_video_info_returns_metadata` | ✅ PASS |
| `get_video_info` missing video handling | `TestGetVideoInfoTool::test_get_video_info_missing_video_returns_not_found` | ✅ PASS |
| `search_transcripts` accepts optional `video_id` | `TestSearchTranscriptsTool::test_search_with_video_id_scopes_results` | ✅ PASS |
| Agent registers `list_videos` and `get_video_info` | `TestToolCallingLoop::test_fake_llm_calls_list_videos`, `test_fake_llm_calls_get_video_info` | ✅ PASS |
| Agent reformulates queries before search | `TestCreateAgent::test_system_prompt_mandates_reformulation` | ✅ PASS |
| Agent presents results as structured lists | `TestCreateAgent::test_system_prompt_requires_list_formatting` | ✅ PASS |
| Agent factory uses native tool calling + history | `TestCreateAgent::test_create_agent_returns_runnable_with_history`, `test_create_agent_wires_history_keys` | ✅ PASS |
| Fake LLM invokes scoped search | `TestToolCallingLoop::test_fake_llm_calls_search_transcripts` | ✅ PASS |
| System prompt mentions all tools | `TestCreateAgent::test_system_prompt_mentions_all_tools` | ✅ PASS |
| System prompt lacks ReAct markers | `TestCreateAgent::test_create_agent_prompt_has_no_react_format` | ✅ PASS |

## Correctness Table

| Code Quality Check | Evidence | Status |
|--------------------|----------|--------|
| All tools use `@tool` decorator | `backend/agents/tools.py` lines 32, 97, 155 | ✅ PASS |
| No hardcoded production paths | Paths via `video_data_dir` param / `VIDEO_DATA_DIR` env / `CHROMA_PERSIST_DIR` env | ✅ PASS |
| Error handling for missing `video_id` | `get_video_info` returns Spanish "not found" message; `list_videos` handles empty catalog | ✅ PASS |
| English code, comments, identifiers | Source files use English identifiers and comments | ✅ PASS |

## Design Coherence Table

| Design Decision | Implementation | Status |
|-----------------|----------------|--------|
| Tools in `backend/agents/tools.py` | `make_list_videos`, `make_get_video_info`, extended `make_search_transcripts` all in `backend/agents/tools.py` | ✅ PASS |
| `list_videos` source: ChromaDB IDs + JSON enrichment | `store.get_unique_videos()` + `VideoData.load_json()` enrichment | ✅ PASS |
| `get_video_info` source: `VideoData` JSON + chunk count | Reads JSON, counts chunks via `get_unique_videos()` | ✅ PASS |
| Scoped search uses ChromaDB `where` filter | `VectorStore.search()` passes `where={"video_id": video_id}` | ✅ PASS |
| Summary = first 300 chars of `full_text` | `video_data.full_text[:300]` | ✅ PASS |
| No new files created unnecessarily | Only existing 4 source/test files modified | ✅ PASS |
| `video_data_dir` default: `data/raw/whisper` | `DEFAULT_VIDEO_DATA_DIR = Path(os.getenv("VIDEO_DATA_DIR", "data/raw/whisper"))` | ✅ PASS |

**Note:** The verification checklist mentioned `data/processed/` as the JSON source, but the authoritative design document and implementation both use `data/raw/whisper` (the canonical `VideoData.save_json` output). Implementation is coherent with design.

## Findings

### CRITICAL
None.

### WARNING
1. **Outdated `create_agent` docstring**
   - **Where:** `backend/agents/agent.py`, line 79.
   - **What:** Docstring says tools default to `[search_transcripts]`, but the default now includes `list_videos`, `get_video_info`, and `search_transcripts`.
   - **Why fix:** Misleading documentation for callers of the factory.
   - **Suggested fix:** Update docstring to "Defaults to [list_videos, get_video_info, search_transcripts]."

### SUGGESTION
1. **Address `RunnableWithMessageHistory` deprecation**
   - The full suite emits `LangChainDeprecationWarning: RunnableWithMessageHistory is deprecated. Use LangGraph's built-in persistence instead.` This is pre-existing but will become a migration task.
2. **Align verification checklist with design**
   - Future verify prompts should reference `data/raw/whisper` for `VideoData` JSON to match the design document and project conventions.

## Final Verdict
**PASS WITH WARNINGS**

The implementation fully satisfies the specs and design. All targeted tests pass, the full suite only fails on 3 pre-existing BGE-M3 environmental issues, and both agent CLI and RAG test start correctly. The single WARNING is a docstring inaccuracy in `create_agent` that should be corrected before archive or in a fast follow-up commit.

## Next Recommended
1. Fix `create_agent` docstring (one-line change).
2. Re-run `uv run python -m pytest tests/test_agent.py tests/test_vector_store.py -v` to confirm no regression.
3. Proceed to `sdd-archive`.

## Risks
- **Low:** The pre-existing BGE-M3 torch/transformers CVE mismatch remains unaddressed, but it is outside this change's scope and documented as the conda path.
- **Low:** `RunnableWithMessageHistory` deprecation will require future migration but does not affect current functionality.

## Skill Resolution
- Skill loaded: `sdd-verify`
- Strict TDD module: active (per orchestrator instruction)
- Skill paths injected: `sdd-verify` skill instructions, project AGENTS.md conventions
