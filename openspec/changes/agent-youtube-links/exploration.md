## Exploration: Agent-generated YouTube links

### Current State

The system already produces inline YouTube links for end users, but it does so **downstream of the agent** rather than inside the agent's natural-language response.

- **Agent type**: The codebase uses `create_tool_calling_agent` (native Gemini function calling via `langchain-google-genai`), **not** a ReAct agent. This is explicitly declared in `backend/agents/agent.py` lines 1–5 and 169.
- **System prompt**: Defined as the `SYSTEM_PROMPT` constant in `backend/agents/agent.py` (lines 29–71). It already contains a citation rule:  
  `"When citing, include title and video ID. Example: \"Video: Mujeres del Maiz (mY1hw79ydY0), 07:50\"."`  
  It also explicitly forbids markdown (`"Do NOT use markdown ..."`).
- **Tool observation**: `search_transcripts` in `backend/agents/tools.py` (lines 79–95) emits blocks in the format:  
  `[i] Title [Speaker] (start–end) | video_id\ntext`  
  This includes `video_id`, `start_time`, and `end_time` drawn from chunk metadata.
- **API layer**: `backend/api/routes/chat.py` parses those observation blocks with `_SOURCE_BLOCK_RE` (lines 24–33) and extracts structured `Source` objects containing `video_id`, `title`, `start_time`, `end_time`, and `text`.
- **Frontend layer**: `frontend/src/message-list.ts` already:
  - Builds full YouTube URLs via `buildSourceUrl(videoId, startTime)` → `https://www.youtube.com/watch?v=ID&t=N` (lines 180–184).
  - Renders clickable source cards where the video title links to YouTube (lines 86–136).
  - Linkifies any `video_id` occurrence in the agent's answer text into an `<a>` tag via `linkifySources()` (lines 199–219).

### Affected Areas

- `backend/agents/agent.py` — system prompt definition; adding a URL citation rule would change behavior here.
- `backend/agents/tools.py` — tool observation formatting; could optionally embed a pre-built URL.
- `backend/api/routes/chat.py` — source parsing regex; would need updates if the observation format changes.
- `frontend/src/message-list.ts` — already handles URL building and linkification; would need defensive updates if the agent starts emitting raw URLs.

### Approaches

1. **Instruct the agent to cite with full YouTube URLs** — Add a formatting rule to `SYSTEM_PROMPT` telling the agent to include complete `https://www.youtube.com/watch?v=...&t=...` links inline.
   - Pros: Zero structural code changes; CLI users would see clickable URLs in terminals that support link detection.
   - Cons: Conflicts with the existing `"Do NOT use markdown"` and compact-citation style; Gemini-2.5-flash (temperature 0.2, `tool_config mode: ANY`) already deviates from the no-markdown rule occasionally, so URL obedience is unreliable; long URLs hurt plain-text readability; frontend `linkifySources` would need changes to avoid double-linking or broken HTML if the agent emits raw URLs.
   - Effort: Low

2. **Enhance tool observation with pre-built URLs** — Modify `search_transcripts` in `tools.py` to append a `URL: https://...` line to each observation block.
   - Pros: Agent sees the exact URL and can copy-paste it; minimal prompt changes.
   - Cons: No guarantee the agent will actually include the URL in its final answer (it often paraphrases rather than copying observations verbatim); makes observations longer, consuming extra context window; if the agent ignores the URL, zero user-facing benefit.
   - Effort: Low

3. **Keep current architecture (frontend-driven linkification)** — Rely on the existing `buildSourceUrl` + `linkifySources` + source cards.
   - Pros: Most reliable and deterministic; no dependency on LLM obedience; source cards are always rendered regardless of what the agent mentions in prose; already implemented and tested (`tests/test_frontend.py` asserts `youtube.com/watch` and `t=` presence).
   - Cons: If the agent does not mention the `video_id` in its answer text, `linkifySources` has no inline text to wrap (but the structured source cards below the answer still provide clickable links); CLI users see plain text IDs rather than clickable URLs.
   - Effort: None (already done)

### Recommendation

**Adopt Approach 3 — no change.** The frontend already solves the problem deterministically. Trying to push URL generation into the agent layer introduces unreliability (Gemini flash is not guaranteed to follow formatting instructions), degrades plain-text readability, and creates potential conflicts with the existing frontend linkify logic.

If CLI usability is a concern, a small separate enhancement to `backend/scripts/agent_cli.py` (e.g., post-processing the agent output to wrap video IDs in ANSI hyperlink sequences) is cleaner than coercing the LLM.

### Risks

- **Agent-type misidentification**: The orchestrator prompt refers to a "ReAct agent", but the codebase uses `create_tool_calling_agent`. ReAct-specific assumptions (e.g., `Thought:` / `Action:` parsing) do not apply.
- **LLM instruction drift**: The current prompt already struggles to keep Gemini from using markdown; adding URL formatting instructions may increase drift without improving the user experience.
- **Double-linking / broken HTML**: If the agent emits raw URLs and the frontend simultaneously linkifies video IDs, the resulting HTML could contain nested `<a>` tags or malformed hrefs unless `linkifySources` is updated.
- **start_time accuracy**: Chunk `start_time` is estimated from the first transcript timestamp marker inside the chunk, not the exact semantic match point. It is accurate enough for `&t=N` deep-linking but not frame-perfect.

### Ready for Proposal

**No.** The orchestrator should tell the user: "The frontend already builds YouTube links inline and renders clickable source cards. Making the agent generate URLs would be less reliable and make responses less readable. No backend or agent changes are needed."
