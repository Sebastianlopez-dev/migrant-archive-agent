# Design: Chat UI Redesign

## Technical Approach

Refactor the existing `ChatWidget` into a small set of vanilla-TypeScript ES modules that render a fixed FAB, a right-side panel, a static zero-state, and a bottom-anchored input toolbar. State changes are instantaneous: no CSS transitions, transforms, keyframes, or JavaScript animation loops. The backend API contract, Vite configuration, and bootstrap code remain untouched.

## Architecture Decisions

### Decision: Component split

| Option | Tradeoff | Decision |
|---|---|---|
| Single `chat-widget.ts` | Fewer files, but grows with every feature | Rejected |
| 5-6 focused ES modules | More files, easier to review and test | Selected |

### Decision: State management

| Option | Tradeoff | Decision |
|---|---|---|
| Plain class properties on `ChatWidget` | Zero deps, sufficient for this scope | Selected |
| External state library | Adds dependency and indirection | Rejected |

### Decision: Panel open/close rendering

| Option | Tradeoff | Decision |
|---|---|---|
| `display` / `visibility` toggle | Instant, respects no-animation constraint | Selected |
| CSS transform/transition slide | Violates the delta spec | Rejected |

### Decision: Theming

| Option | Tradeoff | Decision |
|---|---|---|
| CSS custom properties | Native, zero deps, easy dark palette | Selected |
| Utility-class framework | Adds build complexity and deps | Rejected |

## Component Architecture

```
chat-widget.ts      orchestrator: state + lifecycle
fab.ts              FAB button
panel.ts            panel shell, header, close button
zero-state.ts       greeting + suggestion cards
message-list.ts     message bubbles + source citations
input-bar.ts        bottom toolbar + voice/model placeholders
api-client.ts       fetch wrapper for POST /api/ask
```

## DOM Structure

```
#chat-root
├── button.chat-fab[aria-controls="chat-panel"][aria-expanded]
│   └── img /cerito-avatar.svg
└── section#chat-panel.chat-panel[role="dialog"][aria-label="Chat con Cerito"]
    ├── header.chat-panel-header
    │   ├── .chat-panel-title
    │   │   ├── img
    │   │   └── h2 Cerito
    │   └── button.chat-panel-close[aria-label="Cerrar chat"]
    ├── .chat-panel-content
    │   ├── .chat-zero-state
    │   │   ├── .chat-zero-state-greeting
    │   │   │   ├── h3 Hola, soy Cerito
    │   │   │   └── p Purpose text
    │   │   └── .chat-suggestions
    │   │       └── button.chat-suggestion (×3)
    │   └── .chat-messages[role="log"][aria-live="polite"]
    └── .chat-input-bar
        ├── .chat-input-toolbar
        │   ├── button.chat-input-tool (voice placeholder)
        │   ├── input.chat-input
        │   └── button.chat-send
        └── .chat-input-meta (model selector placeholder)
```

## CSS Strategy

- CSS custom properties for the dark palette and the brand blue accent (`--blue: #019ee3`).
- BEM-style class names scoped under `.chat-widget`.
- Panel width: `width: 30vw; min-width: 320px; max-width: 480px`.
- Below 640px: `width: 100%`.
- Static hover/focus states use color or outline changes only (no `transition`).
- `prefers-reduced-motion` query retained as defense-in-depth.

## State Management

`ChatWidget` owns plain private properties:

- `isOpen: boolean`
- `hasStarted: boolean`
- `isLoading: boolean`
- `messages: Message[]`
- `sessionId: string`

Key methods:

- `openPanel()` / `closePanel()` / `togglePanel()`
- `selectSuggestion(text: string)`
- `sendMessage(text: string)`
- `appendMessage(...)` delegates to `message-list.ts`

Child modules render based on the state they receive; they do not mutate global state.

## File Changes

| File | Action | Description |
|---|---|---|
| `frontend/src/chat-widget.ts` | Modify | Slimmer orchestrator; delegates rendering to modules. |
| `frontend/src/fab.ts` | Create | FAB button with avatar and toggle handler. |
| `frontend/src/panel.ts` | Create | Panel shell, header, and close button. |
| `frontend/src/zero-state.ts` | Create | Greeting and three suggestion cards. |
| `frontend/src/message-list.ts` | Create | User/agent/error bubbles and source citations. |
| `frontend/src/input-bar.ts` | Create | Bottom toolbar with send, voice placeholder, and model selector placeholder. |
| `frontend/src/api-client.ts` | Create | Fetch wrapper for `/api/ask` with timeout and error mapping. |
| `frontend/src/styles.css` | Modify | Dark theme, side-panel layout, zero-state, input bar, no animations. |
| `frontend/src/main.ts` | Unchanged | Bootstrap logic stays the same. |
| `frontend/index.html` | Unchanged | Mount point stays the same. |

## Interfaces / Contracts

### Frontend types (unchanged)

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

### Internal message type

```typescript
interface Message {
  id: string;
  sender: 'user' | 'agent' | 'error';
  text: string;
  sources?: Source[];
}
```

## Accessibility

- Move focus to the text input on panel open; restore focus to the FAB on close.
- `aria-label` on every icon-only button (FAB, close, send, voice).
- FAB uses `aria-controls="chat-panel"` and `aria-expanded`.
- Panel uses `role="dialog"` and `aria-label="Chat con Cerito"`.
- Suggestion cards are real `<button>` elements with visible focus rings.
- Message list uses `role="log"` and `aria-live="polite"`.
- Escape key closes the panel.

## Testing Strategy

| Layer | What to Test | Approach |
|---|---|---|
| Build | TypeScript compiles and Vite bundles | `cd frontend && pnpm build` |
| API contract | `AskRequest`/`AskResponse` unchanged | Existing `uv run python -m pytest tests/ -v` |
| Manual / a11y | Focus order, keyboard navigation, screen-reader labels | Checklist during review |
| Visual | Panel width at 1280px and 480px, FAB visibility, zero-state presence | Browser dev tools |

## Migration / Rollout

No backend migration is required. Rollout steps:

1. Run `cd frontend && pnpm install && pnpm build`.
2. Verify `pnpm build` exits cleanly.
3. Run `uv run python -m pytest tests/ -v`.

## No Animations Constraint Enforcement

- No `@keyframes` rules.
- No `transition` properties.
- No JavaScript animation loops or `requestAnimationFrame`.
- No CSS `transform` used for motion.
- Panel visibility toggled via `display` (or `visibility`) only.
- `prefers-reduced-motion` media query kept as a safety net.

## Open Questions

None.
