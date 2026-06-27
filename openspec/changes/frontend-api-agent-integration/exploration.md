# Exploration: Frontend <-> API <-> Agent Integration Status

## Current State
- **Frontend**: Complete chat widget (bubble + slide-out panel) in vanilla TypeScript. Calls `POST /api/ask`. Does NOT send `session_id`. Build pipeline (Vite + pnpm + TS) is fully configured and produces a `dist/` bundle.
- **API**: FastAPI with two endpoints (`POST /api/ask`, `DELETE /api/session/{session_id}`). CORS configured for `localhost:5173`. **NOT runnable** because `agent.py` imports `langchain_chroma`, which is not installed / not in `requirements.txt`.
- **Agent**: `create_agent()`, `get_session_history()`, and `clear_session()` are all present and correctly wired. Uses `InMemoryChatMessageHistory` with a 10-message sliding window. Same `langchain_chroma` import blocks initialization.

## What's Already Connected
- Frontend `fetch('/api/ask')` -> Vite proxy (`vite.config.ts:7-10`) -> FastAPI `chat.ask` (`backend/api/routes/chat.py:82-101`)
- API `ask` -> `get_agent` dependency (`backend/api/dependencies.py:26`) -> `create_agent()` (`backend/agents/agent.py:124`)
- API `delete_session` -> `clear_session()` (`backend/agents/agent.py:113`)
- Source parsing from `intermediate_steps` -> `AskResponse.sources` (`backend/api/routes/chat.py:48-79`)
- CORS preflight and validation error handlers configured (`backend/api/main.py:25-47`)
- Unit tests cover Pydantic models, route logic with mocked agents, CORS, and frontend structure (`tests/test_api.py`, `tests/test_frontend.py`)

## What's Missing / Broken
- **`backend/agents/agent.py:13`** — `from langchain_chroma import Chroma` raises `ModuleNotFoundError`. This cascades to `dependencies.py:23` and `chat.py:22`, making the entire API unimportable.
- **`frontend/src/chat-widget.ts:156`** — `body: JSON.stringify({ question })` omits `session_id`. Every browser session shares the `"default"` session history, so conversations leak across users/tabs.
- **`backend/api/main.py:38`** — No static file mount for the built frontend (`dist/`). In production the API and frontend need a reverse proxy or the API must serve `dist/` itself.
- **`backend/api/main.py`** — No health/readiness endpoint. Hard to verify deployment status.
- **`frontend/src/chat-widget.ts:153`** — Fetch uses a relative `/api/ask` URL. This works in dev (Vite proxy) but assumes the API is on the same origin in production.

## Steps to Connect (ordered, with estimated lines per step)
1. **Fix `langchain_chroma` import** — Either add `langchain-chroma` to `requirements.txt` and install it, OR change `backend/agents/agent.py:13` to import `Chroma` from `langchain_community.vectorstores`. Verify `uv run python -c "from backend.api.main import app"` succeeds. — ~2 lines across 1-2 files
2. **Add session management to frontend** — Generate a UUID on first widget open, persist in `localStorage`, and include it in every `POST /api/ask` body as `session_id`. — ~12 lines in `frontend/src/chat-widget.ts`
3. **Serve built frontend from FastAPI** — Mount `frontend/dist` as static files at `/` in `backend/api/main.py` so the API can host its own UI. — ~6 lines in `backend/api/main.py`
4. **Add health check endpoint** — `GET /health` returning `{"status": "ok"}` in `backend/api/main.py`. — ~5 lines in `backend/api/main.py`
5. **Run smoke test** — Start `uvicorn backend.api.main:app --port 8000`, start `pnpm dev`, open browser, verify chat bubble -> question -> agent answer with sources. — ~0 lines (manual verification)

## Total Lines to Touch
~25 lines across 3 files (agent.py, chat-widget.ts, main.py) plus potentially 1 line in requirements.txt.
