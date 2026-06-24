# Tasks: api-chat-frontend

## Review Workload Forecast

| Field | Value |
|-------|-------|
| Estimated changed lines | 900–1100 |
| 400-line budget risk | High |
| Chained PRs recommended | Yes |
| Suggested split | PR 1 (backend API + tests) → PR 2 (frontend widget + assets) → PR 3 (integration smoke tests + docs) |
| Delivery strategy | auto-forecast |
| Chain strategy | stacked-to-main |

Decision needed before apply: No
Chained PRs recommended: Yes
Chain strategy: stacked-to-main
400-line budget risk: High

### Suggested Work Units

| Unit | Goal | Likely PR | Notes |
|------|------|-----------|-------|
| 1 | Backend API, models, dependencies, routes, CORS, error handling, source parsing, unit/CORS tests | PR 1 | Base: main; includes `backend/api/*`, `backend/agents/tools.py`, `tests/test_api.py`, `requirements.txt` |
| 2 | Vite + TypeScript frontend setup, chat widget, styles, avatar, build verification | PR 2 | Base: PR 1 branch or feature/tracker; no Python code |
| 3 | Integration/E2E smoke test, manual runbook | PR 3 | Base: PR 2 branch or feature/tracker; ties both stacks together |

## Phase 1: Dependencies

- [x] 1.1 Add `fastapi` to `requirements.txt` and run `uv pip install -r requirements.txt`
- [x] 1.2 Create `backend/api/__init__.py`

## Phase 2: Pydantic Models (TDD)

- [x] 2.1 RED: Write failing test in `tests/test_api.py` for `AskRequest` validation (empty question raises 422)
- [x] 2.2 GREEN: Implement `backend/api/models.py` with `AskRequest`, `Source`, and `AskResponse`
- [x] 2.3 REFACTOR: Run `uv run python -m pytest tests/test_api.py -v -k model` until green

## Phase 3: API Route (TDD)

- [x] 3.1 RED: Write failing test in `tests/test_api.py` for `POST /api/ask` with a mocked agent returning fixed `intermediate_steps`
- [x] 3.2 GREEN: Implement `backend/api/dependencies.py` (`get_agent()` factory), `backend/api/routes/chat.py` (`POST /api/ask`), and `backend/api/main.py` (app factory + router registration)
- [x] 3.3 REFACTOR: Run `uv run python -m pytest tests/test_api.py -v -k ask` until green

## Phase 4: CORS + Error Handling (TDD)

- [x] 4.1 RED: Write failing CORS preflight test in `tests/test_api.py` (`OPTIONS /api/ask` with `Origin: http://localhost:5173`)
- [x] 4.2 GREEN: Wire CORS middleware from `ALLOWED_ORIGINS`, add 422 validation handler, and 503 handler for missing `GEMINI_API_KEY`
- [x] 4.3 REFACTOR: Run `uv run python -m pytest tests/test_api.py -v -k cors` until green

## Phase 5: Source Parsing

- [x] 5.1 RED: Write test in `tests/test_api.py` parsing `search_transcripts` observation into `Source` list
- [x] 5.2 GREEN: Implement source extraction from agent `intermediate_steps` in `backend/api/routes/chat.py`
- [x] 5.3 Modify `backend/agents/tools.py` to include `video_id` in the tool observation using the `[n] VIDEO_ID | Title (start–end)` format

## Phase 6: Frontend Setup

- [ ] 6.1 Create `frontend/package.json`, `frontend/vite.config.ts`, and `frontend/tsconfig.json` with dev proxy `/api` → `http://localhost:8000`
- [ ] 6.2 Create `frontend/index.html` with a widget mount point
- [ ] 6.3 Run `pnpm install` in `frontend/` and verify no errors

## Phase 7: Chat Widget

- [ ] 7.1 Implement `frontend/src/styles.css` with brand CSS custom properties (`--brand-blue: #019ee3`) and animations
- [ ] 7.2 Implement `frontend/src/chat-widget.ts`: floating bubble, slide-out 380px panel, message list, input, send button, and `fetch POST /api/ask`
- [ ] 7.3 Implement `frontend/src/main.ts` to bootstrap the widget on DOM ready
- [ ] 7.4 Create `frontend/public/cerito-avatar.svg` placeholder
- [ ] 7.5 Verify widget builds with `pnpm build`

## Phase 8: Integration + E2E

- [x] 8.1 Write integration test in `tests/test_api.py` that uses the real agent and skips when `GEMINI_API_KEY` is unset
- [ ] 8.2 Run the full test suite `uv run python -m pytest tests/ -v` and fix failures
- [ ] 8.3 Manual smoke test: start `uvicorn backend.api.main:app` and `pnpm dev`, then submit a question through the widget
