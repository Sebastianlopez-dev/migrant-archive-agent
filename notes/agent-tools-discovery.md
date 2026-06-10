# Agent Tools — Two Data Sources, One Agent

**Discovery**: ingestion produces two usable data layers per video, not one.

| Layer | Source | Format | For |
|-------|--------|--------|-----|
| **Transcript** | `transcript_segments` + `full_text` | Text with timestamps | Semantic Q&A (RAG) |
| **Metadata** | `metadata` dict (75 keys) | Structured fields | Analytics, stats, comparisons |

This means **Cero** can answer both "What did they say?" and "How well did the video perform?"

---

## 15 Possible Tools

### Transcript tools (semantic search)

| # | Tool | What it does | Example query |
|---|------|-------------|---------------|
| 1 | `search_transcripts` | Semantic search across ChromaDB chunks | "¿Qué dijo sobre descolonizar la cultura?" |
| 2 | `get_transcript_context` | Return surrounding segments around a timestamp | "Dame el minuto 2:30 con contexto" |
| 3 | `list_sources` | Return video titles + IDs used in a response | "¿De qué videos viene esta respuesta?" |

### Single-video stats tools

| # | Tool | Metadata keys used | Example query |
|---|------|-------------------|---------------|
| 4 | `get_video_stats` | `view_count`, `like_count`, `duration`, `upload_date`, `comment_count` | "Stats del video APgxfNssxGQ" |
| 5 | `engagement_rate` | `like_count / view_count` | "¿Cuál es el engagement del video?" |
| 6 | `video_age` | `upload_date` → days since upload | "¿Hace cuánto se subió este video?" |
| 7 | `get_video_description` | `description` | "Resumime de qué trata el video" |

### Channel-wide analytics tools

| # | Tool | What it does | Example query |
|---|------|-------------|---------------|
| 8 | `top_videos_by_views` | Rank by view_count DESC, return top N | "Top 5 más vistos" |
| 9 | `top_videos_by_likes` | Rank by like_count DESC, return top N | "Top 5 más gustados" |
| 10 | `total_channel_views` | Sum all view_counts | "¿Cuántas vistas totales?" |
| 11 | `avg_video_duration` | Mean duration across all videos | "¿Cuánto duran en promedio?" |
| 12 | `publishing_frequency` | Group upload_dates by month/week | "¿Cada cuánto suben videos?" |
| 13 | `duration_distribution` | Bucket durations (0-5min, 5-15min, etc.) | "¿Son videos cortos o largos?" |
| 14 | `most_used_tags` | Frequency count of tags across channel | "¿De qué temas hablan más?" |
| 15 | `compare_videos` | Side-by-side diff of any two videos | "Compará el video A con el B" |

---

## Agent Architecture

```
User question → Cero (LangChain agent)
    │
    ├─ "¿Qué dijo sobre...?"  → router → search_transcripts (ChromaDB)
    ├─ "¿Cuál es el más...?"  → router → top_videos_by_views (metadata)
    └─ "¿Promedio de...?"     → router → avg_video_duration (metadata)
```

Single agent, many tools. The agent decides which tool to use based on the question.
All tools read from the same `data/raw/whisper/` JSON collection.

---

## Implementation note

Tools 4-15 don't need embeddings or ChromaDB — they query structured `metadata` fields.
A simple `json.load()` loop over all saved JSONs is enough for channel-wide analytics.
For 50 videos (< 5MB total JSON), this is instant.

When to add a database: if the channel grows past 500+ videos, swap the JSON loop for SQLite.
