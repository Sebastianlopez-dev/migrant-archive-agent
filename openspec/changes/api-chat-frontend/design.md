# Design: api-chat-frontend

## Technical Approach

Expose the S06 Cero ReAct agent through a FastAPI `POST /api/ask` endpoint and an embeddable vanilla-TypeScript chat widget. The backend builds a fresh `AgentExecutor` for every request and runs the synchronous `agent.invoke()` in `run_in_threadpool`. The frontend uses Vite with a dev-server proxy to the API and has zero runtime dependencies. Brand colors and typography mirror the existing Plataforma Cero site.

## Architecture Decisions

### Decision: Per-request agent instances

| Option | Tradeoff | Decision |
|--------|----------|----------|
| Singleton agent reused across requests | Lower latency but risks shared ChromaDB/Gemini client state | Rejected |
| Fresh `AgentExecutor` per request | Slightly higher cold-start, guaranteed isolation | Selected |

Rationale: `chromadb.PersistentClient` and `google.genai.Client` are not documented as thread-safe. Request-scoped instances are the safest MVP and satisfy the spec's concurrency requirement.

### Decision: Source extraction

| Option | Tradeoff | Decision |
|--------|----------|----------|
| Parse from agent `intermediate_steps` | Captures the exact sources the agent consumed | Selected |
| Re-run vector search in the route | Wasteful and may diverge from the agent's view | Rejected |

Rationale: The response must include `video_id`, `title`, `start_time`, `end_time`, and `text`. The current `search_transcripts` observation omits `video_id`, so the tool formatting is extended to include it and the route parses the observation string.

### Decision: Frontend stack

| Option | Tradeoff | Decision |
|--------|----------|----------|
| Vite + vanilla TypeScript | No runtime deps, fast builds, easy to embed | Selected |
| React + build toolchain | Heavier, more dependencies | Rejected |

Rationale: The widget is a drop-in component. Keeping it dependency-free reduces maintenance, bundle size, and embedding friction.

## Data Flow

```
Browser widget ──POST /api/ask──► FastAPI route
                                        │
                                        ▼
                         dependencies.get_agent() → fresh AgentExecutor
                                        │
                                        ▼
                         run_in_threadpool(agent.invoke(question))
                                        │
                                        ▼
                         search_transcripts tool → ChromaDB VectorStore
                                        │
                         ┌──────────────┘
                         ▼
              Parse intermediate_steps into Source[]
                         │
                         ▼
              JSON AskResponse ──► Widget renders answer + sources
```

## File Changes

| File | Action | Description |
|------|--------|-------------|
| `backend/api/main.py` | Create | FastAPI app factory, CORS middleware, route registration |
| `backend/api/models.py` | Create | Pydantic `AskRequest`, `AskResponse`, `Source` |
| `backend/api/dependencies.py` | Create | `get_agent()` per-request factory |
| `backend/api/routes/chat.py` | Create | `POST /api/ask`, invokes agent and parses sources |
| `backend/agents/tools.py` | Modify | Include `video_id` in tool observation for parsing |
| `tests/test_api.py` | Create | Unit, integration, and CORS tests |
| `frontend/package.json` | Create | pnpm/Vite project manifest |
| `frontend/vite.config.ts` | Create | Dev proxy `/api` → `http://localhost:8000` |
| `frontend/index.html` | Create | Widget mount point |
| `frontend/src/main.ts` | Create | Bootstrap `ChatWidget` |
| `frontend/src/chat-widget.ts` | Create | Bubble + panel DOM logic and API call |
| `frontend/src/styles.css` | Create | Brand CSS custom properties and animations |
| `frontend/public/cerito-avatar.svg` | Create | Bubble avatar SVG |
| `requirements.txt` | Modify | Add `fastapi` |

## Interfaces / Contracts

### Backend

```python
class Source(BaseModel):
    video_id: str
    title: str
    start_time: str
    end_time: str
    text: str

class AskRequest(BaseModel):
    question: str = Field(..., min_length=1)

class AskResponse(BaseModel):
    answer: str
    sources: list[Source]
```

### Frontend

```typescript
interface Source {
  video_id: string;
  title: string;
  start_time: string;
  end_time: string;
  text: string;
}

interface AskResponse {
  answer: string;
  sources: Source[];
}
```

### Source parsing contract

The `search_transcripts` observation is formatted as:

```text
[1] VIDEO_ID | Title (start–end)
Text chunk content

[2] VIDEO_ID | Title (start–end)
Text chunk content
```

The route parses each block with a regex such as:

```python
r"\[(\d+)\]\s+([^\n|]+?)\s*\|\s*([^(\n]+?)\s*\(([^–)]+?)\s*–\s*([^)]+?)\)\n(.*)"
```

## Testing Strategy

| Layer | What to Test | Approach |
|-------|-------------|----------|
| Unit | `POST /api/ask` with mocked agent | Patch `dependencies.get_agent`, assert `AskResponse` shape and source fields |
| Integration | Real agent path | `pytest.mark.skipif(not os.getenv("GEMINI_API_KEY"))`, assert 200 and non-empty answer |
| CORS | Preflight headers | `client.options("/api/ask", headers={"Origin": "http://localhost:5173"})` |

## Migration / Rollout

No migration required. Local rollout sequence:

1. Add `fastapi` to `requirements.txt` and run `uv pip install -r requirements.txt`.
2. Start the API: `uv run uvicorn backend.api.main:app --reload --port 8000`.
3. Start the widget: `cd frontend && pnpm install && pnpm dev`.
4. Embed the built widget bundle in the Plataforma Cero page.

## Open Questions

None.
