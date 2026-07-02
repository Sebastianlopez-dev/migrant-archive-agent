# Tasks: Cero UI Polish

## Review Workload Forecast

| Field | Value |
|-------|-------|
| Estimated changed lines | ~60 |
| 800-line budget risk | Low |
| Chained PRs recommended | No |
| Suggested split | Single PR |
| Delivery strategy | single-pr |

Decision needed before apply: No
Chained PRs recommended: No
Chain strategy: pending
800-line budget risk: Low

### Suggested Work Units

| Unit | Goal | Likely PR | Notes |
|------|------|-----------|-------|
| 1 | Light-mode input contrast + rotating loading messages | PR 1 | Both changes in one PR; under 60 lines total |

## Phase 1: CSS Fix — Light-Mode Input Contrast

- [x] 1.1 Add `color: var(--gray-900);` inside `[data-theme="light"] .chat-input { ... }` block at line ~818 of `frontend/src/styles.css`

## Phase 2: Rotating Localized Loading Messages

- [x] 2.1 Change `LOADING_I18N` in `frontend/src/message-list.ts` from `Record<string, string>` to `Record<string, string[]>` with 4 archive-themed messages per language (en, es, ca, fr, pt, de)
- [x] 2.2 Add `rotationTimer` (`ReturnType<typeof setInterval> | null`) and `rotationIndex` (`number`) variables inside `createMessageList()`
- [x] 2.3 In `setLoading(true)`: set initial text from `LOADING_I18N[currentLang][0]`, start `setInterval` (2.5s) cycling `rotationIndex` and updating `loadingIndicator.textContent`, guard against double intervals (`if (rotationTimer) return` before starting)
- [x] 2.4 In `setLoading(false)`: `clearInterval(rotationTimer)`, null the timer, remove loadingIndicator from DOM
- [x] 2.5 In `clear()`: `clearInterval(rotationTimer)`, null the timer, then empty DOM and null `loadingIndicator`
- [x] 2.6 In `setLanguage()`: if `rotationTimer` is active, clear it, reset `rotationIndex` to 0, update `loadingIndicator.textContent` to new language's first message, restart interval

## Phase 3: Manual Verification

- [x] 3.1 Light-mode input text readable (WCAG AA): open widget in light theme, type text, verify dark/visible
- [x] 3.2 Dark theme input unaffected: open widget in dark theme, type text, verify unchanged appearance
- [x] 3.3 Loading messages rotate every ~2.5s while API request is pending across all six languages
- [x] 3.4 Rotation stops cleanly on response: no stale interval, loading indicator removed from DOM
- [x] 3.5 `setLanguage` during active loading restarts rotation from new language's first message
- [x] 3.6 Rapid open/close during loading does not leak intervals (check browser console for errors)

## Phase 4: Loading Text Synchronization Regression Fix

- [x] 4.1 Fix `setLoading(true)` in `frontend/src/message-list.ts` to reset `rotationIndex` to 0 and synchronize `loadingIndicator.textContent` from `getLoadingText()` before appending/starting rotation
- [x] 4.2 Add static regression test in `tests/test_frontend.py` asserting the synchronization order and guard-exit for reused indicators
