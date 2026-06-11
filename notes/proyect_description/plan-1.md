# Multimodal AI Chatbot for YouTube Video QA

## Decisiones de arquitectura (30 May 2026)

### 1. Canal fijo
- Se procesa **un canal específico de YouTube** en batch antes del deploy.
- Los videos se transcriben, chunked, embedden y guardan en ChromaDB **una sola vez**.
- En runtime el usuario solo pregunta → respuesta instantánea (sin esperar procesamiento).
- Ventaja: más rápido para el usuario, demo más pulida, base de conocimiento coherente.
- El canal se define en `config.py`.

### 2. Frontend separado del backend
- **Backend**: FastAPI exponiendo endpoints REST (`POST /api/ask`, etc.).
- **Frontend**: HTML/CSS/JS (arranca simple, puede migrar a React después sin tocar backend).
- Decisión motivada por control de UI/UX y posibilidad de desarrollar en paralelo.
- El frontend solo hace `fetch()` al backend, no conoce la lógica de RAG ni ChromaDB.

### 3. Estrategia dual de transcripción (actualizado 12 Jun 2026)
- **Strategy A**: `youtube-transcript-api` → gratis, instantáneo, calidad media (sin puntuación).
- **Strategy B**: `faster-whisper` local CPU → gratis, alta calidad, puntuación correcta, ~2 min para video de 4 min.
- **Strategy B GPU**: `ingestion_colab.py` para videos >5 min (misma lógica, defaults `large-v3 --device cuda`).
- Ambas estrategias producen el mismo contrato `VideoData` → el resto del pipeline no sabe cuál se usó.
- **Decisión**: faster-whisper como default, captions como fallback. Ver `notes/session-1-ingestion.md`.

### 4. Voice input del usuario con Web Speech API
- El usuario puede hacer preguntas **por voz** desde el frontend.
- Se usa la **Web Speech API** del navegador (gratis, sin API externa).
- Funciona en Brave, Chrome, Edge, Opera, Arc (todos los Chromium-based).
- La transcripción ocurre **en el navegador** → el backend recibe texto, igual que si el usuario tipeara.
- **Cero cambios en el backend.** No se necesita Whisper ni endpoint adicional.
- Código de referencia para `frontend/app.js`:
  ```javascript
  const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
  const recognition = new SpeechRecognition();
  recognition.lang = "es-ES";
  recognition.continuous = false;
  recognition.onresult = (event) => {
      const question = event.results[0][0].transcript;
      sendToAPI(question);
  };
  recognition.start();  // al clickear el botón del micrófono
  ```
- Si el navegador no soporta Web Speech API, el input de texto sigue funcionando como fallback.

### 5. Stack tecnológico (actualizado 12 Jun 2026)
| Capa | Herramienta | Nota |
|---|---|---|
| Transcripción | `youtube-transcript-api` + `faster-whisper` | Estrategia dual: Whisper default, captions fallback |
| Embeddings | **Gemini `embedding-001`** (default) | #1 MTEB Multilingual, free tier, $0.15/M tokens |
| Embeddings (local) | **BGE-M3** (alternativa) | Open-source, CPU, 100+ idiomas, $0 |
| Embeddings (opcional) | OpenAI `text-embedding-3-small` | Solo si se necesita compatibilidad OpenAI |
| Vector DB | ChromaDB (local, sin servidor externo) | |
| LLM | OpenAI `gpt-4o-mini` ⚠️ pendiente revisión | ¿Migrar a Gemini 2.5 Flash? (créditos Google) |
| Orquestación | LangChain (agentes, tools, cadenas RAG) | |
| Backend API | FastAPI | |
| Frontend | HTML + CSS + vanilla JS | |
| Voice input | Web Speech API (navegador, gratuito) | |
| Evaluación | LangSmith | |

### 6. Estrategia de embeddings con Inversión de Dependencias (12 Jun 2026)
- **Patrón**: Strategy + Dependency Inversion (mismo enfoque que ingestion).
- **Contrato**: `core/embedding.py` define `EmbeddingProvider` (clase base abstracta).
- **Implementaciones**:
  - `core/embedding_gemini.py` → Gemini API (cloud, mejor calidad multilingual, free tier generoso).
  - `core/embedding_bge_m3.py` → BGE-M3 local (CPU, 568M params, zero-cost, datos sensibles).
  - `core/embedding_openai.py` → OpenAI API (opcional, compatibilidad con ecosistema OpenAI).
- **`processor.py`** recibe un `EmbeddingProvider` por inyección — no sabe ni le importa cuál.
- **`vector_store.py`** solo persiste vectores — no sabe quién los generó.
- **¿Por qué Gemini y no OpenAI?**:
  - Gemini embedding-001 lidera MTEB Multilingual (71.5 vs 39.2 de OpenAI small en español).
  - El contenido del canal es 100% español → la calidad multilingual es crítica.
  - Free tier de Gemini elimina el costo para el volumen del proyecto (~$0.10 para todo el canal).
  - OpenAI requiere tarjeta y créditos; el proyecto ya tiene cuenta Google con saldo.
- **¿Por qué BGE-M3 local también?**:
  - Demuestra comprensión de tradeoffs cloud vs local en entrevistas.
  - Cero dependencia de APIs externas para generación de embeddings.
  - Misma interfaz `EmbeddingProvider` → cambiar de Gemini a BGE-M3 es una línea de config.
- Ver investigación completa: `notes/session-2-embeddings-research.md`.

