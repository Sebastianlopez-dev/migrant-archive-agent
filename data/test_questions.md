# Test Questions

Copy-paste one at a time. Commands assume `uv run python`.

---

## rag_test.py — Semantic Search

Questions for `backend/scripts/rag_test.py` (embedding search, no LLM).

### FILMIG Presentation (APgxfNssxGQ)

- ¿Qué es FILMIG y cuál es su propósito?
- ¿Quiénes organizan la FILMIG y qué otras entidades colaboran?
- ¿Cuándo y dónde se realizó la primera edición de FILMIG?
- ¿Qué tipo de actividades, géneros literarios y contenidos hay en la feria?
- ¿Cuál es el lema de FILMIG y qué hashtags se usan?

### Conversatorio Literatura Palestina (myxPJCDedOE)

- ¿Quiénes participaron en el conversatorio sobre literatura palestina?
- ¿Quién fue Ghassan Kanafani y por qué es relevante?
- ¿Cuál es la tensión entre estética y política en la literatura palestina?
- ¿Qué dijo Mahmoud Darwish sobre la poesía política?
- ¿Qué papel juega Sahar Khalifa en la literatura palestina?
- Según Mohammad Bitari, ¿el escritor palestino debe ser documentador o artista?
- ¿Qué relación tiene el lema "escribir es para valientes" con el conversatorio?
- ¿En qué video y minuto se habla de la Nakba?

---

## cero-01.py — Conversational RAG

Single-shot or REPL. Use `--verbose` to see source documents.

```bash
uv run python cero-01.py "pregunta"
uv run python cero-01.py --verbose "pregunta"
uv run python cero-01.py                # REPL mode
```

### Works — Experiential questions (semantic search)

| # | Question |
|---|----------|
| 1 | ¿qué sentimientos expresan las mujeres en los testimonios? |
| 2 | ¿cómo ayuda la escritura a las migrantes? |
| 3 | ¿cómo describen el apoyo entre mujeres migrantes? |
| 4 | ¿qué dicen sobre el dolor de migrar? |
| 5 | ¿cómo cambian las personas después de compartir sus historias? |
| 6 | ¿qué significa sororidad en los testimonios? |
| 7 | ¿cómo enfrentan la soledad? |
| 8 | ¿qué papel tiene la poesía en los relatos? |
| 9 | ¿hay experiencias de sanación o cura? |
| 10 | ¿cómo describen el proceso de migrar? |

### Does NOT work — Catalog questions (needs tools)

These require `list_videos` / `get_video_info` tools (not yet implemented).

| # | Question |
|---|----------|
| 1 | ¿qué videos tienes? |
| 2 | ¿cuántos testimonios hay? |
| 3 | dame la lista de videos |
| 4 | ¿cuál es el video más reciente? |
| 5 | ¿qué canales están indexados? |
