# Presentation Content Specification

## Purpose

Define the acceptance criteria for the refreshed `presentation/migrant-archive-slides.html` deck.
Every requirement is a testable assertion about deck content traceable to README.md (S01–S08).
Visual design (CSS `:root` tokens, layout classes, `<script>`) is preserved unchanged.

---

## Requirements

### Requirement: REQ-CONTENT-001 Fabricated metrics are absent

The deck SHALL NOT contain any of the following strings: `+22%`, `70× speedup`, `4× real-time`.
These numbers have no source in README.

#### Scenario: Verify no fabricated percentage

- GIVEN the refreshed HTML file
- WHEN its full text content is searched for `+22%`
- THEN zero matches are found

#### Scenario: Verify no fabricated speedup

- GIVEN the refreshed HTML file
- WHEN its full text content is searched for `70×`
- THEN zero matches are found

#### Scenario: Verify no fabricated real-time ratio

- GIVEN the refreshed HTML file
- WHEN its full text content is searched for `4× real-time`
- THEN zero matches are found

---

### Requirement: REQ-CONTENT-002 OpenAI reference is absent

The deck SHALL NOT contain `OpenAI`. README S02 documents exactly two embedding providers (Gemini and BGE-M3); OpenAI is not one of them.

#### Scenario: Verify no OpenAI mention

- GIVEN the refreshed HTML file
- WHEN its full text is searched for `OpenAI`
- THEN zero matches are found

---

### Requirement: REQ-CONTENT-003 Three ingestion strategies, correct labels

The ingestion section SHALL describe THREE strategies with labels matching README S01 strategy comparison table exactly: Strategy A = Colab GPU (recommended), Strategy B = faster-whisper local CPU, Strategy C = captions (fallback). The framing word "Two" applied to strategies SHALL NOT appear.

#### Scenario: Strategy count

- GIVEN the slide covering ingestion strategies
- WHEN a reviewer reads it
- THEN the word "Three" (or "3") is present and "Two" is absent in relation to strategy count

#### Scenario: Strategy A label

- GIVEN the strategy listing
- WHEN Strategy A is examined
- THEN it is labeled Colab GPU and marked as recommended. Source: README S01 Strategy comparison.

#### Scenario: Strategy B label

- GIVEN the strategy listing
- WHEN Strategy B is examined
- THEN it is labeled faster-whisper local CPU. Source: README S01.

#### Scenario: Strategy C label

- GIVEN the strategy listing
- WHEN Strategy C is examined
- THEN it is labeled captions (fallback). Source: README S01.

---

### Requirement: REQ-CONTENT-004 Test count is 149 passing across 7 layers

The slide covering the test suite SHALL state 149 passing tests broken down across exactly 7 layers matching README Tests table. The superseded counts (125 total, 121 pass, 16 agent) SHALL NOT appear.

#### Scenario: Total count

- GIVEN the tests slide
- WHEN its visible text is read
- THEN the number 149 appears as the passing count. Source: README Tests section.

#### Scenario: Layer breakdown

- GIVEN the tests slide
- WHEN each stat block is read
- THEN the following values are present: Unit 40 / Integration 55 / Agent 28 / Speaker 11 / Frontend 9 / Observability 3 / E2E 2. Source: README Tests table.

#### Scenario: Stale counts absent

- GIVEN the refreshed HTML file
- WHEN its full text is searched for `125` or `121 pass` or `16 agent`
- THEN zero matches are found

---

### Requirement: REQ-CONTENT-005 S01–S08 naming is used throughout

Every label that previously read "Week N" or "Step N" SHALL be replaced with S01–S08 nomenclature matching README Pipeline Architecture and Progress Dashboard. The strings "Week 1", "Week 2", "Week 3", "Week 4", "Step 1", "Step 2", "Step 3", "Step 4", "Step 5" SHALL NOT appear as slide labels.

#### Scenario: No Week/Step labels

- GIVEN the refreshed HTML file
- WHEN its full text is searched for the pattern `Week [1-4]` and `Step [1-5]` as slide section labels
- THEN zero matches are found in slide heading or label contexts

#### Scenario: S01–S08 labels present

- GIVEN the slides covering the pipeline stages
- WHEN slide labels are read
- THEN S01 through S08 labels appear and map to the README pipeline sections. Source: README Pipeline Architecture.

---

### Requirement: REQ-CONTENT-006 S02 embedding providers are Gemini and BGE-M3 only

The embedding slide SHALL name Gemini (cloud, 3072 dimensions) and BGE-M3 (local, 1024 dimensions) as the two providers. No third provider SHALL appear. The abstract EmbeddingProvider contract and Dependency Inversion framing SHALL be present. Source: README S02 embedding provider comparison.

#### Scenario: Gemini provider detail

- GIVEN the embedding provider slide
- WHEN Gemini is described
- THEN 3072d (or 3072 dimensions) is stated. Source: README S02 provider table.

#### Scenario: BGE-M3 provider detail

- GIVEN the embedding provider slide
- WHEN BGE-M3 is described
- THEN 1024d (or 1024 dimensions) is stated. Source: README S02 provider table.

#### Scenario: No third provider

