# Archive Report: agent-disambiguation-tools

**Change**: agent-disambiguation-tools  
**Archived**: 2026-06-24  
**Mode**: hybrid (Engram + OpenSpec)  
**Final verdict**: PASS WITH WARNINGS (all warnings resolved before archive)

## Artifact Traceability

### Engram observations

| Artifact | Observation ID | Topic key |
|----------|---------------|-----------|
| Proposal | #1132 | `sdd/agent-disambiguation-tools/proposal` |
| Spec | #1133 | `sdd/agent-disambiguation-tools/spec` |
| Design | #1134 | `sdd/agent-disambiguation-tools/design` |
| Tasks | #1135 | `sdd/agent-disambiguation-tools/tasks` |
| Apply progress | #1136 | `sdd/agent-disambiguation-tools/apply-progress` |
| Verify report | #1137 | `sdd/agent-disambiguation-tools/verify-report` |
| Archive report | — | `sdd/agent-disambiguation-tools/archive-report` |

### OpenSpec files

| Artifact | Active path | Archived path |
|----------|-------------|---------------|
| Proposal | `openspec/changes/agent-disambiguation-tools/proposal.md` | `openspec/changes/archive/2026-06-24-agent-disambiguation-tools/proposal.md` |
| Specs | `openspec/changes/agent-disambiguation-tools/specs/` | `openspec/changes/archive/2026-06-24-agent-disambiguation-tools/specs/` |
| Design | `openspec/changes/agent-disambiguation-tools/design.md` | `openspec/changes/archive/2026-06-24-agent-disambiguation-tools/design.md` |
| Tasks | `openspec/changes/agent-disambiguation-tools/tasks.md` | `openspec/changes/archive/2026-06-24-agent-disambiguation-tools/tasks.md` |
| Apply progress | `openspec/changes/agent-disambiguation-tools/apply-progress.md` | `openspec/changes/archive/2026-06-24-agent-disambiguation-tools/apply-progress.md` |
| Verify report | `openspec/changes/agent-disambiguation-tools/verify-report.md` | `openspec/changes/archive/2026-06-24-agent-disambiguation-tools/verify-report.md` |
| Archive report | `openspec/changes/agent-disambiguation-tools/archive-report.md` | `openspec/changes/archive/2026-06-24-agent-disambiguation-tools/archive-report.md` |

## Task Completion Gate

All 12 implementation tasks in `tasks.md` / Engram #1135 are marked `[x]`.

No stale unchecked implementation tasks remain.

## Spec Sync

### Domains affected

| Domain | Action | Details |
|--------|--------|---------|
| `agent-video-listing` | No delta merge needed | Main spec `openspec/specs/agent-video-listing/spec.md` already contains the full requirement set from the change. |
| `agent-video-info` | No delta merge needed | Main spec `openspec/specs/agent-video-info/spec.md` already contains the full requirement set from the change. |
| `agent-conversation` | Merged delta | Replaced "Agent factory uses native tool calling" and "System prompt is role-focused" with updated versions; added "Agent registers list_videos and get_video_info", "Agent reformulates queries before search", and "Agent presents results as structured lists". |

### Requirements added to main specs

- `agent-conversation` / Agent registers list_videos and get_video_info
- `agent-conversation` / Agent reformulates queries before search
- `agent-conversation` / Agent presents results as structured lists

### Requirements modified in main specs

- `agent-conversation` / Agent factory uses native tool calling (now registers all 3 tools)
- `agent-conversation` / System prompt is role-focused (now mentions reformulation, list formatting, all 3 tools)

No requirements were removed.

## Verification Status

- **Targeted tests**: `uv run python -m pytest tests/test_agent.py tests/test_vector_store.py -v` → 38 passed.
- **Full suite**: `uv run python -m pytest tests/ -v` → 137 passed, 3 failed (pre-existing BGE-M3 environmental failures), 1 skipped.
- **Behavioral smoke tests**: Agent CLI and `rag_test.py` start correctly.
- **CRITICAL findings**: None.
- **WARNING findings**: One outdated `create_agent` docstring claimed default tools were `[search_transcripts]`; verified fixed at `backend/agents/agent.py` line 79, which now reads `Defaults to [list_videos, get_video_info, search_transcripts].`.

## Files Changed (Implementation)

| File | Change |
|------|--------|
| `backend/core/vector_store.py` | Added `video_id` filter to `search()` and added `get_unique_videos()`. |
| `backend/agents/tools.py` | Added `make_list_videos`, `make_get_video_info`; extended `make_search_transcripts` with optional `video_id`. |
| `backend/agents/agent.py` | Updated `SYSTEM_PROMPT`; registered 3 tools; fixed docstring. |
| `tests/test_vector_store.py` | Added scoped search and unique-videos tests. |
| `tests/test_agent.py` | Added tool unit tests, prompt assertions, fake-LLM integration tests. |

## Source of Truth Updated

The following main specs now reflect the new behavior:

- `openspec/specs/agent-video-listing/spec.md`
- `openspec/specs/agent-video-info/spec.md`
- `openspec/specs/agent-conversation/spec.md`

## Archive Location

The full change artifact trail has been moved to:

```
openspec/changes/archive/2026-06-24-agent-disambiguation-tools/
```

## SDD Cycle Complete

The change has been fully planned, implemented, verified, and archived. Ready for the next change.
