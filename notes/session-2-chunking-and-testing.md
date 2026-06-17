# Session 2 — Chunking Strategy & Testing Strategy

**Date**: 12 June 2026
**Goal**: Define the chunking strategy for Spanish conversational content and design the testing pyramid.

---

## 1. Chunking Strategy

### Final decision: 1000 tokens / 200 overlap / simple estimator

| Parameter | Value | Rationale |
|-----------|-------|---------------|
| Chunk size | **1000 tokens** (~750 words) | Captures ~4-5 min of Spanish speech — one complete answer or idea |
| Overlap | **200 tokens (20%)** | Enough to ensure no idea is cut between chunks; RAG standard |
| Token counter | **Simple estimator** (4 chars ≈ 1 token) | Zero dependencies, sufficient accuracy for chunking |

### Why not 512/50?

| | 512 tk / 50 ov | 1000 tk / 200 ov |
|---|---|---|
| Words per chunk | ~380 | ~750 |
| Minutes of speech | ~1.5 min | ~4-5 min |
| Overlap | 10% (low) | 20% (RAG standard) |
| Chunks in 1h video | ~25 | ~12 |
| Main risk | Cuts ideas in half ❌ | Practically zero ✅ |

Spanish has longer sentences than English. A 380-word chunk cuts an idea just as it starts. At 750 words, you capture a complete thought: an entire answer, an anecdote, an argument.

### Does it scale for 1-hour videos?

**Yes, and better than smaller chunks.**

- A 1h video (~9,000 words) generates only **12 chunks** of 1000 tokens.
- At 512 tokens, it would generate **25 micro-chunks** — more search noise, higher API cost.
- ChromaDB handles millions of vectors. 12 or 25 per video is irrelevant to the DB.
- What matters is **semantic density**: each chunk must contain one complete idea. 1000 tokens achieves this.

```
1h video  |████████████████████████████████████████████████████████████|
          
512/50:   |██| ██| ██| ██| ██| ██| ██| ██| ██| ██| ██| ██|  ← 25 micro-chunks
          cut ideas ❌           fragmentation ❌

1000/200: |█████| █████| █████| █████| █████| █████| █████|  ← 12 dense chunks
            ~~      ~~     ~~     ~~     ~~     ~~
          overlap preserves context ✅  each chunk = 1 idea ✅
```

---

## 2. tiktoken vs Simple Estimator

### What is tiktoken?

`tiktoken` is OpenAI's official library for counting tokens. It uses the exact BPE (Byte-Pair Encoding) tokenizer that OpenAI models use. It tells you **exactly** how many tokens a text has.

### What is the simple estimator?

The rule `characters / 4 ≈ tokens`. It's based on the fact that, on average, one token in modern models equals ~4 characters in English and ~3.5 in Spanish.

### Real comparison

```python
text = "La migración es un derecho humano fundamental y debe ser protegido"

# Simple estimator
chars = len(text)  # 64
tokens_est = chars / 4  # 16 tokens

# tiktoken (if we used it)
tokens_real = 18  # varies by tokenizer
```

| Aspect | Simple estimator | tiktoken |
|---------|-----------------|----------|
| Accuracy | ±15% | Exact |
| Dependency | None | `tiktoken` (pip install) |
| Speed | Instant (division) | ~1-5ms per text |
| Does it affect chunking? | No — ±2 tokens is irrelevant | Adds no value |

### When to use each?

| Use case | Recommendation |
|-------------|---------------|
| **Chunking** (splitting text into pieces) | ✅ Simple estimator |
| **Cost tracking** (calculate exact API cost) | tiktoken |
| **Context window management** (avoid exceeding model limit) | tiktoken |
| **Quick approximation** | ✅ Simple estimator |

### Conclusion

For chunking, **the simple estimator is more than enough**. The difference between 980 and 1020 real tokens does not affect chunk quality. tiktoken is only justified if you need to count API costs to the penny or ensure you don't exceed the LLM's context window. For this project: zero dependencies, same practical result.

---

## 3. Testing Strategy — The Three Layers

### The pyramid

```
         ┌──────┐
         │ E2E  │  ← Does it work in the real world?
         │ ~30s │     Gemini API + ChromaDB + 1 video
         ├──────┤
         │ Int. │  ← Do my pieces fit together?
         │ ~10s │     Real BGE-M3 + real ChromaDB
         ├──────┤
         │ Unit │  ← Does my logic work?
         │ <1s  │     FakeEmbeddingProvider (mock)
         └──────┘
```

### Layer 1 — Unit Tests

**What it tests**: Isolated logic. Chunking, orchestration, contracts.

**How**: `FakeEmbeddingProvider` — a fake implementation that returns dummy vectors.

