# Apply Progress: Cero UI Polish

## Change

**cero-ui-polish** — frontend-only polish for the chat widget.

## Mode

Strict TDD Mode (`uv run python -m pytest tests/ -v`).

## Completed Tasks

- [x] 1.1 Add `color: var(--gray-900);` inside `[data-theme="light"] .chat-input { ... }` block at line ~818 of `frontend/src/styles.css`
- [x] 2.1 Change `LOADING_I18N` in `frontend/src/message-list.ts` from `Record<string, string>` to `Record<string, string[]>` with 4 archive-themed messages per language (en, es, ca, fr, pt, de)
- [x] 2.2 Add `rotationTimer` (`ReturnType<typeof setInterval> | null`) and `rotationIndex` (`number`) variables inside `createMessageList()`
- [x] 2.3 In `setLoading(true)`: set initial text from `LOADING_I18N[currentLang][0]`, start `setInterval` (2.5s) cycling `rotationIndex` and updating `loadingIndicator.textContent`, guard against double intervals (`if (rotationTimer) return` before starting)
- [x] 2.4 In `setLoading(false)`: `clearInterval(rotationTimer)`, null the timer, remove loadingIndicator from DOM
- [x] 2.5 In `clear()`: `clearInterval(rotationTimer)`, null the timer, then empty DOM and null `loadingIndicator`
- [x] 2.6 In `setLanguage()`: if `rotationTimer` is active, clear it, reset `rotationIndex` to 0, update `loadingIndicator.textContent` to new language's first message, restart interval
- [x] 3.1 Light-mode input text readable (WCAG AA): verified via static test + CSS rule
- [x] 3.2 Dark theme input unaffected: light override is scoped to `[data-theme="light"] .chat-input`
- [x] 3.3 Loading messages rotate every ~2.5s while API request is pending across all six languages
- [x] 3.4 Rotation stops cleanly on response: `stopRotation()` called in `setLoading(false)` path
- [x] 3.5 `setLanguage` during active loading restarts rotation from new language's first message
- [x] 3.6 Rapid open/close during loading does not leak intervals: guarded by `if (rotationTimer) return` in `startRotation()` and cleared on `setLoading(false)` / `clear()`
- [x] 4.1 Fix `setLoading(true)` in `frontend/src/message-list.ts` to reset `rotationIndex` to 0 and synchronize `loadingIndicator.textContent` from `getLoadingText()` before appending/starting rotation
- [x] 4.2 Add static regression test in `tests/test_frontend.py` asserting the synchronization order and guard-exit for reused indicators

## Files Changed

| File | Action | What Was Done |
|------|--------|---------------|
| `frontend/src/styles.css` | Modified | Added `color: var(--gray-900);` to `[data-theme="light"] .chat-input` for light-mode readability |
| `frontend/src/message-list.ts` | Modified | Replaced static `LOADING_I18N` with per-language arrays; added `rotationTimer`, `rotationIndex`, `startRotation()`, `stopRotation()`; updated `setLoading`, `clear`, and `setLanguage` for safe timer lifecycle; fixed `setLoading(true)` to reset `rotationIndex` and refresh text from `getLoadingText()` before appending/starting rotation |
| `tests/test_frontend.py` | Modified | Updated loading-indicator tests for rotating messages; added CSS contrast test and rotation-lifecycle tests; added static regression test for loading-text synchronization on `setLoading(true)` |

## TDD Cycle Evidence

| Task | Test File | Layer | Safety Net | RED | GREEN | TRIANGULATE | REFACTOR |
|------|-----------|-------|------------|-----|-------|-------------|----------|
| 1.1 | `tests/test_frontend.py` | Static source | 225 passed, 1 skipped | Written | Passed | Single rule assertion | Extracted CSS contrast test |
| 2.1-2.6 | `tests/test_frontend.py` | Static source | 225 passed, 1 skipped | Written | Passed | Array shape + timer lifecycle + language coverage | Extracted `stopRotation()` / `startRotation()` helpers; constant `ROTATION_INTERVAL_MS` |
| 4.1-4.2 | `tests/test_frontend.py` | Static source | 63 passed | Written | Passed | Guard-exit + order assertions for reused indicator | Moved text sync and `rotationIndex` reset outside `if (!loadingIndicator)` guard |

### Test Summary

- **Total tests written**: 6 new tests added to `tests/test_frontend.py` across the change (1 regression test added in this fix)
- **Total tests passing**: 230 passed, 1 skipped (full suite)
- **Layers used**: Static source inspection (project has no JS/TS test runner; Python test suite validates frontend artifacts)
- **Approval tests**: None — no refactoring tasks
- **Pure functions created**: `getLoadingText()` remains pure; `stopRotation()` / `startRotation()` encapsulate timer side effects
- **Behavior-level JS testing limitation**: No JavaScript test runner exists in the project, so the regression coverage is a static source assertion that verifies the synchronization code is present and correctly ordered. Runtime language-swap behavior should be validated manually or with a future JS test harness.

## Deviations from Design

None — implementation matches design.

## Issues Found

- Pre-commit review discovered a stale loading-text bug: `setLoading(false)` removed the indicator from the DOM but left the `loadingIndicator` reference and old `textContent` in place. `setLanguage()` only updated the text while the indicator was attached, so a subsequent `setLoading(true)` re-appended the stale text until the 2.5s rotation tick replaced it. Fixed by moving `rotationIndex = 0` and `loadingIndicator.textContent = getLoadingText()` outside the `if (!loadingIndicator)` guard so the text is synchronized every time loading is shown or re-shown.

## Remaining Tasks

None. All tasks complete.

## Workload / PR Boundary

- Mode: single PR
- Current work unit: Cero UI Polish (complete)
- Boundary: entire change applied in one batch
- Estimated review budget impact: ~75 changed lines (well under 800-line budget)

## Status

15/15 tasks complete. Ready for verify.
