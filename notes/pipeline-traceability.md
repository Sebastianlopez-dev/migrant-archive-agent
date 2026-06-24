# Pipeline Traceability

Every task, decision, file, and test mapped by week and stage.

| Week | Stage | Task | Type | Files | Status |
|------|-------|------|------|-------|--------|
| 1 | S01 | 3-strategy approach (captions / faster-whisper / Colab GPU) | Decision | — | Done |
| 1 | S01 | Strategy Pattern for ingestion | Decision | — | Done |
| 1 | S01 | VideoData JSON as shared contract across strategies | Decision | — | Done |
| 1 | S01 | VideoData dataclass + timestamp helpers | Code | `backend/core/ingestion.py` | Done |
| 1 | S01 | Strategy A: YouTube auto-captions | Code | `backend/core/ingestion_caption.py` | Done |
| 1 | S01 | Strategy B: faster-whisper local CPU | Code | `backend/core/ingestion_audio.py` | Done |
| 1 | S01 | Strategy B GPU: Colab wrapper | Code | `backend/core/ingestion_colab.py` | Done |
| 1 | S01 | Ingestion unit tests | Test | `tests/test_ingestion.py` | Done |
| 1 | S01 | faster-whisper audio strategy tests | Test | `tests/test_faster_whisper_audio.py` | Done |
| 1 | S01 | Colab notebook validation tests | Test | `tests/test_faster_whisper_colab.py` | Done |
| 1 | S02 | Chunk size 1000 / overlap 200 (Spanish conversational) | Decision | — | Done |
| 1 | S02 | Enriched text: title + description + [MM:SS] timestamps | Decision | — | Done |
| 1 | S02 | Dependency Inversion: EmbeddingProvider ABC | Decision | — | Done |
| 1 | S02 | EmbeddingProvider abstract contract | Code | `backend/core/embedding.py` | Done |
| 1 | S02 | Gemini embedding provider (text-embedding-004, 3072d) | Code | `backend/core/embedding_gemini.py` | Done |
| 1 | S02 | BGE-M3 local embedding provider (1024d) | Code | `backend/core/embedding_bge_m3.py` | Done |
| 1 | S02 | Text chunking + embedding orchestration | Code | `backend/core/processor.py` | Done |
| 1 | S02 | Embedding contract tests (FakeEmbeddingProvider) | Test | `tests/test_embedding.py` | Done |
| 1 | S02 | Gemini provider tests | Test | `tests/test_embedding_gemini.py` | Done |
| 1 | S02 | BGE-M3 provider tests | Test | `tests/test_embedding_bge_m3.py` | Done |
| 1 | S02 | Chunking + orchestration tests | Test | `tests/test_processor.py` | Done |
| 1 | S03 | ChromaDB persistent vector store | Code | `backend/core/vector_store.py` | Done |
| 1 | S03 | Vector store CRUD + relevance tests | Test | `tests/test_vector_store.py` | Done |
| 1 | S03 | Full pipeline E2E (real video, Gemini API) | Test | `tests/test_pipeline_e2e.py` | Done |
| 2 | S04 | Fast keyword search script (no API, no embeddings) | Code | `backend/scripts/quick_search.py` | Done |
| 2 | S04 | Interactive RAG test script (ChromaDB + embeddings) | Code | `backend/scripts/rag_test.py` | Done |
| 2 | S05 | First-5K sample extraction (ChromaDB + JSON roundtrip) | Code | `backend/scripts/extract_sample.py` | Done |
| 2 | S05 | Sample extraction + truncation tests | Test | `tests/test_extract_sample.py` | Done |
| 2 | S06 | Native tool calling over ReAct text parsing | Decision | — | Done |
| 2 | S06 | RunnableWithMessageHistory over ConversationBufferMemory | Decision | — | Done |
| 2 | S06 | faster-whisper over WhisperX (Colab compatibility) | Decision | `notes/faster-whisper-migration.md` | Done |
| 2 | S06 | Tool-calling agent: 3 tools (list, info, search) | Code | `backend/agents/agent.py` | Done |
| 2 | S06 | Tools: list_videos, get_video_info, search_transcripts | Code | `backend/agents/tools.py` | Done |
| 2 | S06 | Speaker extraction (5 description patterns, unicode norm) | Code | `backend/agents/tools.py` | Done |
| 2 | S06 | Interactive agent CLI with session memory | Code | `backend/scripts/agent_cli.py` | Done |
| 2 | S06 | Agent, tool, memory, disambiguation, scoped search, CLI tests | Test | `tests/test_agent.py` | Done |
| 2 | S06 | Speaker extraction: patterns, unicode, channel fallback | Test | `tests/test_speaker_extraction.py` | Done |
| 3 | S07 | FastAPI app factory + CORS | Code | `backend/api/main.py` | Done |
| 3 | S07 | Pydantic schemas (AskRequest with session_id) | Code | `backend/api/models.py` | Done |
| 3 | S07 | Agent dependency injection (RunnableWithMessageHistory) | Code | `backend/api/dependencies.py` | Done |
| 3 | S07 | POST /api/ask + DELETE /api/session/{id} | Code | `backend/api/routes/chat.py` | Done |
| 3 | S07 | LangSmith zero-code tracing (env-var auto-detection) | Decision | — | Done |
| 3 | S07 | LangSmith tracing guard fixture (disabled during pytest) | Code | `tests/conftest.py` | Done |
| 3 | S07 | API models, routes, CORS, errors, session lifecycle | Test | `tests/test_api.py` | Done |
| 3 | S07 | LangSmith tracing + fixture guard tests | Test | `tests/test_langsmith.py` | Done |
| 3 | S07 | Chat widget: blue bubble, slide-out panel, fetch API | Code | `frontend/src/chat-widget.ts` | Done |
| 3 | S07 | Widget bootstrap + Vite config | Code | `frontend/src/main.ts` | Done |
| 3 | S07 | Widget styles | Code | `frontend/src/styles.css` | Done |
| 3 | S07 | Frontend build + widget structure tests | Test | `tests/test_frontend.py` | Done |
| 4 | S08 | 20-slide HTML presentation deck | Code | `presentation/migrant-archive-slides.html` | Done |
| 4 | S08 | Deploy platform research (Railway / Fly.io / Cloudflare) | Decision | — | Done |
| 4 | S08 | Frontend polish: accessibility, loading states, error toasts | Code | `frontend/src/` | Pending |
| 4 | S08 | Deploy to production (live web app) | Ops | — | Pending |
| 4 | S08 | Voice input via Web Speech API | Code | `frontend/src/` | Pending |
