# Session 2 — Chunking Strategy & Testing Strategy

**Date**: 12 June 2026
**Goal**: Definir estrategia de chunking para contenido en español conversacional y diseñar la pirámide de testing.

---

## 1. Chunking Strategy

### Decisión final: 1000 tokens / 200 overlap / estimador simple

| Parámetro | Valor | Justificación |
|-----------|-------|---------------|
| Chunk size | **1000 tokens** (~750 palabras) | Captura ~4-5 min de habla española — una respuesta o idea completa |
| Overlap | **200 tokens (20%)** | Suficiente para que ninguna idea quede partida entre chunks; estándar RAG |
| Token counter | **Estimador simple** (4 chars ≈ 1 token) | Cero dependencias, precisión suficiente para chunking |

### ¿Por qué no 512/50?

| | 512 tk / 50 ov | 1000 tk / 200 ov |
|---|---|---|
| Palabras por chunk | ~380 | ~750 |
| Minutos de habla | ~1.5 min | ~4-5 min |
| Overlap | 10% (bajo) | 20% (estándar RAG) |
| Chunks en video de 1h | ~25 | ~12 |
| Riesgo principal | Corta ideas a la mitad ❌ | Prácticamente nulo ✅ |

El español tiene oraciones más largas que el inglés. Un chunk de 380 palabras corta apenas arrancó una idea. Con 750 palabras capturás un pensamiento completo: una respuesta entera, una anécdota, un argumento.

### ¿Escala para videos de 1 hora?

**Sí, y mejor que chunks más chicos.**

- Un video de 1h (~9,000 palabras) genera solo **12 chunks** de 1000 tokens.
- Con 512 tokens generaría **25 micro-chunks** — más ruido en la búsqueda, más costo de API.
- ChromaDB maneja millones de vectores. 12 o 25 por video es irrelevante para la DB.
- Lo que importa es la **densidad semántica**: cada chunk debe contener una idea completa. 1000 tokens lo logra.

```
Video de 1h |████████████████████████████████████████████████████████████|
            
512/50:     |██| ██| ██| ██| ██| ██| ██| ██| ██| ██| ██| ██|  ← 25 micro-chunks
            ideas partidas ❌      fragmentación ❌

1000/200:   |█████| █████| █████| █████| █████| █████| █████|  ← 12 chunks densos
              ~~      ~~     ~~     ~~     ~~     ~~
            overlap preserva contexto ✅  cada chunk = 1 idea ✅
```

---

## 2. tiktoken vs Estimador Simple

### ¿Qué es tiktoken?

`tiktoken` es la librería oficial de OpenAI para contar tokens. Usa el tokenizador BPE (Byte-Pair Encoding) exacto que usan los modelos de OpenAI. Te dice **exactamente** cuántos tokens tiene un texto.

### ¿Qué es el estimador simple?

La regla `caracteres / 4 ≈ tokens`. Se basa en que, en promedio, un token en modelos modernos equivale a ~4 caracteres en inglés y ~3.5 en español.

### Comparación real

```python
texto = "La migración es un derecho humano fundamental y debe ser protegido"

# Estimador simple
chars = len(texto)  # 64
tokens_est = chars / 4  # 16 tokens

# tiktoken (si lo usáramos)
tokens_real = 18  # varía según el tokenizador
```

| Aspecto | Estimador simple | tiktoken |
|---------|-----------------|----------|
| Precisión | ±15% | Exacta |
| Dependencia | Ninguna | `tiktoken` (pip install) |
| Velocidad | Instantáneo (división) | ~1-5ms por texto |
| ¿Afecta al chunking? | No — ±2 tokens es irrelevante | No aporta valor |

### ¿Cuándo usar cada uno?

| Caso de uso | Recomendación |
|-------------|---------------|
| **Chunking** (cortar texto en pedazos) | ✅ Estimador simple |
| **Cost tracking** (calcular costo exacto de API) | tiktoken |
| **Context window management** (no exceder límite del modelo) | tiktoken |
| **Aproximación rápida** | ✅ Estimador simple |

### Conclusión

Para chunking, **el estimador simple alcanza y sobra**. La diferencia entre 980 y 1020 tokens reales no afecta la calidad del chunk. tiktoken solo se justifica si necesitás contar costos de API al centavo o asegurar que no excedés el context window del LLM. Para este proyecto: cero dependencias, mismo resultado práctico.

---

## 3. Testing Strategy — Las Tres Capas

### La pirámide

```
         ┌──────┐
         │ E2E  │  ← ¿Funciona en el mundo real?
         │ ~30s │     Gemini API + ChromaDB + 1 video
         ├──────┤
         │ Int. │  ← ¿Mis piezas encajan?
         │ ~10s │     BGE-M3 real + ChromaDB real
         ├──────┤
         │ Unit │  ← ¿Mi lógica funciona?
         │ <1s  │     FakeEmbeddingProvider (mock)
         └──────┘
```

### Capa 1 — Unit Tests

**Qué prueba**: Lógica aislada. Chunking, orquestación, contratos.

**Cómo**: `FakeEmbeddingProvider` — una implementación falsa que devuelve vectores dummy.

