# Design: presentation-slides-refresh

## Technical Approach

Rewrite the body of each of the 20 `<section class="slide">` blocks in `presentation/migrant-archive-slides.html` so every claim traces to `README.md`. The visual system is reused verbatim: `:root` tokens, the modular type scale, every layout class, and the entire navigation `<script>` are untouched. The deck stays at 20 slides, so the counter `total` (derived as `slides.length`) needs no change. Only existing CSS classes are used — no new classes, no new colors, no new type sizes, no ad-hoc spacing. The work maps cleanly to the explore content map and resolves the two known layout questions (Slide 03 eight-node flow; Tests slide stat count).

## Architecture Decisions

| Decision | Options | Tradeoffs | Choice |
|---|---|---|---|
| **D1 — Slide 03 fit 8 pipeline nodes (S01..S08)** | (a) Reuse `.process-flow` with 8 `.process-step` + 7 `.process-line`; (b) Convert to 8 `.day-list` rows; (c) Split across two slides | (a) Stays glanceable as one linear flow (power #1 one idea), zero token change, existing `flex-wrap` + `@media (max-width:1024px)` handle overflow; (b) loses the "flow" metaphor, becomes a list; (c) breaks the 20-slide count and needs a `total` change | **(a)** 8 nodes + 7 connectors in existing `.process-flow` |
| **D2 — Tests slide stat count** | (a) Merge Agent 28 + Speaker 11 → one "39 / agent+speaker" `.stat` → 6 stats; (b) Keep 7 separate `.stat` blocks | (a) Lands at power #3 ideal ceiling (6 ≤ 7), fits `.stat-row` flex without wrap, speaker still named in body; (b) hits the hard 7-chunk limit and crowds `.stat-row` | **(a)** 6 `.stat` blocks; speaker surfaced in the body line |
| **CSS policy** | Reuse-only vs. allow small additions | Reuse-only guarantees the visual system and review scope stay minimal; the deck already implements every needed primitive | **Reuse-only** — `:root`, layout classes, `<script>` byte-identical |
| **Strategy labels source** | README S01 comparison table vs. README Project-Structure file comments | The comparison table (A=Colab GPU, B=Whisper local, C=Captions) is the canonical, presentation-facing source; the file-tree comments invert A/B and are an internal inconsistency | Follow the **S01 comparison table** |
| **Counter `total`** | Recompute vs. hardcode | Count stays 20; `total = slides.length` already self-derives | **No JS change** |

## Decision 1 — geometry proof (no spacing tokens change)

`.process-step` circle = 56px; `.process-line` = 64px width + `margin:0 12px` (24px) = 88px per connector.

- Desktop: 8×56 + 7×88 = 448 + 616 = **1064px** < usable width 1920 − 2×96 = 1728px. One row, no wrap.
- ≤1024px (`@media`): circle 44px, line 32px + 24px margin = 56px → 8×44 + 7×56 = 352 + 392 = **744px** < 1024 − 2×48 = 928px. Still one row; `flex-wrap` is the safety net.

The 5-step connector pattern is preserved exactly — N nodes use N−1 `.process-line` spans; 8 nodes → 7 connectors. No connector "breaks" because the markup repeats the identical step/line/step structure.

## Decision 2 — Tests slide `.stat` blocks (6, fits `.stat-row`)

`.stat-row { display:flex; gap:48px }`. Six `.stat` (value `3.2rem` + short label):

| `.stat-val` | `.stat-label` | README source |
|---|---|---|
| 40 | unit | Tests table (line 1208) |
| 55 | integration | Tests table (line 1209) |
| 39 | agent + speaker | Agent 28 (1210) + Speaker 11 (1211) |
| 9 | frontend | Tests table (line 1212) |
| 3 | observability | Tests table (line 1213) |
| 2 | E2E | Tests table (line 1214) |

Body line keeps speaker visible and states the known failures: "39 = 28 agent + 11 speaker · 3 pre-existing BGE-M3 failures (UV env)". Title: "149 passing. 7 layers." (40+55+28+11+9+3+2 = 149).

## Slide-by-slide content specification

All bodies ≤15 words (power #20 presenter mode). Existing classes only; one accent moment per slide (power #13). `[S0x]` = README section.

| # | Label | Title (≤10 words) | Body / tags / stats — every fact `[source]` | Classes |
|---|---|---|---|---|
| 01 | Ironhack AI Engineer Bootcamp | Migrant-Archive · Cero | Subtitle "Sebastian Lopez Largo" [as-is] | `.slide-hero .t-hero .divider .t-body` |
| 02 | Project | RAG chatbot for FILMIG / Plataforma Cero | "Cero answers in Spanish, grounded in real YouTube transcripts." [intro L3-4, S06 L1008] | `.slide-content .t-title .divider .t-body` |
| 03 | Pipeline | S01–S08: one linear pipeline | 8 `.process-step`: S01 Ingest · S02 Embed · S03 ChromaDB · S04 RAG · S05 Sample · S06 Cero · S07 API · S08 Deploy [Pipeline diagram L21-72] | `.process-flow .process-step .process-num .process-label .process-line` |
| 04 | S01 · Ingestion | Three strategies. One shared contract. | big-icon kept. "VideoData JSON — the pipeline never knows which strategy ran." [S01 L77-85] | `.big-icon .t-title .divider .t-body` |
| 05 | S01 · Comparison | Strategy A / B / C | 3 `.day-item`: "A Colab GPU — ~15s, 5/5"; "B Whisper local — ~2min, 4/5"; "C Captions — instant, 2/5, no punctuation" [S01 table L469-475] | `.two-col .big-number .day-list .day-item .day-num` |
| 06 | S02 · Chunking | Chunking + Embedding | tags: "1000 tok / 200 overlap" (accent) · "Enriched: title+desc+[MM:SS]" [S02 L92-95, table L573-580] | `.t-title .divider .tag-row .tag .tag.accent-tag` |
| 07 | S02 · Decision | Dependency Inversion: two providers | tags: "Gemini 3072d · #1 MTEB" (accent) · "BGE-M3 1024d · no API key". "One contract. Two implementations. Zero coupling." [S02 L94, table L592-600] | `.big-icon .t-title .divider .tag-row .tag .t-body` |
| 08 | S03 · Vector Store | ChromaDB: zero-config vector store | tags: "No API keys" (accent) · "Semantic search" · "Metadata filters". "Local, persistent, LangChain-native." [S03 L919-937] | `.t-title .divider .tag-row .tag .t-body` |
| 09 | S04–S05 · Verify | RAG test + sample extraction | 2 `.day-item`: "S04 rag_test.py — semantic search, no agent"; "S05 extract_sample.py — first-5K dual-backend roundtrip" [S04 L949-977, S05 L987-998] | `.t-title .divider .day-list .day-item .day-num` |
| 10 | S06 · Agent | Cero — tool-calling agent with memory | `.process-flow` U → A → T → DB [as-is]. tags: "Gemini 2.5 Flash" (accent) · "3 tools" · "RunnableWithMessageHistory" · "Spanish prompt" [S06 L1008-1027] | `.t-title .divider .process-flow .tag-row .tag` |
| 11 | S06 · Tools | 3 tools + disambiguation | tags: "list_videos" · "get_video_info" · "search_transcripts" (accent). "Asks 'which video?' before scoped search." [S06 tools table L1031-1052] | `.t-title .divider .tag-row .tag .t-body` |
| 12 | S06 · Decision | Native tool calling over ReAct | big-number "30%" accent + "failure rate eliminated on Spanish queries." [S06 L1015, L126] | `.two-col .big-number .t-title .t-body` |
| 13 | S07 · Observability | LangSmith — auto-tracing, zero code | `.process-flow` LLM → Tool → LLM [as-is]. stats: "5K traces/mo" (accent) · "0 code changes" · "test-safety guard" [S07 L1104-1118] | `.t-title .divider .process-flow .stat-row .stat` |
| 14 | S07 · API + Widget | FastAPI REST + embeddable chat widget | stats: "POST /api/ask" · "DELETE /api/session/{id}". tags: "Vanilla TypeScript" (accent) · "Zero runtime deps" · "Vite proxy" · "Blue bubble" [S07 L1136-1157] | `.t-title .divider .stat-row .stat .tag-row .tag` |
| 15 | S08 · Status | S08: presentation done, deploy pending | 4 `.day-item`: "Done — presentation (this deck)"; "Pending — deploy (Railway / Fly.io / Cloudflare)"; "Pending — frontend polish"; "Pending — voice input (Web Speech API)" [S08 L1170-1182, Dashboard L15] | `.two-col .big-number .day-list .day-item .day-num` |
| 16 | Quality | 149 passing. 7 layers. | 6 `.stat` per Decision 2. Body: "39 = 28 agent + 11 speaker · 3 pre-existing BGE-M3 failures (UV env)." [Tests table L1206-1214, L1204] | `.t-title .divider .stat-row .stat .t-body` |
| 17 | S01 · Toolchain | Three ingestion paths | 3 `.day-item`: "A Colab GPU + yt-dlp + faster-whisper large-v3"; "B local CPU + ffmpeg + faster-whisper + uv"; "C youtube-transcript-api (captions)" [S01 L459-547, structure L384-386] | `.t-title .divider .day-list .day-item .day-num` |
| 18 | Tech Stack | Tech stack | tags [as-is]: FastAPI (accent) · ChromaDB · Gemini Embeddings · LangChain · LangSmith · faster-whisper · Vite+TypeScript · pytest. "Agent: Cero — Spanish RAG with memory." [intro + all S] | `.tag-row .tag .tag.accent-tag .divider .t-body` |
| 19 | Demo | Run it locally | 3 `.day-item`: "Terminal 1 — uvicorn :8000"; "Terminal 2 — pnpm dev"; "Browser — localhost:5173". "Traces at smith.langchain.com" [Quick Start Step 7 L344-354] | `.t-title .divider .day-list .day-item .day-num .t-body` |
| 20 | — | Thank you. | "Questions?" [as-is] | `.slide-closing .t-hero .divider .t-sub` |

## Data flow (README section → slide)

```
README                          Deck slide(s)
intro (L1-4)            ──────► 01 hero, 02 what-is, 18 stack
Pipeline diagram (L21) ──────► 03 S01–S08 flow
S01 (L457-551)         ──────► 04 contract, 05 comparison, 17 toolchain
S02 (L557-661)         ──────► 06 chunking, 07 providers
S03 (L915-941)         ──────► 08 ChromaDB
S04–S05 (L947-1000)    ──────► 09 verify scripts
S06 (L1006-1090)       ──────► 10 agent, 11 tools, 12 native-vs-ReAct
S07 (L1096-1159)       ──────► 13 LangSmith, 14 API+widget
S08 (L1164-1183)       ──────► 15 status
Tests table (L1206)    ──────► 16 tests
Quick Start S7 (L344)  ──────► 19 demo
```

## File Changes

| File | Action | Description |
|---|---|---|
| `presentation/migrant-archive-slides.html` | Modify | Rewrite body of 20 `<section class="slide">` blocks per the table above; `<style>` and `<script>` untouched |

## Removed fabrications (must not survive)

| Removed | Replaced with | Source |
|---|---|---|
| "+22% more text extracted" (old 11) | 5/5 vs 2/5 quality comparison | S01 table L471 |
| "70× speedup" / "4× real-time" (old 10) | "~15s Colab / ~2min local" | S01 table L472 |
| "OpenAI (optional)" (old 12) | "two implementations" (Gemini + BGE-M3) | S02 L96, table L592 |
| "Two strategies" (old 08) | "Three strategies" | S01 L78, L469 |
| Strategy A=captions / B=whisper swap (old 09-10) | A=Colab GPU, B=Whisper, C=Captions | S01 table L469 |
| "125 tests. 121 pass." / "16 agent" (old 16) | "149 passing" / "39 agent+speaker" | Tests L1204, L1210-1211 |
| "Week N / Step N" (old 03-07) | "S01–S08" labels | Dashboard L12-15 |
| Generic 5-step methodology (old 03) | S01–S08 pipeline flow | Pipeline diagram L21 |

## power-design compliance

- **#1 one idea**: each slide carries a single claim; old slide 11's three-claim violation is removed (now one strategy-comparison idea).
- **#3 ≤7 chunks**: Tests slide held at 6 `.stat` via Decision 2; Slide 03 is one flow object; tag rows ≤4 tags.
- **#6/#7 type scale**: only existing `--fs-*` sizes used; no new sizes — deck stays at its 6-size limit.
- **#12 color**: no new colors; `--accent` is the only accent, `--bg`/`--surface` dominant.
- **#13 one accent/slide**: exactly one accent moment per slide (one `.accent-tag`, one accent `.stat-val`, or one accent `.big-number` — never combined).
- **#15 8pt grid**: no spacing values added; reuses class margins (16/24/32/40/48/64). Decision 1 geometry stays on existing tokens.
- **#19 F-pattern**: `.slide-label` (accent, uppercase, top) + `.t-title` preserved on every content slide.
- **#20 presenter mode**: every body ≤15 words; deck stays in presenter mode (no mode mixing).
- **#21 logo**: none present; user implicitly opted out — not added.

## Testing Strategy

| Layer | What to verify | Approach |
|---|---|---|
| Content | No claim absent from README | Diff each slide's facts against cited README lines; the "Removed fabrications" table must all be gone |
| Visual invariants | `:root` + `<script>` byte-identical | `git diff` confined to `<section>` markup only |
| Layout | Slide 03 single row; Tests `.stat-row` no wrap | Open in browser at 1920 and ≤1024; verify 8 nodes / 6 stats render without overflow |
| Navigation | Deck still advances 1→20 | Counter reads "x / 20"; arrows/click/touch work unchanged |

## Migration / Rollout

No migration. Single static-file edit. Rollback: `git checkout -- presentation/migrant-archive-slides.html`. No data/build/dependency side effects.

## Open Questions

- [ ] None blocking. Note for the user: README has an internal inconsistency — the S01 Project-Structure file comments (L384-386) label `ingestion_caption.py` as "Strategy A" while the S01 comparison table (L469) labels Colab GPU as "A". The deck follows the comparison table (canonical, presentation-facing). Fixing the README comment is out of scope here.
