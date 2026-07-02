# Design: Cero UI Polish

## Technical Approach

Two isolated frontend-only changes in `message-list.ts` and `styles.css`. No backend, no new dependencies, no build config changes. Scope is strictly limited to light-mode input contrast fix and localized rotating loading messages.

1. **CSS fix**: Add `color: var(--gray-900)` to the existing `[data-theme="light"] .chat-input` rule block (line ~815 of `styles.css`). The base `.chat-input` at line 668 sets `color: var(--white)`; the light-theme override already adjusts `border-color` and `background` but never overrides `color`, causing white text on the light `rgba(0,0,0,0.04)` background.

2. **Loading rotation**: Replace `LOADING_I18N: Record<string, string>` with `Record<string, string[]>` containing 4 archive-themed messages per language. Add `setInterval`-based cycling in `setLoading(true)`, cleared on `setLoading(false)` and `clear()`. Timer lifecycle stays co-located in `message-list.ts` — no timer logic leaks across module boundaries.

## Architecture Decisions

| # | Choice | Alternatives considered | Rationale |
|---|--------|------------------------|-----------|
| 1 | Rotation timer lives in `message-list.ts` | `chat-widget.ts` via `setInterval` in `sendMessage`/`finally` | The message list already owns the loading indicator DOM and its text. Keeping the timer here co-locates lifecycle management with the element it controls. |
| 2 | 2.5-second rotation interval | 1.5s, 3s, 5s | 2.5s gives enough time to read a short phrase without feeling sluggish. |
| 3 | Guard against double intervals with `rotationTimer` flag | `clearInterval` before every `setInterval` | The `if (rotationTimer) return;` guard inside `setLoading(true)` prevents the re-append on line 97 from creating a second interval. |

## Data Flow

```
ChatWidget.sendMessage()
  └─ this.setLoading(true)          // guards with this.isLoading
       └─ messageList.setLoading(true)
            ├─ creates/recovers loadingIndicator
            ├─ gets initial message from LOADING_I18N[currentLang][0]
            └─ starts setInterval → cycles index every 2.5s
                                          │
  ...await ask(...)                       │
  ...addAgentResponse(...)                │
                                          │
  finally:                                │
    this.setLoading(false)                │
      └─ messageList.setLoading(false) ───┘
           ├─ clearInterval(rotationTimer)
           ├─ rotationTimer = null
           └─ removes loadingIndicator from DOM
```

## File Changes

| File | Action | Description |
|------|--------|-------------|
| `frontend/src/styles.css` | Modify | Add `color: var(--gray-900)` inside `[data-theme="light"] .chat-input` block (~line 818) |
| `frontend/src/message-list.ts` | Modify | Change `LOADING_I18N` to `Record<string, string[]>`, add 4 messages per language, add `rotationTimer` + `rotationIndex`, update `setLoading`/`clear`/`setLanguage` for timer lifecycle |

## Interfaces / Contracts

No API changes. `MessageListApi` signatures are unchanged — the timer is an internal implementation detail. Only `LOADING_I18N` changes shape:

```typescript
// message-list.ts — internal constant (replaces old Record<string, string>)
const LOADING_I18N: Record<string, string[]> = {
  en: [
    'Consulting the archive...',
    'Cero is reviewing testimonies...',
    'Cross-referencing oral histories...',
    'Tracing stories through the archive...',
  ],
  es: [
    'Consultando el archivo...',
    'Cero está revisando testimonios...',
    'Cotejando historias orales...',
    'Rastreando relatos en el archivo...',
  ],
  ca: [
    'Consultant l\'arxiu...',
    'Cero està revisant testimonis...',
    'Constrastant històries orals...',
    'Resseguint relats a l\'arxiu...',
  ],
  fr: [
    'Consultation des archives...',
    'Cero examine les témoignages...',
    'Recoupement des histoires orales...',
    'Parcours des récits dans les archives...',
  ],
  pt: [
    'Consultando o arquivo...',
    'Cero está a rever os testemunhos...',
    'Cruzando histórias orais...',
    'Percorrendo relatos no arquivo...',
  ],
  de: [
    'Archiv wird konsultiert...',
    'Cero sichtet die Zeugnisse...',
    'Mündliche Überlieferungen werden abgeglichen...',
    'Geschichten im Archiv werden nachverfolgt...',
  ],
};
```

## Testing Strategy

| Layer | What to Test | Approach |
|-------|-------------|----------|
| Visual | Light-mode input text is readable | Manual: open widget in light theme, type text, verify contrast |
| Manual | Loading messages rotate across all six languages | Open widget, send query, observe messages change during API call and disappear on response. Switch language during loading to verify pool change. |
| Manual | No residual interval after close | Open/close panel rapidly while request pending; check no JS errors in console |

No automated frontend tests exist. The change scope (one CSS line + one module refactor) makes manual verification proportionate.

## Migration / Rollout

No migration required. Revert both files to undo.

## Open Questions

None.
