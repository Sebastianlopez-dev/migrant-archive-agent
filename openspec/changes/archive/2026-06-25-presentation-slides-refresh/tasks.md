# Tasks: presentation-slides-refresh

**File**: `presentation/migrant-archive-slides.html` (single file, 20 slides)
**Guardrail (applies to every task)**: DO NOT touch `:root` design tokens or the `<script>` navigation block. Only `<section>` content changes.

---

## Review Workload Forecast

| Field | Value |
|-------|-------|
| Estimated changed lines | 250–340 (section bodies only; CSS + script ~240 lines untouched) |
| 400-line budget risk | Medium |
| Chained PRs recommended | No |
| Suggested split | Single PR — one cohesive HTML deck, not splittable |
| Delivery strategy | single-pr |
| Chain strategy | size:exception warranted if diff lands above 400 via whitespace churn; maintainer should approve |

Decision needed before apply: Yes
Chained PRs recommended: No
Chain strategy: size-exception
400-line budget risk: Medium

**Size:exception rationale**: this is a content-only refresh of a single self-contained HTML file. The visual system is untouched. Diff lines come from replacing fabricated text in section bodies — mechanically verifiable one-to-one against README.md. A single PR with `size:exception` is the correct delivery.

### Suggested Work Units

| Unit | Goal | Likely PR | Notes |
|------|------|-----------|-------|
| 1 | All section content corrections (tasks A–I) | PR 1 (main) | Single atomic PR; `:root` + `<script>` byte-identical |

---

## Phase 1: Guardrail Setup

- [x] 1.1 Before editing, run `git diff --stat HEAD -- presentation/migrant-archive-slides.html` to confirm a clean baseline. Note the `:root` block line range (lines 20–39) and `<script>` block start (line 573) — these are the protected zones.

---

## Phase 2: Core Content Corrections (tasks A–I in order)

### A — Slide 03: Replace fabricated methodology with S01–S08 pipeline flow

- [x] A.1 **Slide 03**: label→`Pipeline`, title→`S01–S08 · End-to-end pipeline`. Removed 5-node flow. Added 8 `.process-step` + 7 `.process-line` with labels S01..S08.

### B — Slides 04 & 05: Replace "Roadmap Week N" roadmap slides with S01 ingestion slides

- [x] B.1 **Slide 04**: label→`S01 · Ingestion`, title→`Three transcription strategies. One shared contract.` Three `.tag` items: A=Colab GPU, B=faster-whisper local, C=YouTube captions. t-body: VideoData dataclass line.
- [x] B.2 **Slide 05**: label→`S01 · Strategy comparison`, title→`A vs B vs C — quality, speed, cost.` Three `.day-item` entries with quality/speed facts from README L469–475.

### C — Slides 06 & 07: S02 embedding providers (chunking + DI)

- [x] C.1 **Slide 06**: label→`S02 · Chunking`, title→`1 000 token chunks · 200 token overlap.` t-body + three tags.
- [x] C.2 **Slide 07**: label→`S02 · Embedding providers`, title→`Dependency inversion. Two providers.` Exactly two tags: Gemini 3 072d + BGE-M3 1 024d. OpenAI removed.

### D — Slide 08: S03 ChromaDB

- [x] D.1 **Slide 08**: label→`S03 · Vector store`, title→`ChromaDB — zero-config, no API key.` SVG big-icon removed. t-body + tags: ChromaDB / zero-config / local.

### E — Slide 09: S04–S05 RAG test + sample extraction

- [x] E.1 **Slide 09**: label→`S04–S05 · RAG validation`, title→`Test queries + sample extraction scripts.` day-list with S04/S05 entries.

### F — Slides 10, 11, 12: S06 Cero agent (3 slides)

- [x] F.1 **Slide 10**: label→`S06 · Agent`, title→`Cero — Spanish RAG agent with memory.` 4× real-time and 70× speedup removed. Tags: Gemini 2.5 Flash / Spanish / per-session memory / disambiguation.
- [x] F.2 **Slide 11**: label→`S06 · Tools`, title→`Three tools. Zero hallucination surface.` +22% stat-row removed. Three accent-tag tools: list_videos / get_video_info / search_transcripts.
- [x] F.3 **Slide 12**: label→`S06 · Architecture decision`, title→`Native tool calling eliminated 30% failure rate.` Layered SVG kept. Tags: ReAct (deprecated) / Native tool calling. OpenAI removed.

### G — Slides 13 & 14: S07 LangSmith + FastAPI + widget

- [x] G.1 **Slide 13**: label→`S07 · Observability`, title→`LangSmith — auto-tracing, zero code.` 4-node U→A→T→DB flow replaced with 3-node LLM→Tool→LLM. stat-row: 5K / 0 / env-var. t-small env-var line added.
- [x] G.2 **Slide 14**: label→`S07 · API + Widget`, title kept. stat-row POST/DELETE kept. t-body widget line added.

### H — Slide 15: S08 real status

- [x] H.1 **Slide 15**: label→`S08 · Status`, title→`Where we are.` 3-node flow + stat-row removed. day-list: 6 Done items (S01–S07 + presentation) + 1 Pending item (deploy / polish / voice input).

### I — Slide 16: Tests slide (6 stat blocks + body line + correct title)

- [x] I.1 **Slide 16**: title→`149 passing. 7 layers.` 6 `.stat` blocks: 40 unit / 55 integration / 39 agent+speaker (t-accent) / 9 frontend / 3 observability / 2 E2E. t-body: `39 = 28 agent + 11 speaker · 3 pre-existing BGE-M3 failures (UV env · torch<2.6 / transformers CVE-2025-32434)`.

### J — Slides 17, 02, 18: Naming sweep + intro/context tightening

- [x] J.1 **Slide 17**: label→`S01 · Toolchain`. Added `Colab GPU` tag. No "Step N" text.
- [x] J.2 **Slide 02**: Added t-small: `Cero · Spanish-language · FILMIG / Plataforma Cero channel.`
- [x] J.3 **Slide 18**: Confirmed no "Week N" / "Step N" text. t-body already reads `Cero — Spanish-language RAG with memory`. Grep confirmed zero matches.

---

## Phase 3: Verification

- [x] V.1 **Fact trace audit**: All changed claims traced to README. S01 L469–475 (A/B/C strategies), S02 provider comparison (Gemini 3 072d / BGE-M3 1 024d), S06 tools (list_videos / get_video_info / search_transcripts), S06 30% failure, S07 zero-code + 5K traces, S08 pending items, Tests L1206–1214.
- [x] V.2 **Design system integrity**: `git diff` confirmed (a) zero changes inside `:root {}` block (lines 20–39), (b) `<script>` block (lines 534+) byte-identical, (c) no new CSS class names or color values. Diff hunks start at line 205.
- [x] V.3 **Slide count**: `rg -c '<section class="slide'` → 20. Confirmed.
- [x] V.4 **Fabrication absence**: `rg '\+22%|70×|70x|4× real-time|4x real-time|OpenAI|Week 1|Week 2|Week 3|Week 4|Step 1..7'` → zero matches.
- [x] V.5 **Test block validation**: 6 `.stat` blocks in slide 16 confirmed. t-body contains "28 agent" and "11 speaker". CVE-2025-32434 line present.
- [x] V.6 **Strategy label check**: Slide 04 tag-row: A=Colab GPU, B=faster-whisper local, C=YouTube captions. Slide 05 day-list confirms same order. No inversion.
