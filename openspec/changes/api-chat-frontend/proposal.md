# Proposal: api-chat-frontend

## Intent

Expose the existing `Cero` ReAct agent (S06) through a FastAPI backend and an embeddable chat widget, so Plataforma Cero visitors can ask questions about archived migrant testimonies directly from the website.

## Scope

### In Scope
- `POST /api/ask` endpoint returning `answer` and `sources`.
- CORS configured for local widget development and the Plataforma Cero production origin.
- Stateless, single-turn chat API (no session memory).
- `frontend/` with pnpm + Vite + vanilla TypeScript.
- Floating chat bubble, slide-out panel, "Cerito" avatar placeholder.
- Brand styling matching Plataforma Cero colors and system font stack.

### Out of Scope
- Multi-turn conversation memory or user sessions.
- Authentication, rate limiting, and persistence of chat history.
- Hosting/deployment automation (only local dev wiring).

## Capabilities

### New Capabilities
- `chat-api`: FastAPI endpoint wrapping the Cero agent with request-scoped instances.
- `chat-widget`: Embeddable frontend bubble and slide-out panel for asking questions.

### Modified Capabilities
- None.

## Approach

### Backend
- Add FastAPI in `backend/api/main.py` with a `POST /api/ask` route.
- Request body: `{"question": "..."}`; response: `{"answer": "...", "sources": [...]}`.
- Build a fresh `AgentExecutor` per request using `create_agent()` to avoid sharing non-thread-safe ChromaDB and Gemini clients across concurrent requests.
- Run `agent.invoke()` in `run_in_threadpool` because `AgentExecutor` is synchronous.
- Add CORS middleware allowing configured origins (`http://localhost:5173` and the production site).

### Frontend
- Vite + vanilla TypeScript project in `frontend/`.
- Render a fixed bottom-right bubble; clicking it opens a slide-out panel.
- Panel contains messages list, input field, and send button.
- Call `POST /api/ask` and render streaming-free response.
- Use CSS custom properties for brand colors and the existing system font stack.

## Key Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Widget form | Embeddable slide-out bubble (Approach 2) | Matches the requested Claude-style UX and can be dropped into any page. |
| Agent instance | Per-request `AgentExecutor` (Approach 3) | `chromadb.PersistentClient` and `google.genai.Client` are not guaranteed thread-safe; fresh instances per request are the safest MVP. |
| Memory model | Stateless single-turn | Keeps S07 small; conversation memory is deferred to a follow-up change. |
| Frontend stack | Vite + vanilla TypeScript | No runtime dependencies; fast build; easy to embed. |

## File Plan

### New Files
| File | Description |
|------|-------------|
| `backend/api/main.py` | FastAPI app, CORS, `/api/ask` route. |
| `backend/api/models.py` | Pydantic request/response models. |
| `backend/api/dependencies.py` | Per-request agent factory. |
| `tests/test_api.py` | API unit/integration tests. |
| `frontend/package.json` | pnpm/Vite project manifest. |
| `frontend/vite.config.ts` | Vite dev server + build config. |
| `frontend/index.html` | Entry page and widget mount point. |
| `frontend/src/main.ts` | Bootstrap widget. |
| `frontend/src/chat-widget.ts` | Bubble + panel logic and DOM. |
| `frontend/src/styles.css` | Brand styling and animations. |
| `frontend/public/cerito-avatar.svg` | Placeholder avatar. |

### Modified Files
| File | Change |
|------|--------|
| `requirements.txt` | Add `fastapi`. |
| `.env.example` (if exists) | Document `ALLOWED_ORIGINS`. |

## Dependencies

- **Backend runtime**: `fastapi` (add to `requirements.txt`). `uvicorn` is already present.
- **Frontend runtime**: none (vanilla TypeScript).
- **Frontend dev**: pnpm, Vite, TypeScript.

## Risks

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| ChromaDB concurrency issues | Med | Per-request agent instances avoid shared client state. |
| CORS misconfiguration blocking widget | Low | Explicit allowed-origin list and local-dev wildcard fallback. |
| No session memory limits usefulness | Med | Documented as MVP scope; follow-up change planned. |
| Synchronous agent blocks event loop | Med | Wrap `agent.invoke()` in `run_in_threadpool`. |

## Rollback Plan

1. Stop the FastAPI process.
2. Revert `requirements.txt` to remove `fastapi`.
3. Delete `backend/api/` and `frontend/` directories.
4. The previous CLI-based agent (`backend/scripts/agent_cli.py`) remains unchanged and functional.

## Success Criteria

- [ ] `POST /api/ask` returns a JSON answer with sources in under ~5 seconds for typical queries.
- [ ] Frontend widget loads, opens on bubble click, sends questions, and displays answers.
- [ ] Tests pass: `uv run python -m pytest tests/ -v`.
- [ ] CORS allows the configured frontend origin.
- [ ] Concurrent requests do not crash or corrupt the ChromaDB client.
