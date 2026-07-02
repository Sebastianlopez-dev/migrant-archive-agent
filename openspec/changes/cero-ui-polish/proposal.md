# Proposal: Cero UI Polish

## Intent

Fix the light-mode input text contrast bug (white text invisible on light background) and replace the static `Cero is thinking...` loading message with rotating Cero/archive-themed messages across all six supported UI languages.

## Scope

### In Scope
- Fix `.chat-input` typed-text color in `[data-theme="light"]` so it is readable on the light input background
- Replace single-string `LOADING_I18N` with per-language arrays of archive-themed messages
- Timed rotation through loading messages while the API request is pending
- Full i18n: en, es, ca, fr, pt, de with product-intent tone (Cero moving through the archive)

### Out of Scope
- CeroState character component or CSS character animations
- GIFs or animated visual indicators
- Backend behavior changes
- Adding languages beyond the existing six

## Capabilities

### New Capabilities
None

### Modified Capabilities
- `chat-widget`: loading indicator MUST cycle through a set of localized Cero/archive-themed messages while the API request is pending, replacing the static single-message approach

## Approach

1. **CSS fix**: Add `color: var(--gray-900)` to `[data-theme="light"] .chat-input` in `frontend/src/styles.css`. One-line addition to an existing light-theme rule block.

2. **Loading rotation**: Change `LOADING_I18N` from `Record<string, string>` to `Record<string, string[]>` with 4-5 archive-themed messages per language. Add `setInterval`-based cycling in `setLoading(true)`, cleared on `setLoading(false)`. Existing `msg-loading` structure stays unchanged.

## Affected Areas

| Area | Impact | Description |
|------|--------|-------------|
| `frontend/src/styles.css` | Modified | Add light-mode `color` override for `.chat-input` |
| `frontend/src/message-list.ts` | Modified | Change `LOADING_I18N` shape, add rotation timer logic |

## Risks

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| Interval leak on rapid open/close | Low | Clear interval in `setLoading(false)` and guard against double-starts |
| Loading text overlaps with response arrival | Low | Current flow already removes loading indicator before appending response |

## Rollback Plan

Revert both files. Changes are isolated: one CSS rule + one i18n constant and timer in `setLoading`. No database, API, or build changes.

## Dependencies

None. Purely frontend changes, no backend or external dependencies.

## Success Criteria

- [ ] Typed text in light-mode chat input is visible against the input background
- [ ] Loading indicator shows at least 3 distinct archive-themed messages per language
- [ ] Messages rotate on a timed interval while the API request is pending
- [ ] All six supported languages (en, es, ca, fr, pt, de) have localized loading messages
- [ ] Existing tests pass without modification
