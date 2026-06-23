# Project: Migrant Archive

## Stack
- Python 3.12+, uv (package manager)
- LangChain (langchain-classic, langchain-core, langchain-google-genai)
- ChromaDB (vector store)
- Google Gemini (embeddings + LLM via google-genai)
- faster-whisper (audio transcription)
- pytest (testing, strict TDD)
- HTML/CSS/JS (frontend, planned Week 4)
- JSON (VideoData format, data storage)

## Language Convention
- User conversation: Spanish (Rioplatense)
- Code, comments, identifiers, UI copy: English
- Technical artifacts (specs, designs, tasks): English
- README documentation: English

## Package Tracking Rule
When new packages are added to requirements.txt, update the Stack section above.

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
- `.env` file with GEMINI_API_KEY (required)
- Two paths: UV (lightweight, Gemini cloud) or Conda (ML-ready, BGE-M3 local)
- Package install: `uv pip install -r requirements.txt`

## Architecture
- Pipeline: S01 Ingestion → S02 Chunking+Embedding → S03 ChromaDB → S04-S05 Scripts → S06 Agent → S07 API → S08 Frontend
- Strategy Pattern for ingestion (captions / faster-whisper local / Colab GPU)
- Dependency Inversion for embeddings (EmbeddingProvider abstract base, Gemini and BGE-M3 implementations)
- Single Responsibility: each file does one thing

## Commits
- Conventional commits (feat:, fix:, deps:, docs:)
- Work-unit commits: each commit is a reviewable, testable unit
- No Co-Authored-By or AI attribution

## Current State (June 2026)
- S01-S05: Complete (ingestion, chunking, embeddings, ChromaDB, RAG test)
- S06: Complete (LangChain agent with ConversationBufferMemory + search_transcripts tool)
- S07-S08: Pending (FastAPI, frontend)