```python
class FakeEmbeddingProvider(EmbeddingProvider):
    def embed(self, texts):
        return [[0.1] * 768 for _ in texts]  # vectores falsos
    
    def embed_query(self, text):
        return [0.1] * 768
    
    @property
    def dimension(self):
        return 768

def test_chunk_overlap():
    provider = FakeEmbeddingProvider()
    processor = Processor(provider, chunk_size=1000, overlap=200)
    
    # VideoData de prueba con texto conocido
    vd = create_test_videodata("Texto de prueba " * 500)
    chunks = processor.chunk(vd)
    
    assert len(chunks) > 1
    # Verificar que el overlap existe: última palabra del chunk N
    # aparece en el chunk N+1
    last_words_chunk0 = chunks[0].text.split()[-10:]
    first_words_chunk1 = chunks[1].text.split()[:10]
    assert any(w in first_words_chunk1 for w in last_words_chunk0)
```

**Qué caza**: Errores de lógica — chunking mal implementado, índices fuera de rango, metadata incorrecta.

**Cuándo corre**: Cada vez que tocás `processor.py` o `embedding.py`.

**Sin**: API keys, internet, ChromaDB.

---

### Capa 2 — Integration Tests

**Qué prueba**: Que las piezas REALES encajan — BGE-M3 genera vectores válidos, ChromaDB los persiste y los encuentra.

**Cómo**: BGE-M3 local (gratis, CPU) + ChromaDB temporal.

```python
def test_vector_store_add_and_search():
    provider = BGE_M3_Provider()  # REAL, carga el modelo
    store = VectorStore(persist_dir=":memory:")  # ChromaDB en memoria
    
    # Insertar
    store.add(
        ids=["test_1"],
        documents=["La migración es un derecho humano"],
        metadatas=[{"video_id": "v001", "chunk_index": 0}],
        embeddings=provider.embed(["La migración es un derecho humano"])
    )
    
    # Buscar
    query_embedding = provider.embed_query("derecho humano")
    results = store.search(query_embedding, top_k=3)
    
    assert len(results) > 0
    assert results[0]["metadata"]["video_id"] == "v001"
```

**Qué caza**: Interfaces rotas — provider no respeta el contrato, ChromaDB schema mismatch, embeddings con dimensión incorrecta.

**Cuándo corre**: Antes de commitear.

**Sin**: API keys, internet. Corre 100% local (~10 segundos, la mayor parte es cargar BGE-M3 la primera vez).

---

### Capa 3 — E2E Tests

**Qué prueba**: El pipeline completo en condiciones reales — Gemini API, ChromaDB real, un video posta.

**Cómo**: Gemini API + ChromaDB en disco.

```python
def test_full_pipeline_one_video():
    provider = GeminiProvider()  # usa GEMINI_API_KEY
    store = VectorStore(persist_dir="data/chroma_test")
    processor = Processor(provider, chunk_size=1000, overlap=200)
    
    # Cargar un VideoData real (ya existe en data/raw/whisper/)
    video_data = VideoData.load_json("data/raw/whisper/APgxfNssxGQ.json")
    
    # Procesar
    chunks = processor.chunk(video_data)
    embeddings = processor.embed_chunks(chunks)
    store.add_from_chunks(chunks, embeddings)
    
    # Verificar búsqueda
    query_embedding = provider.embed_query("¿Cuál es el mensaje principal?")
    results = store.search(query_embedding, top_k=5)
    
    assert len(results) > 0
    assert all(r["metadata"]["video_id"] == video_data.video_id for r in results)
```

**Qué caza**: Problemas del mundo real — API timeout, encoding raro en transcripción, texto vacío, videos sin transcript.

**Cuándo corre**: Antes de deployar o cuando cambiás de proveedor de embeddings.

**Requiere**: `GEMINI_API_KEY` e internet.

---

### ¿Por qué tres capas y no solo tests unitarios?

Porque cada capa caza bugs que la anterior no puede ver:

| Bug | Unit lo ve? | Integration lo ve? | E2E lo ve? |
|-----|-------------|-------------------|------------|
| `chunk()` no calcula bien el overlap | ✅ | ✅ | ✅ |
| `EmbeddingProvider.embed()` devuelve dimensión incorrecta | ❌ (usa mock) | ✅ | ✅ |
| ChromaDB schema no matchea metadata | ❌ | ✅ | ✅ |
| Gemini API devuelve error 429 (rate limit) | ❌ | ❌ | ✅ |
| VideoData con `full_text` vacío rompe el pipeline | ✅ | ✅ | ✅ |
| Texto con caracteres especiales (¿¡ñ) | ❌ (mock ignora) | ✅ (BGE-M3 real) | ✅ |

**En una entrevista**, saber explicar estas tres capas y CUÁNDO usar cada una demuestra que entendés testing como herramienta de diseño, no como checklist.

---

## Resumen de decisiones

| Decisión | Valor | Archivo donde se implementa |
|----------|-------|---------------------------|
| Chunk size | 1000 tokens | `core/processor.py` |
| Overlap | 200 tokens (20%) | `core/processor.py` |
| Token counter | Estimador simple | `core/processor.py` |
| Unit tests | FakeEmbeddingProvider mock | `tests/test_processor.py`, `tests/test_embedding.py` |
| Integration tests | BGE-M3 + ChromaDB temporal | `tests/test_vector_store.py` |
| E2E tests | Gemini + ChromaDB + video real | `tests/test_pipeline_e2e.py` |
