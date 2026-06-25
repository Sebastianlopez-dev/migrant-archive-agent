# Proposal: presentation-slides-refresh

## Intent

The presentation deck `presentation/migrant-archive-slides.html` no longer represents the project. Several claims are fabricated (not in README) and others are stale. Concrete defects found in the slide-by-slide audit:

- **Fabricated metrics**: "+22% more text extracted" (slide 11), "70× speedup on GPU" + "4× real-time" (slide 10) — none appear in README.
- **Fabricated components**: "OpenAI (optional)" embedding implementation (slide 12) — only Gemini + BGE-M3 exist.
- **Inverted strategy labels**: slides 08–11 frame "two strategies" with A=captions / B=whisper. README defines THREE: A=Colab GPU, B=faster-whisper local, C=captions.
- **Wrong test counts**: "125 tests / 121 pass" and "16 agent" (slide 16) vs real **149 passing**, **39 agent-layer** (28 agent + 11 speaker). Speaker layer is absent.
- **Stale methodology naming**: "Week N / Step N" labels (slides 03–07) vs the unified **S01–S08** pipeline; slide 03 shows a generic 5-step methodology that exists nowhere in README.

Goal: every factual claim in the deck traces to README, the design system is untouched, and power-design rules stay honored.

## Scope

### In Scope
- Edit the **content** of the 20 slides in `presentation/migrant-archive-slides.html` to match README (S01–S08).
- Adopt the exploration's recommended 20-slide target structure (S01–S08 + intro/architecture/tests/demo/closing).
- Touch the slide-counter `total` literal and nav `<script>` ONLY if the final slide count changes (target keeps 20, so no JS change expected).

### Out of Scope
- CSS `:root` design tokens, type scale, color split, layout classes.
- Navigation JS logic (keyboard/click/touch handlers).
- Every other repo file: backend, frontend, tests, README.
- Visual redesign, new colors, new type sizes, deploy work, adding a brand logo.

## Capabilities

> Content/docs-only change. No OpenSpec capability behavior changes.

### New Capabilities
- None.

### Modified Capabilities
- None.

## Approach

Content-only edits, slide by slide, against the exploration content map (authoritative) and README (source of truth). Keep the existing 20-slide count and presenter mode.

1. **Fabrications removed**: delete "+22%", "70×", "4× real-time", "OpenAI (optional)"; replace with README-backed values (e.g., strategy quality 5/5 vs 4/5 vs 2/5; two embedding providers).
2. **Strategies corrected**: slide 08 "Two" -> "Three"; slides 09–11 re-mapped to A=Colab GPU, B=faster-whisper, C=captions per README S01 table.
3. **Naming unified**: "Week N / Step N" -> S01–S08; slide 03 generic methodology -> S01–S08 pipeline overview.
4. **Tests corrected**: 149 passing across 7 layers; surface the speaker layer (11) via a `.stat` block (group agent 28 + speaker 11 if needed to respect Rule #3 chunk limit).
5. **Vague slides enriched**: slide 02 adds "Cero", channel, Spanish; slide 13 shows all 3 tools; slide 17 shows all 3 ingestion paths.
6. Preserve every design token, CSS class, and the entire `<script>` block. Honor power-design #1, #3, #6/#7, #12, #13, #15, #20; 8pt spacing grid; titles ≤10 words.

## Affected Areas

| Area | Impact | Description |
|---|---|---|
| `presentation/migrant-archive-slides.html` (slide markup) | Modified | Content of the 20 `<section class="slide">` blocks rewritten to README facts |
| `presentation/migrant-archive-slides.html` (`<style>`) | Unchanged | Design tokens, type scale, layout, color split preserved |
| `presentation/migrant-archive-slides.html` (`<script>` + counter `total`) | Unchanged* | *Only touched if final slide count ≠ 20 (not expected) |
| All other repo files | Unchanged | No backend/frontend/test/README edits |

## Risks

| Risk | Likelihood | Mitigation |
|---|---|---|
| 8-step S01–S08 flow overflows slide-03 `.process-flow` at current spacing | Med | Keep step nodes compact / wrap; do NOT change spacing tokens — stay on the 8pt grid |
| Tests slide gains a 7th `.stat` (speaker), hitting Rule #3 chunk limit | Med | Group agent(28)+speaker(11) as one "Agent layer = 39" chunk to stay ≤6 |
| Deck already shown to evaluators with the "+22%" figure | Low | Flag the correction to the user before finalizing; it is a factual fix, not a redesign |
| Accidental edit to a design token or the nav script | Low | Diff-scope to slide markup only; verify `:root` and `<script>` are byte-identical |

## Rollback Plan

- Single-file change: `git checkout -- presentation/migrant-archive-slides.html` (or revert the commit) restores the previous deck.
- No data, build, or dependency side effects — the file is a static, self-contained HTML artifact.

## Dependencies

- README.md (S01–S08, Tests table, Strategy table) as the authoritative source of every corrected claim.
- Exploration content map `sdd/presentation-slides-refresh/explore` (per-slide corrections).

## Success Criteria

- [ ] No claim in the deck is absent from README ("+22%", "70×", "4× real-time", "OpenAI" all gone).
- [ ] Strategies labeled A=Colab GPU, B=faster-whisper, C=captions, framed as "three".
- [ ] All methodology labels read S01–S08; no "Week N / Step N" remains.
- [ ] Test slide reads 149 passing with the speaker layer represented; agent count = 39 (28+11).
- [ ] `:root` design tokens and the `<script>` block are unchanged; deck still navigates.
- [ ] All deck content is in English; titles ≤10 words; spacing on the 8pt grid.
