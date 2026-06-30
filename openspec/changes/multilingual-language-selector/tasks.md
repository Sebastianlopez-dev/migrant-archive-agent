# Tasks: multilingual-language-selector

## Review Workload Forecast

| Field | Value |
|-------|-------|
| Estimated changed lines | ~80–100 |
| 400-line budget risk | Low |
| Chained PRs recommended | No |
| Delivery strategy | single-pr |

Decision needed before apply: No

## Implementation Tasks

### Backend

- [x] 1.1 Add `language: str = "en"` field to `AskRequest` in `backend/api/models.py`
- [x] 1.2 Update `backend/agents/agent.py` system prompt to use dynamic `{language}` variable
- [x] 1.3 Update `backend/agents/agent.py` docstring: "Spanish-speaking agent" → "multilingual agent"
- [x] 1.4 Pass `language` to `agent.invoke()` in `backend/api/routes/chat.py`
- [x] 1.5 Add optional `language` query parameter to `POST /api/transcribe` in `backend/api/routes/transcribe.py`
- [x] 1.6 Remove hardcoded `_GROQ_LANGUAGE = "es"` constant; let Groq auto-detect when no language is provided
- [x] 1.7 Update standalone script prompt in `backend/scripts/cero-01.py` to be multilingual

### Frontend

- [x] 2.1 Add `language` parameter to `ask()` and `askQuestion()` in `frontend/src/api-client.ts`
- [x] 2.2 Add `language` state and `setLanguage()` method to `ChatWidget` in `frontend/src/chat-widget.ts`
- [x] 2.3 Pass `this.language` to `ask()` in `frontend/src/chat-widget.ts`
- [x] 2.4 Add language selector `<select>` to panel header in `frontend/src/panel.ts`
- [x] 2.5 Update `createPanel()` signature to accept `onLanguageChange` callback
- [x] 2.6 Add `setVoiceLanguage()` to `InputBarApi` and module-level voice language in `frontend/src/input-bar.ts`
- [x] 2.7 Pass language query param to `/api/transcribe` from `frontend/src/input-bar.ts`
- [x] 2.8 Change `frontend/index.html` `lang` attribute from `es` to `en`

### Validation

- [x] 3.1 Verify `AskRequest` model accepts `language` field
- [x] 3.2 Run `uv run python -m pytest tests/test_api.py -v` — all pass
- [x] 3.3 Run `pnpm exec tsc --noEmit` in `frontend/` — no errors
