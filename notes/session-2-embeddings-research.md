# Session 2 — Embedding Model Research & Decision

**Date**: 12 June 2026
**Goal**: Select the best embedding model for multilingual (Spanish) RAG and design the embedding layer with Dependency Inversion.

---

## Decision Record

### Models Evaluated

| # | Model | Provider | Cost / 1M tokens | Dims | Multilingual Quality | Runs Local? |
|---|-------|----------|------------------|------|---------------------|-------------|
| 1 | `text-embedding-3-small` | OpenAI | $0.02 | 1536 | ⭐⭐ (39.2% acc en español) | ❌ API only |
| 2 | `text-embedding-3-large` | OpenAI | $0.13 | 3072 | ⭐⭐⭐ (64.6 MTEB) | ❌ API only |
| 3 | `gemini-embedding-001` | Google | $0.15 (free tier available) | 3072 | 🥇 #1 MTEB Multilingual (71.5%) | ❌ API only |
| 4 | `gemini-embedding-2-preview` | Google | $0.20 (batch $0.10) | 768–3072 | 🥇 69.9 MTEB Multilingual | ❌ API only |
| 5 | `BGE-M3` | BAAI (open-source) | FREE | 1024 | ⭐⭐⭐⭐ 100+ languages | ✅ CPU (568M params) |
| 6 | `Qwen3-Embedding-0.6B` | Alibaba (Apache 2.0) | FREE | 1024–2048 | 🥇 #1 open-source multilingual | ✅ CPU (0.6B variant) |
| 7 | `Nomic Embed Text V2` | Nomic (Apache 2.0) | FREE | 768 | ⭐⭐⭐ 100+ languages | ✅ CPU (137M params) |
| 8 | `EmbeddingGemma-300M` | Google (open) | FREE | 768 | ⭐⭐⭐ multilingual | ✅ CPU (300M params) |

### Chosen: Gemini embedding-001 (primary) + BGE-M3 (local alternative)

**Why Gemini embedding-001 as default:**
- #1 on MTEB Multilingual leaderboard (71.5% accuracy).
- Spanish quality is critical — the channel content is 100% Spanish.
- Free tier available on Gemini API — virtually $0 for a 50-video channel (~$0.10 total).
- Matryoshka Representation Learning: 3072-dim vectors can be truncated to 1536/768 without re-embedding.
- 20,000 token context window — handles long transcripts in one call.
- Google ecosystem: user already has Google account with €20 credits.

**Why BGE-M3 as local alternative:**
- Fully open-source, zero cost, no API key.
- 100+ languages with excellent Spanish performance.
- 568M params runs comfortably on Intel i9 + 32GB RAM (CPU).
- Same interface → one-line config change to switch between cloud and local.
- Interview gold: demonstrates understanding of cloud vs local tradeoffs.

**Why NOT OpenAI text-embedding-3-small:**
- 39.2% accuracy on Spanish benchmarks vs 71.5% for Gemini.
- Requires separate OpenAI account + credit card.
- The $0.02/M price advantage is irrelevant at this project's scale (~$0.10 difference total).
- MTEB English bias: looks good on paper, underperforms on non-English content.

**Why NOT gemini-embedding-2:**
- Multimodal (text+image+audio+video) is overkill for text-only RAG.
- 2x the cost of embedding-001 ($0.20 vs $0.15) with similar text performance.
- Still in "preview" — pricing and API may change.

---

## Architecture Decision: Dependency Inversion

### Pattern: Strategy + Dependency Inversion (same as ingestion)

Extending the pattern already proven in `ingestion.py`:

```
core/embedding.py            ← EmbeddingProvider (abstract contract)
core/embedding_gemini.py     ← Gemini API implementation (default)
core/embedding_bge_m3.py     ← BGE-M3 local implementation
core/embedding_openai.py     ← OpenAI implementation (optional)
```

**Contract:**
```python
class EmbeddingProvider(ABC):
    @abstractmethod
    def embed(self, texts: list[str]) -> list[list[float]]:
        """Convert texts to embedding vectors."""
        ...

    @abstractmethod
    def embed_query(self, text: str) -> list[float]:
        """Convert a single query to embedding vector."""
        ...
```

**`processor.py`** receives an `EmbeddingProvider` via dependency injection — it doesn't know or care which implementation is active.

**`vector_store.py`** only persists and retrieves vectors — it has no knowledge of how they were generated.

### Why this matters for interviews

