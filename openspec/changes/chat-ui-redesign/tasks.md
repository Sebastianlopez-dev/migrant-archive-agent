# Tasks: Chat UI Redesign

## Review Workload Forecast

| Field | Value |
|-------|-------|
| Estimated changed lines | ~1,600–1,800 (additions + deletions) |
| 400-line budget risk | High |
| Chained PRs recommended | Yes |
| Suggested split | PR 1 (foundation) → PR 2 (shell) → PR 3 (zero-state + input) → PR 4 (message list) → PR 5 (integration + a11y) |
| Delivery strategy | ask-on-risk |
| Chain strategy | pending (ask user: stacked-to-main or feature-branch-chain) |

Decision needed before apply: Yes
Chained PRs recommended: Yes
Chain strategy: pending
400-line budget risk: High

### Suggested Work Units

| Unit | Goal | Likely PR | Depends on | Notes |
|------|------|-----------|------------|-------|
| 1 | API client + shared types | PR 1 | — | Independent foundation |
| 2 | FAB + Panel + shell styles | PR 2 | PR 1 | Base side-panel shell |
| 3 | Zero-state + Input-bar + their styles | PR 3 | PR 2 | Content above the fold |
| 4 | Message-list + message styles | PR 4 | PR 2 | Conversation rendering |
| 5 | Chat-widget integration + a11y + final styles + verification | PR 5 | PR 1–4 | Brings modules together |

## Phase 1: Foundation

- [x] **T001 — Create `frontend/src/api-client.ts` with types and fetch wrapper**
  - Export `Source`, `AskResponse`, `Message` interfaces and `ask(sessionId, question)`.
  - Include 60 s timeout, `AbortController`, and error mapping.
  - Estimated lines: +70
  - Acceptance: TypeScript compiles; `ask()` returns typed response and maps errors.
  - Commit: `feat(chat): add api-client module with ask wrapper`

## Phase 2: Shell Modules

- [ ] **T002 — Create `frontend/src/fab.ts` floating action button module**
  - Render fixed button with avatar, `aria-controls="chat-panel"`, `aria-expanded`, `aria-label`.
  - Accept click callback; hide/show controlled by orchestrator.
  - Estimated lines: +50
  - Acceptance: FAB renders, click callback fires, ARIA attributes correct.
  - Commit: `feat(chat): add floating action button module`

- [ ] **T003 — Create `frontend/src/panel.ts` panel shell module**
  - Render `section#chat-panel` with `role="dialog"`, header, title avatar, close button.
  - Accept close callback and content container reference.
  - Estimated lines: +70
  - Acceptance: Panel renders with correct ARIA, close callback fires.
  - Commit: `feat(chat): add panel shell module`

## Phase 3: Content Modules

- [ ] **T004 — Create `frontend/src/zero-state.ts` greeting and suggestions module**
  - Render greeting "Hola, soy Cerito", purpose text, and three suggestion buttons.
  - Use exact labels from spec; accept click callback.
  - Estimated lines: +80
  - Acceptance: All three suggestion cards visible with correct labels and click handlers.
  - Commit: `feat(chat): add zero-state greeting and suggestions`

- [ ] **T005 — Create `frontend/src/input-bar.ts` bottom input module**
  - Render text input, send button, disabled microphone placeholder, model selector placeholder.
  - Handle Enter key and submit callback; microphone button does nothing.
  - Estimated lines: +100
  - Acceptance: Input, send, voice placeholder render; Enter triggers submit; voice button is inert.
  - Commit: `feat(chat): add input bar with voice placeholder`

- [ ] **T006 — Create `frontend/src/message-list.ts` conversation module**
  - Render user/agent/error bubbles, source citations, YouTube links, scroll-to-bottom.
  - Port escaping, source linkification, and time parsing from existing widget.
  - Estimated lines: +150
  - Acceptance: Messages render; sources link to YouTube at correct timestamp; list scrolls.
  - Commit: `feat(chat): add message list module with source citations`

## Phase 4: Integration and Styles

- [ ] **T007 — Refactor `frontend/src/chat-widget.ts` as orchestrator**
  - Import T001–T006 modules; manage `isOpen`, `hasStarted`, `isLoading`, `messages`, `sessionId`.
  - Wire open/close, suggestion send, message send, loading state, focus management.
  - Estimated lines: ~−160 net; ~460 diff
  - Acceptance: Widget opens/closes via FAB and close button; messages send; suggestions send.
  - Commit: `refactor(chat): rewrite chat-widget as module orchestrator`

- [ ] **T008 — Rewrite `frontend/src/styles.css` for dark theme and layout**
  - Dark palette with `--blue: #019ee3`; FAB/panel layout; zero-state; messages; input bar.
  - Panel width `30vw` bounded `320px–480px`; full width below `640px`.
  - Remove all `transition`, `@keyframes`, transform motion.
  - Estimated lines: ~−40 net; ~680 diff
  - Acceptance: Build passes; no `transition` or `@keyframes` rules remain; responsive widths correct.
  - Commit: `feat(chat): apply dark theme and side-panel layout styles`

- [ ] **T009 — Add keyboard navigation and focus management**
  - Escape closes panel; focus input on open; restore focus to FAB on close; visible focus rings.
  - Verify all icon-only buttons have `aria-label`.
  - Estimated lines: +40
  - Acceptance: Escape works; focus moves correctly; a11y checklist passes.
  - Commit: `feat(chat): add keyboard navigation and focus management`

## Phase 5: Verification

- [ ] **T010 — Verify build and backend contract**
  - Run `cd frontend && pnpm install && pnpm build`.
  - Run `uv run python -m pytest tests/ -v`.
  - Estimated lines: 0–20
  - Acceptance: `pnpm build` exits 0; backend tests pass; no CSS animations/transitions remain.
  - Commit: `test(chat): verify build and api contract after redesign`
