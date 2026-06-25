# Archive Report — presentation-slides-refresh

**Date:** 2026-06-25
**Status:** Completed and verified (pass-with-warnings → warnings remediated)

## Summary

Content-only refresh of `presentation/migrant-archive-slides.html` (20-slide deck) so every
claim traces to `README.md` (S01–S08). The visual design system — `:root` tokens, layout
classes, and the `<script>` navigation block — was left byte-identical.

## Outcome

- Removed fabricated claims: "+22% more text", "OpenAI (optional)", "70× speedup", "4× real-time".
- Corrected ingestion strategy labels: A = Colab GPU (recommended), B = faster-whisper local, C = captions.
- Fixed test count: 149 passing, 7 layers (6 `.stat` blocks; agent+speaker merged to 39; body line surfaces 28 + 11).
- Unified naming: "Week N / Step N" → S01–S08.
- S02 provider inversion: Gemini 3072d + BGE-M3 1024d (no third provider).
- S06 Cero: 3 tools + per-session memory + disambiguation. S07 LangSmith zero-code + FastAPI + widget. S08 real status.

## Verify result

`pass-with-warnings` (0 CRITICAL). 2 warnings remediated post-verify + 2 suggestions applied:

- WARNING-01: slide 13 env vars `LANGCHAIN_*` → `LANGSMITH_API_KEY + LANGSMITH_TRACING=true`.
- WARNING-02: slide 09 "5 curated queries" → "interactive semantic search".
- SUGGESTION-01: `~30%` qualifier restored (slide 12).
- SUGGESTION-02: widget copy aligned to README — "Vanilla TypeScript, zero runtime deps. Blue bubble, slide-out panel, clickable source links." (slide 14).

## Integrity

- `:root` and entire `<script>` confirmed unchanged via `git diff`.
- 20 slides preserved; JS counter `total` (= `slides.length`) untouched.
- Diff: 144 insertions / 183 deletions.

## Known upstream issues (out of scope for this change)

1. **README test-count inconsistency.** The Tests-table layers sum to 148 (40+55+28+11+9+3+2) but the README states "149 passing". The deck mirrors the README headline ("149 passing. 7 layers."). Reconciling the README is a separate change.
2. **README Strategy A/B label inconsistency.** The S01 file-tree comments (README L384–386) label `ingestion_caption.py` as "Strategy A", while the S01 comparison table (L469) labels Colab GPU as "A". The deck follows the comparison table (canonical, presentation-facing).

## Persisted artifacts (Engram, project `migrant-archive-agent`)

- `sdd/presentation-slides-refresh/explore`
- `sdd/presentation-slides-refresh/proposal`
- `sdd/presentation-slides-refresh/spec`
- `sdd/presentation-slides-refresh/design`
- `sdd/presentation-slides-refresh/tasks`
- `sdd/presentation-slides-refresh/apply-progress`
- `sdd/presentation-slides-refresh/verify-report`

## Spec promotion

`openspec/specs/presentation-content/spec.md` (new capability baseline).