> "Diseñé el pipeline con inversión de dependencias. El processor recibe un `EmbeddingProvider` por interfaz. Si mañana queremos cambiar de Gemini a BGE-M3, tocamos una línea de config y cero lógica de negocio. Es el mismo patrón que usamos en ingestion con las estrategias de transcripción."

---

## Cost Projection

### For the full channel (~50 videos × ~10 min each)

| Model | Cost per video | Cost for 50 videos |
|-------|---------------|-------------------|
| Gemini embedding-001 (free tier) | $0.00 | **$0.00** |
| Gemini embedding-001 (paid) | ~$0.002 | **~$0.10** |
| BGE-M3 (local) | $0.00 | **$0.00** |
| OpenAI text-embedding-3-small | ~$0.001 | **~$0.05** |
| OpenAI text-embedding-3-large | ~$0.007 | **~$0.35** |

All costs are negligible at this project's scale. The differentiator is **quality for Spanish content**, not price.

---

## Benchmarks Deep Dive

### MTEB Multilingual (Massive Text Embedding Benchmark)

| Model | MTEB Multilingual Score |
|-------|------------------------|
| Qwen3-Embedding-8B | 70.58 (#1 open-source) |
| Gemini embedding-2 | 69.9 |
| Gemini embedding-001 | 71.5 (#1 overall) |
| BGE-M3 | 65+ (estimated, multilingual subset) |
| OpenAI text-embedding-3-large | 64.6 |
| OpenAI text-embedding-3-small | 61.0 (English subset) |

### Real-world Spanish RAG test (500K Amazon reviews — independent benchmark)

| Model | Accuracy |
|-------|----------|
| Gemini embedding-001 | 71.5% |
| OpenAI text-embedding-3-large | 64.6% |
| OpenAI text-embedding-3-small | 39.2% |

**Key insight**: `text-embedding-3-small` is optimized for English retrieval. Its multilingual performance drops sharply — it finds semantically *related* documents but often not the *correct* ones. For Spanish content, this is a critical failure mode.

---

## Dependencies to Add

| Package | Purpose | Install |
|---------|---------|---------|
| `google-genai` | Gemini API client | `uv pip install google-genai` |
| `chromadb` | Vector store | `uv pip install chromadb` |
| `FlagEmbedding` | BGE-M3 local inference | `uv pip install FlagEmbedding` |
| `python-dotenv` | Environment variables | Already included |

---

## Discoveries

- **OpenAI text-embedding-3-small is NOT suitable for Spanish RAG.** The 39.2% accuracy on multilingual benchmarks is a dealbreaker for a primarily Spanish content channel. The model was optimized for English MTEB and the quality gap on non-English data is real.
- **Gemini embedding-001 free tier is generous.** Google's free tier covers the entire project's embedding needs at zero cost. No credit card required for the free tier.
- **Matryoshka embeddings save storage.** Both Gemini models support truncation (3072 → 1536 → 768) without re-embedding the corpus. This matters when scaling.
- **Embedding models are small enough for CPU.** BGE-M3 (568M params) runs on CPU without GPU. The 0.6B Qwen3 variant also runs on CPU. GPU is only needed for 8B+ models.
- **Embedding model choice is rarely the bottleneck.** Chunking strategy, reranking, and hybrid search (BM25 + vector) matter more than 1–2 points on MTEB. This informed the decision to invest in architecture design (Dependency Inversion) rather than chasing the absolute highest benchmark score.
- **Old Google embedding models are deprecated.** `text-embedding-004` shut down Jan 2026. `gemini-embedding-exp-03-07` deprecated Aug 2025. Only `gemini-embedding-001` and `gemini-embedding-2` are current.

---

## Toolchain (Updated)

| Tool | Version | Role |
|------|---------|------|
| `google-genai` | latest | Gemini API client (embeddings + future LLM) |
| `chromadb` | latest | Vector store (local, no external server) |
| `FlagEmbedding` | latest | BGE-M3 local inference |
| `yt-dlp` | latest | Metadata + audio download |
| `youtube-transcript-api` | 1.2.4 | YouTube auto-captions (fallback) |
| `faster-whisper` | latest | Local transcription (CTranslate2 backend) |
| `ffmpeg` | 8.1.1 | Audio extraction |

---

## Next Session

- Implement `core/embedding.py` — EmbeddingProvider contract
- Implement `core/embedding_gemini.py` — Gemini API
- Implement `core/embedding_bge_m3.py` — BGE-M3 local
- Implement `core/processor.py` — Chunking + embedding orchestration
- Implement `core/vector_store.py` — ChromaDB persistence