```python
class FakeEmbeddingProvider(EmbeddingProvider):
    def embed(self, texts):
        return [[0.1] * 768 for _ in texts]  # fake vectors
    
    def embed_query(self, text):
        return [0.1] * 768
    
    @property
    def dimension(self):
        return 768

def test_chunk_overlap():
    provider = FakeEmbeddingProvider()
    processor = Processor(provider, chunk_size=1000, overlap=200)
    
    # Test VideoData with known text
    vd = create_test_videodata("Test text " * 500)
    chunks = processor.chunk(vd)
    
    assert len(chunks) > 1
    # Verify that overlap exists: last words of chunk N
    # appear in chunk N+1
    last_words_chunk0 = chunks[0].text.split()[-10:]
    first_words_chunk1 = chunks[1].text.split()[:10]
    assert any(w in first_words_chunk1 for w in last_words_chunk0)
```

**What it catches**: Logic errors — poorly implemented chunking, out-of-range indices, incorrect metadata.

**When it runs**: Every time you touch `processor.py` or `embedding.py`.

**Without**: API keys, internet, ChromaDB.

---

### Layer 2 — Integration Tests

**What it tests**: That the REAL pieces fit together — BGE-M3 generates valid vectors, ChromaDB persists and retrieves them.

**How**: Local BGE-M3 (free, CPU) + temporary ChromaDB.

```python
def test_vector_store_add_and_search():
    provider = BGE_M3_Provider()  # REAL, loads the model
    store = VectorStore(persist_dir=":memory:")  # ChromaDB in memory
    
    # Insert
    store.add(
        ids=["test_1"],
        documents=["La migración es un derecho humano"],
        metadatas=[{"video_id": "v001", "chunk_index": 0}],
        embeddings=provider.embed(["La migración es un derecho humano"])
    )
    
    # Search
    query_embedding = provider.embed_query("derecho humano")
    results = store.search(query_embedding, top_k=3)
    
    assert len(results) > 0
    assert results[0]["metadata"]["video_id"] == "v001"
```

**What it catches**: Broken interfaces — provider doesn't respect the contract, ChromaDB schema mismatch, embeddings with incorrect dimension.

**When it runs**: Before committing.

**Without**: API keys, internet. Runs 100% local (~10 seconds, most of it is loading BGE-M3 the first time).

---

### Layer 3 — E2E Tests

**What it tests**: The full pipeline under real conditions — Gemini API, real ChromaDB, a real video.

**How**: Gemini API + ChromaDB on disk.

```python
def test_full_pipeline_one_video():
    provider = GeminiProvider()  # uses GEMINI_API_KEY
    store = VectorStore(persist_dir="data/chroma_test")
    processor = Processor(provider, chunk_size=1000, overlap=200)
    
    # Load a real VideoData (already exists in data/raw/whisper/)
    video_data = VideoData.load_json("data/raw/whisper/APgxfNssxGQ.json")
    
    # Process
    chunks = processor.chunk(video_data)
    embeddings = processor.embed_chunks(chunks)
    store.add_from_chunks(chunks, embeddings)
    
    # Verify search
    query_embedding = provider.embed_query("¿Cuál es el mensaje principal?")
    results = store.search(query_embedding, top_k=5)
    
    assert len(results) > 0
    assert all(r["metadata"]["video_id"] == video_data.video_id for r in results)
```

**What it catches**: Real-world problems — API timeout, weird encoding in transcription, empty text, videos without transcript.

**When it runs**: Before deploying or when switching embedding providers.

**Requires**: `GEMINI_API_KEY` and internet.

---

### Why three layers and not just unit tests?

Because each layer catches bugs the previous one can't see:

| Bug | Unit sees it? | Integration sees it? | E2E sees it? |
|-----|-------------|-------------------|------------|
| `chunk()` doesn't calculate overlap correctly | ✅ | ✅ | ✅ |
| `EmbeddingProvider.embed()` returns wrong dimension | ❌ (uses mock) | ✅ | ✅ |
| ChromaDB schema doesn't match metadata | ❌ | ✅ | ✅ |
| Gemini API returns error 429 (rate limit) | ❌ | ❌ | ✅ |
| VideoData with empty `full_text` breaks pipeline | ✅ | ✅ | ✅ |
| Text with special characters (¿¡ñ) | ❌ (mock ignores) | ✅ (real BGE-M3) | ✅ |

**In an interview**, knowing how to explain these three layers and WHEN to use each one demonstrates that you understand testing as a design tool, not as a checklist.

---

## Summary of decisions

| Decision | Value | File where implemented |
|----------|-------|---------------------------|
| Chunk size | 1000 tokens | `core/processor.py` |
| Overlap | 200 tokens (20%) | `core/processor.py` |
| Token counter | Simple estimator | `core/processor.py` |
| Unit tests | FakeEmbeddingProvider mock | `tests/test_processor.py`, `tests/test_embedding.py` |
| Integration tests | BGE-M3 + temporary ChromaDB | `tests/test_vector_store.py` |
| E2E tests | Gemini + ChromaDB + real video | `tests/test_pipeline_e2e.py` |
