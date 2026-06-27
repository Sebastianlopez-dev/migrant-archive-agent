# Proposal: Chat UI Redesign

## Intent

Redesign the existing `chat-widget` frontend to follow LangSmith-inspired conversational UI patterns. The current widget works but presents a blank initial state and no guidance. The redesign will add a friendly greeting, one-click preview questions, a collapsible side-panel, and a bottom-anchored input bar so general-public visitors can start interacting with Cero immediately.

## Scope

### In Scope
- Replace the floating bubble + slide-out panel pattern with a collapsible side-panel (≈30% width) that toggles from a floating action button (FAB).
- Add a zero-state greeting with an animated agent avatar on first open.
- Add three clickable suggestion cards: "¿Qué es FILMIG?", "¿Qué videos puedo encontrar de Plataforma Cero?", "¿Qué es mujeres del maíz?".
- Redesign the input area as a bottom-anchored toolbar with integrated send and a placeholder voice button.
- Apply a dark theme with the existing brand blue accent.
- Keep the Vite + vanilla TypeScript stack and zero runtime dependencies.

### Out of Scope
- Voice input implementation (placeholder only).
- Model selector / LLM routing.
- Thread history / multiple conversation threads.
- Reading main-page context into the agent.
- Backend API changes.

## Capabilities

### New Capabilities
- None.

### Modified Capabilities
- `chat-widget`: UI behavior changes to a side-panel + FAB layout, zero-state suggestions, greeting animation, and bottom-anchored input toolbar.

## Approach

Build on the completed `api-chat-frontend` implementation. Keep `POST /api/ask`, the `ChatWidget` class, and `Source` rendering unchanged. Refactor DOM creation and CSS to support the new layout:

1. Render a fixed FAB in the bottom-right when the panel is closed.
2. Render a fixed side-panel on the right (≈30% width, min 320px, max 480px) when open.
3. On first open, show a zero-state view with the greeting animation and suggestion cards; hide it after the first user message.
4. Animate the FAB logo with a subtle scale/fade when the panel opens.
5. Anchor the input bar at the bottom of the panel with the text field, send button, and a disabled voice button with `aria-label`.

Use CSS custom properties for the dark palette and `prefers-reduced-motion` to disable animations.

## Affected Areas

| Area | Impact | Description |
|------|--------|-------------|
| `frontend/src/chat-widget.ts` | Modified | New DOM structure for FAB, side-panel, zero-state, and input toolbar. |
| `frontend/src/styles.css` | Modified | Dark theme, side-panel layout, suggestion cards, animation keyframes. |
| `frontend/src/main.ts` | Unchanged | Bootstrap logic remains the same. |
| `frontend/index.html` | Unchanged | Mount point remains the same. |

## Risks

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| Small viewports make the 30% panel unusable | Med | Use `min-width` and fall back to full-width below 640px. |
| Animation triggers motion sensitivity | Low | Respect `prefers-reduced-motion`. |
| Suggestion click path adds state complexity | Low | Toggle a single `hasStarted` flag; keep rendering deterministic. |
| Focus order breaks with hidden FAB | Low | Move focus to the panel input on open; restore focus to FAB on close. |

## Rollback Plan

1. Revert `frontend/src/chat-widget.ts` and `frontend/src/styles.css` to the versions from `api-chat-frontend`.
2. The backend and bootstrap code remain untouched, so the previous widget behavior is restored.

## Dependencies

- `api-chat-frontend` implementation must be complete (it is).

## Success Criteria

- [ ] FAB is visible when panel is closed and hidden when open.
- [ ] Panel opens as a right side-panel occupying ≈30% width on desktop.
- [ ] Greeting animation plays on first open.
- [ ] Three suggestion cards are clickable and send their text as a question.
- [ ] Input bar stays anchored at the bottom of the panel.
- [ ] Existing `uv run python -m pytest tests/ -v` continues to pass.
- [ ] Widget builds with `pnpm build`.
