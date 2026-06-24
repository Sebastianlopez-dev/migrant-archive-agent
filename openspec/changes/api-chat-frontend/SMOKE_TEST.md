# Smoke Test Runbook: api-chat-frontend

This runbook verifies the integration between the FastAPI backend and the Vite/TypeScript chat widget.

## Prerequisites

- Python 3.12+ and `uv` installed
- Node.js 20+ and `pnpm` installed
- `.env` file with `GEMINI_API_KEY` (required for live agent responses; API tests skip live calls when absent)
- Backend and frontend dependencies installed:
  - `uv pip install -r requirements.txt`
  - `cd frontend && pnpm install --ignore-scripts`

## 1. Verify the FastAPI app imports cleanly

```bash
uv run python -c "from backend.api.main import app; print('FastAPI app OK')"
```

Expected output: `FastAPI app OK`

## 2. Start the API server

```bash
uv run uvicorn backend.api.main:app --reload --port 8000
```

Check the health of the app:

```bash
curl http://localhost:8000/docs
```

You should see the auto-generated Swagger UI.

## 3. Start the frontend dev server

In a second terminal:

```bash
cd frontend
pnpm dev
```

The Vite dev server should start on `http://localhost:5173` and proxy `/api/*` requests to `http://localhost:8000`.

## 4. Test the widget manually

1. Open `http://localhost:5173` in a browser.
2. Click the floating chat bubble (bottom-right).
3. Type a question in Spanish, for example:

   > ¿Qué testimonios hay sobre la migración?

4. Press **Enter** or click **Enviar**.
5. Expect:
   - A user message bubble appears.
   - The send button shows **Enviando…** while the request is in flight.
   - An agent response appears with an answer and, when sources are available, a **Fuentes** section.
   - Each source links to the corresponding YouTube timestamp.

## 5. Test an invalid request

```bash
curl -X POST http://localhost:8000/api/ask \
  -H "Content-Type: application/json" \
  -d '{"question": ""}'
```

Expected: HTTP `422 Unprocessable Entity` with a validation detail.

## 6. Run the automated verification

### Targeted tests

```bash
uv run python -m pytest tests/test_api.py tests/test_frontend.py tests/test_agent.py -v
```

Expected: all tests pass except the pre-existing Gemini E2E rate-limit failure (`TestAgentE2E::test_e2e_agent_answers_from_transcripts`).

### Full suite excluding pre-existing broken tests

```bash
uv run python -m pytest tests/ -v \
  --ignore=tests/test_embedding_gemini.py \
  --ignore=tests/test_embedding_bge_m3.py \
  --ignore=tests/test_pipeline_e2e.py
```

Expected: 100 passed, 2 skipped, 2 failed (both are Gemini `429` rate-limit errors unrelated to this change).

## Known pre-existing failures (do not fix here)

- `tests/test_embedding_gemini.py` — `ModuleNotFoundError`
- `tests/test_embedding_bge_m3.py` — `torch/transformers` version incompatibility
- `tests/test_pipeline_e2e.py` — `ImportError`
- `tests/test_vector_store.py::TestVectorStoreGemini::test_search_returns_ordered_by_relevance` — Gemini `429` rate limit
- `tests/test_agent.py::TestAgentE2E::test_e2e_agent_answers_from_transcripts` — Gemini `429` rate limit

## Shut down

Stop the frontend server with `Ctrl+C`, then stop the API server with `Ctrl+C`.
