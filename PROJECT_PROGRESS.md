# Project Status

## Current Phase: Phase 2 â€” Repository Ingestion

---

## Phase Checklist

### Phase 0 â€” Architecture & Design
**Status: COMPLETED**

**Key Decisions Made:**
- Full-stack: Next.js frontend, FastAPI backend, Supabase PostgreSQL + pgvector
- Two database tables: `repos` (status tracking) and `chunks` (content + 384-dim vectors)
- GitHub Contents API for repo ingestion (not `git clone`)
- Hybrid chunking: AST-aware (tree-sitter) for Python/JS/TS, sliding window fallback for others
- `sentence-transformers` / `all-MiniLM-L6-v2` for embeddings (loaded once at startup)
- FastAPI `BackgroundTasks` for indexing (not Celery/Redis)
- Polling (`GET /repos/{id}` every 2s) for indexing status (not WebSockets)
- IVFFlat index on pgvector; cosine similarity; top_k = 5 default
- Grok API for answer generation; temperature 0.2; numbered citation blocks in prompt
- 3 API endpoints: `POST /repos`, `GET /repos/{id}`, `POST /query`

### Phase 1 â€” Project Skeleton
**Status: COMPLETED**

### Phase 2 â€” Repository Ingestion
**Status: NOT STARTED**

### Phase 3 â€” Chunking Engine
**Status: NOT STARTED**

### Phase 4 â€” Embedding & Vector Storage
**Status: NOT STARTED**

### Phase 5 â€” Indexing Pipeline
**Status: NOT STARTED**

### Phase 6 â€” Retrieval Layer
**Status: NOT STARTED**

### Phase 7 â€” Grok Answer Generation
**Status: NOT STARTED**

### Phase 8 â€” Frontend & UX
**Status: NOT STARTED**

### Phase 9 â€” Production Hardening
**Status: NOT STARTED**
