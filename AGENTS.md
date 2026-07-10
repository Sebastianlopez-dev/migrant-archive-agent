# Project: Migrant Archive

## Stack
- Python 3.12+, uv (package manager)
- LangChain (langchain-classic, langchain-core, langchain-google-genai, langchain-chroma, langchain-community==0.3.31)
- ChromaDB (vector store)
- Google Gemini (embeddings + LLM via google-genai; also used as RAGAS judge LLM)
- Groq (Whisper API for voice transcription)
- RAGAS 0.4.3 (evaluation metrics: faithfulness, answer relevancy, context precision, context recall)
- pytest (testing, strict TDD)
- TypeScript/Vite (frontend, complete)
- JSON (VideoData format, data storage)

## Language Convention
- User conversation: Spanish (Rioplatense)
- Code, comments, identifiers, UI copy: English
- Technical artifacts (specs, designs, tasks): English
- README documentation: English

## Package Tracking Rule
When new packages are added to requirements.txt, update the Stack section above.

## Gitignore Convention
- The `.gitignore` uses `.*` as a catch-all to hide dev tool dotfiles (Claude, OpenCode, ATL, etc.) without listing them individually.
- If a dotfile or dotdir starting with `.` is NEEDED for the project to work, add a `!` exception in `.gitignore` so it is tracked (e.g., `!.env.example`).

## Documentation
- No emojis in any artifact — code, comments, docs, README, commits, PR descriptions, UI copy
- All project artifacts in English: code, comments, identifiers, UI copy, README, specs, designs, tasks
- README voice: Researcher, Positive, Affirmative — written for external readers, not self-reference ("I did this") or agent-to-user framing
- Document editing: when adding content to an existing file, find the appropriate section and insert there — do not prepend or append blindly

## SDD Workflow
- Spec-Driven Development with phases: explore → proposal → specs → design → tasks → apply → verify → archive
- Artifact store: both (Engram + OpenSpec files under openspec/changes/)
- Execution: automatic mode, 400-line review budget

## Testing
- Strict TDD: RED (failing test) → GREEN (implementation) → REFACTOR
- Test runner: `uv run python -m pytest tests/ -v`
- Test layers: unit (FakeEmbeddingProvider + FakeChatModel), integration (in-memory ChromaDB), E2E (real Gemini API)
- Skip E2E when GEMINI_API_KEY is not set

## Environment
- `.env` file with GEMINI_API_KEY (required) and GROQ_API_KEY (required for voice transcription)
- UV (lightweight, Gemini cloud) — the only supported path. Conda removed after BGE-M3 deprecation.
- Package install: `uv pip install -r requirements.txt`

## Architecture
- Pipeline: S01 Ingestion → S02 Chunking+Embedding → S03 ChromaDB → S04-S05 Scripts → S06 Agent → S07 API → S08 Frontend → S09 Demo → S10 Evaluation
- Strategy Pattern for ingestion (captions / faster-whisper local / Colab GPU)
- Dependency Inversion for embeddings (EmbeddingProvider abstract base, Gemini implementation)
- Single Responsibility: each file does one thing
- RAGAS evaluation reads all 3 agent tools as context (search_transcripts + get_video_info + list_videos) — not just search_transcripts. The tool-calling agent chooses the right tool per question; metadata from catalog tools is valid context for faithfulness scoring.

## Commits
- Conventional commits (feat:, fix:, deps:, docs:)
- Work-unit commits: each commit is a reviewable, testable unit
- No Co-Authored-By or AI attribution

## Current State (July 2026)
- S01-S05: Complete (ingestion, chunking, embeddings, ChromaDB, RAG test)
- S06: Complete (LangChain agent with native tool calling + 3 tools + session memory)
- S07: Complete (FastAPI REST API + LangSmith tracing + Groq voice transcription)
- S08: Complete (Vite/TypeScript chat widget + i18n + voice input + presentation slides)
- S09: Complete (Plataforma Cero demo snapshot + embeddable widget)
- S10: Complete (RAGAS evaluation with Gemini judge LLM, 5-question Q&A dataset, serial single-turn scoring)