### 7. Timeline (8 días, actualizado 12 Jun 2026)
| Día | Qué | Estado |
|---|---|---|
| 1 | `core/ingestion.py` + estrategias de transcripción (caption + faster-whisper + colab) | ✅ Completado |
| 2 | `core/processor.py` + `core/embedding.py` + `core/vector_store.py` | 🔲 En progreso |
| 3 | `backend/api/routes.py` + `backend/main.py` — API REST funcionando | 🔲 Pendiente |
| 4 | `frontend/` — UI con input de texto + botón de voz (Web Speech API) | 🔲 Pendiente |
| 5 | `agents/` — LangChain agent con tools y memoria | 🔲 Pendiente |
| 6 | Diseño final del frontend + testeo | 🔲 Pendiente |
| 7 | Evaluación con LangSmith + documentación | 🔲 Pendiente |
| 8 | Presentación y deploy | 🔲 Pendiente |

---

## Estructura del proyecto (actualizada 12 Jun 2026)

```
migrant-archive/
├── README.md
├── requirements.txt
├── .env.example
│
├── backend/
│   ├── config.py              # API keys, modelo, canal, paths
│   ├── main.py                # FastAPI entry point + CORS
│   ├── api/
│   │   ├── __init__.py
│   │   └── routes.py          # POST /api/ask, GET /api/health
│   ├── core/
│   │   ├── __init__.py
│   │   ├── ingestion.py        # VideoData dataclass + shared helpers
│   │   ├── ingestion_caption.py    # Strategy A: YouTube auto-captions
│   │   ├── ingestion_audio.py      # Strategy B: faster-whisper local CPU
│   │   ├── ingestion_colab.py      # Strategy B GPU: Colab wrapper
│   │   ├── embedding.py            # EmbeddingProvider (abstract contract)
│   │   ├── embedding_gemini.py     # Gemini API implementation (default)
│   │   ├── embedding_bge_m3.py     # BGE-M3 local implementation
│   │   ├── embedding_openai.py     # OpenAI implementation (optional)
│   │   ├── processor.py            # Chunking + llama a EmbeddingProvider
│   │   ├── vector_store.py         # ChromaDB (guardar, buscar, borrar)
│   │   ├── rag.py                  # Pipeline: pregunta → retrieve → LLM → respuesta
│   │   └── prompts.py              # Templates de prompts del RAG
│   ├── agents/
│   │   ├── __init__.py
│   │   ├── tools.py            # Herramientas para el agente
│   │   └── agent.py            # Configuración del agente + memoria
│   └── scripts/
│       └── ingest_channel.py   # Batch: procesa todos los videos del canal
│
├── frontend/
│   ├── index.html
│   ├── style.css
│   └── app.js                  # fetch() → POST /api/ask + Web Speech API (voz)
│
└── tests/
    ├── test_rag.py
    └── test_api.py
```

---

## Por qué cada separación

| Archivo | Responsabilidad | Cambia cuando... |
|---|---|---|
| `config.py` | Settings centralizadas | Cambiás API key, modelo, canal |
| `main.py` | Servidor FastAPI + CORS | Configurás middlewares, docs |
| `api/routes.py` | Endpoints REST | Cambiás la interfaz pública |
| `core/ingestion.py` | Contrato VideoData + shared helpers | Cambia el schema de datos |
| `core/ingestion_caption.py` | Strategy A: YouTube captions | YouTube API cambia |
| `core/ingestion_audio.py` | Strategy B: faster-whisper CPU | Cambia el modelo Whisper |
| `core/embedding.py` | Contrato EmbeddingProvider (abstracto) | Cambia la interfaz de embeddings |
| `core/embedding_gemini.py` | Gemini API implementation | Gemini API cambia |
| `core/embedding_bge_m3.py` | BGE-M3 local implementation | Cambia el modelo local |
| `core/processor.py` | Chunking + orquesta embeddings | Ajustás tamaño de chunks |
| `core/vector_store.py` | ChromaDB CRUD | Migrás a Pinecone |
| `core/rag.py` | Pipeline Q&A | Mejorás calidad de respuestas |
| `core/prompts.py` | Templates de prompts | Iterás sobre el prompt engineering |
| `agents/tools.py` | Tools del agente | Agregás o quitás herramientas |
| `agents/agent.py` | Agente + memoria | Cambiás estrategia del agente |
| `scripts/ingest_channel.py` | Batch processing | Cambia el canal o la lógica de ingesta |
| `frontend/` | UI/UX + voice input (Web Speech API) | Mejorás diseño o cambias motor de voz sin tocar backend |

---

## Flujo completo

```
# ── Setup (una vez) ──
python -m backend.scripts.ingest_channel
  → YouTube Transcript API baja 50+ videos del canal
  → processor.py: chunk + embed
  → vector_store.py: guarda en ChromaDB

# ── Runtime ──
Usuario habla (micrófono) o escribe en el frontend
  → Web Speech API transcribe voz → texto  (o usa el input de texto directamente)
  → frontend/app.js → fetch POST /api/ask { question: "..." }
  → backend/api/routes.py → core/rag.py
  → rag.py: embed pregunta → ChromaDB search → armar prompt → LLM
  → API devuelve { answer: "...", sources: [...] }
  → frontend muestra respuesta + fuentes
```

---

## Próximo paso (12 Jun 2026)

Implementar Fase 2 — Processor + Embedding + Vector Store:
1. `core/embedding.py` — Contrato `EmbeddingProvider` con método `embed(texts: list[str]) -> list[list[float]]`
2. `core/embedding_gemini.py` — Implementación Gemini API (default)
3. `core/embedding_bge_m3.py` — Implementación BGE-M3 local
4. `core/processor.py` — Chunking + llamada a `EmbeddingProvider` + guardado en VectorStore
5. `core/vector_store.py` — ChromaDB: `add()`, `search()`, `delete_collection()`

⚠️ **Pendiente decidir**: ¿LLM Gemini 2.5 Flash o mantener OpenAI gpt-4o-mini? (créditos Google disponibles)