- GIVEN the embedding provider slide
- WHEN all providers listed are counted
- THEN exactly two providers are shown: Gemini and BGE-M3.

---

### Requirement: REQ-CONTENT-007 S03 ChromaDB presented as zero-config vector store

A slide covering S03 SHALL describe ChromaDB as zero-config / no API key / local persistent vector store. Source: README S03 ChromaDB comparison table.

#### Scenario: ChromaDB slide present

- GIVEN the slides covering S03
- WHEN a reviewer reads the S03 slide
- THEN ChromaDB is identified as the vector store and at least one of "zero-config" or "no API key" is stated. Source: README S03.

---

### Requirement: REQ-CONTENT-008 S04–S05 RAG test and sample extraction present

A slide or section SHALL reference S04 (RAG test script) and S05 (sample extraction) as distinct pipeline steps. Source: README S04–S05.

#### Scenario: S04–S05 content present

- GIVEN the deck
- WHEN slides are reviewed for S04 and S05 content
- THEN the deck contains at least one slide referencing RAG test and sample extraction as S04–S05 work. Source: README S04 and S05.

---

### Requirement: REQ-CONTENT-009 Cero agent slide shows all 3 tools plus per-session memory and disambiguation

The S06 / agent slide(s) SHALL list all three tools (`list_videos`, `get_video_info`, `search_transcripts`) and SHALL state per-session memory and the disambiguation flow. Source: README S06 Tools table and disambiguation flow.

#### Scenario: Three tools listed

- GIVEN the Cero agent slide
- WHEN the tools are enumerated
- THEN `list_videos`, `get_video_info`, and `search_transcripts` are all present. Source: README S06 Tools table.

#### Scenario: Per-session memory stated

- GIVEN the Cero agent slide
- WHEN memory behavior is described
- THEN per-session (or session-based) memory is stated. Source: README S06.

#### Scenario: Disambiguation flow present

- GIVEN the Cero agent slide
- WHEN disambiguation is described
- THEN the concept of agent asking "which video?" before searching is present. Source: README S06 disambiguation flow.

---

### Requirement: REQ-CONTENT-010 S07 LangSmith zero-code tracing and FastAPI widget present

The S07 slide SHALL state LangSmith zero-code tracing (env-var auto-detection, no application code changes), FastAPI endpoints, and the embeddable chat widget. Source: README S07.

#### Scenario: Zero-code tracing stated

- GIVEN the S07 slide
- WHEN LangSmith is described
- THEN "zero code" or "no application code" framing is present. Source: README S07 LangSmith Tracing.

#### Scenario: FastAPI and widget present

- GIVEN the S07 slide
- WHEN the API and widget are described
- THEN FastAPI and embeddable chat widget are both mentioned. Source: README S07 Architecture.

---

### Requirement: REQ-CONTENT-011 S08 status is accurate: presentation done, deploy and polish pending

The S08 slide SHALL state that the presentation is done and that deploy to production, frontend polish, and voice input are pending. Source: README S08 and Progress Dashboard.

#### Scenario: Presentation done

- GIVEN the S08 slide
- WHEN its content is read
- THEN presentation (slides) is listed as completed. Source: README S08 What's done.

#### Scenario: Pending items

- GIVEN the S08 slide
- WHEN pending items are listed
- THEN deploy to production, frontend polish, and voice input (Web Speech API) are all present as pending. Source: README S08 and Progress Dashboard.

---

### Requirement: REQ-CONTENT-012 Design system is byte-identical to pre-change state

The `<style>` block containing CSS `:root` custom properties, all layout utility classes, and the entire `<script>` block SHALL be identical to their pre-change state. No design token, type size, color, spacing value, or navigation logic SHALL be modified.

#### Scenario: CSS root tokens unchanged

- GIVEN a diff of the HTML file before and after the change
- WHEN the `<style>` block is compared
- THEN `--bg`, `--surface`, `--text`, `--muted`, `--accent`, `--accent-dim`, `--fs-hero`, `--fs-title`, `--fs-sub`, `--fs-body`, `--fs-small`, `--fs-cap` are all identical to the pre-change values.

#### Scenario: Layout classes unchanged

- GIVEN a diff of the HTML file
- WHEN layout class definitions are compared
- THEN `.slide`, `.deck`, `.slide-hero`, `.slide-content`, `.slide-closing`, `.process-flow`, `.process-step`, `.two-col`, `.stat-row`, `.tag-row`, `.tag`, `.day-list`, `.day-item`, `.divider`, `.big-number`, `.slide-label`, `.slide-counter`, `.nav-hint` are byte-identical to pre-change state.

#### Scenario: Navigation script unchanged

- GIVEN a diff of the HTML file
- WHEN the `<script>` block is compared
- THEN keyboard navigation (ArrowLeft/Right/Up/Down), click half-screen logic, touch swipe, and the `total` counter variable are all byte-identical to pre-change state.

---

### Requirement: REQ-CONTENT-013 Slide count remains 20

The deck SHALL contain exactly 20 `<section>` elements. Source: Proposal scope — "keep 20 slides + presenter mode."

#### Scenario: Section count

- GIVEN the refreshed HTML file
- WHEN all `<section>` tags are counted
- THEN exactly 20 are found.
