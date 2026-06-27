## Exploration: search_transcripts fails for "Mujeres del Maíz"

### Current State

The migrant-archive system uses ChromaDB to store transcript chunks with embeddings for semantic search. The ingestion pipeline (`backend/scripts/rebuild_index.py`) uses `GeminiEmbeddingProvider` (backend/core/embedding_gemini.py) which calls the Google GenAI API with model `models/gemini-embedding-001` (3072-dim) to generate document embeddings. These embeddings are stored in ChromaDB under the `migrant_archive` collection.

The conversational agent (`backend/agents/agent.py`) creates a LangChain `Chroma` retriever with `GoogleGenerativeAIEmbeddings(model="gemini-embedding-2")` to perform `similarity_search` when the `search_transcripts` tool is invoked. The agent uses a `top_k=3` default.

**The video "Mujeres del Maíz: relatos migrantes escritos por 12 mujeres latinoamericanas" (video_id: `mY1hw79ydY0`) is present in the collection with 4 chunks.** Chunk 0 contains the title and full description. The transcript segments cover topics including writing, migration, sorority, and the book anthology.

### Root Cause: Embedding Model Mismatch

The agent fails to find the video because the **query embeddings are generated with a different model than the document embeddings**.

Evidence gathered by direct vector comparison:

| Model | Used For | Cosine vs doc `mY1hw79ydY0_chunk_0` |
|---|---|---|
| `models/gemini-embedding-001` | Ingestion / `GeminiEmbeddingProvider` | **0.7316** (high relevance) |
| `gemini-embedding-2` | Agent query / `GoogleGenerativeAIEmbeddings` | **-0.0146** (negative / orthogonal) |

The two embedding models produce vectors in completely different semantic spaces (cosine similarity between their query embeddings for the same text is -0.003). When the agent queries ChromaDB with `gemini-embedding-2` embeddings, the similarity scores against documents embedded with `gemini-embedding-001` are essentially random, causing the wrong documents to be returned.

Agent trace for query "¿Qué es mujeres del maíz?":
1. Agent calls `search_transcripts(query="Mujeres del Maíz")`
2. Because of the embedding mismatch, ChromaDB returns chunks from video `CTmWjuQcvHY` (FILMIG 2024 conversatorio) instead of `mY1hw79ydY0`
3. Agent then calls `get_video_info(CTmWjuQcvHY)` and scoped `search_transcripts(video_id=CTmWjuQcvHY)`
4. Agent concludes: "no se encuentra una definición directa de 'Mujeres del Maíz'"

Verification: changing the agent's embedding model to `gemini-embedding-001` (or `models/gemini-embedding-001`) makes `similarity_search("Mujeres del Maíz", k=3)` return all 3 top results from the correct video `mY1hw79ydY0`.

### Affected Areas

- `backend/agents/agent.py` line 153 — `GoogleGenerativeAIEmbeddings(model="gemini-embedding-2")` is the primary source of the mismatch
- `backend/scripts/cero-01.py` line 51 — same incorrect model name in standalone RAG script
- `backend/scripts/agent_cli_monolitic.py` line 88 — same incorrect model name in monolithic CLI
- `tests/test_agent.py` line 967 — test fixture uses the incorrect model, so integration tests may pass for the wrong reasons or fail silently
- `backend/core/embedding_gemini.py` — defines the canonical model `models/gemini-embedding-001` used during ingestion; this is the source of truth

### Approaches

1. **Fix embedding model name in agent and scripts** — Change `"gemini-embedding-2"` to `"gemini-embedding-001"` (or `"models/gemini-embedding-001"`) in all query-side code so it matches the ingestion model.
   - Pros: One-line fix, immediate resolution, no re-indexing required
   - Cons: Requires finding and updating all occurrences; future risk if someone changes one side but not the other
   - Effort: Low

2. **Centralize embedding model configuration** — Extract the embedding model name into a shared constant (e.g., `backend/core/config.py` or `.env`) and reference it from both ingestion and agent code.
   - Pros: Eliminates risk of future mismatches; single source of truth
   - Cons: Slightly more refactoring; requires updating both core and agents to import the constant
   - Effort: Low

3. **Refactor agent to reuse `GeminiEmbeddingProvider`** — Instead of instantiating `GoogleGenerativeAIEmbeddings` directly in `agent.py`, inject the existing `GeminiEmbeddingProvider` into a thin LangChain-compatible wrapper, or use `VectorStore` directly.
   - Pros: Guarantees the same model and embedding logic on both sides; better separation of concerns
   - Cons: More code change; may require a custom LangChain embeddings adapter
   - Effort: Medium

4. **Rebuild index with `gemini-embedding-2`** — Re-index all videos using the same model the agent currently uses.
   - Pros: No code changes in agent
   - Cons: Expensive (220 chunks x API calls), destructive, and `gemini-embedding-2` may be less predictable or more expensive; the root cause (mismatch) remains unaddressed
   - Effort: High

### Recommendation

Implement **Approach 1 + Approach 2** together:

1. Immediately change `"gemini-embedding-2"` to `"gemini-embedding-001"` in `agent.py`, `cero-01.py`, `agent_cli_monolitic.py`, and `test_agent.py` to fix the bug.
2. Introduce a shared constant (e.g., `EMBEDDING_MODEL = "gemini-embedding-001"` in `backend/core/config.py` or `backend/core/embedding_gemini.py`) and have both `GeminiEmbeddingProvider` and the agent's `GoogleGenerativeAIEmbeddings` reference it.

This is the lowest-risk, highest-impact fix. No re-indexing is required because the stored vectors were already generated with `gemini-embedding-001`.

### Risks

- **Silent test failures**: `test_agent.py` currently initializes the store with the mismatched model; tests may be asserting incorrect behavior or passing by coincidence. Any fix must include updating the test fixture.
- **Future regression**: Without a shared constant, a developer could change the ingestion model (e.g., to BGE-M3) while the agent still uses Gemini, re-introducing the mismatch.
- **LangChain model naming**: `GoogleGenerativeAIEmbeddings` accepts both `"gemini-embedding-001"` and `"models/gemini-embedding-001"`. The latter is the fully-qualified API name and is safer to use consistently.
- **No re-indexing needed, but verify**: Because the fix aligns the query model to the existing document vectors, no re-indexing is required. However, after the fix, a quick smoke test with the query "Mujeres del Maíz" should be run to confirm the correct video is returned.

### Ready for Proposal

Yes. The root cause is confirmed, the fix is minimal and well-scoped, and the risk is low. Proceed to proposal phase to document the exact file changes and test plan.
