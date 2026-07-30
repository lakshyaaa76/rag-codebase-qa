# RAG-Powered Codebase Q&A Tool — Phase 0: Architecture & Design

---

## Current Phase: Phase 0 — Architecture & Design
## Completed Phases: None
## Pending Phases: 1 through 9

---

## Section 1 — Architecture Overview

### System Summary

The system is a full-stack RAG (Retrieval-Augmented Generation) application. Users submit a GitHub repository URL, the backend ingests and indexes the code, and users can then ask natural-language questions answered by an LLM grounded in retrieved code snippets.

### High-Level Component Map

```
┌──────────────────────────────────────────────────────────────────┐
│                         BROWSER (Next.js)                        │
│                                                                  │
│   ┌──────────────────┐        ┌─────────────────────────────┐   │
│   │  Repo Input Form │        │  Q&A Interface + Citations  │   │
│   └────────┬─────────┘        └──────────────┬──────────────┘   │
│            │                                 │                   │
└────────────┼─────────────────────────────────┼───────────────────┘
             │ POST /repos                      │ POST /query
             ▼                                  ▼
┌──────────────────────────────────────────────────────────────────┐
│                       FASTAPI BACKEND                            │
│                                                                  │
│  ┌────────────────┐  ┌─────────────────┐  ┌──────────────────┐  │
│  │  Ingestion API │  │  Indexing Logic  │  │  Query / RAG API │  │
│  │  (repos router)│  │  (background)    │  │  (query router)  │  │
│  └───────┬────────┘  └────────┬────────┘  └────────┬─────────┘  │
│          │                   │                     │            │
└──────────┼───────────────────┼─────────────────────┼────────────┘
           │                   │                     │
           ▼                   ▼                     ▼
   ┌───────────────┐  ┌────────────────────┐  ┌────────────────┐
   │  GitHub API   │  │  sentence-          │  │   OpenAI API     │
   │  (repo clone) │  │  transformers       │  │  (answer gen)  │
   └───────────────┘  │  (embeddings)       │  └────────────────┘
                      └────────┬───────────┘
                               │
                               ▼
                   ┌───────────────────────┐
                   │  Supabase PostgreSQL  │
                   │  + pgvector           │
                   │                       │
                   │  repos table          │
                   │  chunks table         │
                   │  (vector column)      │
                   └───────────────────────┘
```

### Request Flows

**Ingestion Flow:**
1. User submits GitHub URL → `POST /repos`
2. Backend creates a repo record with status `pending`
3. Backend clones/fetches repo via GitHub API (or `git clone`)
4. Files are filtered, read, and chunked
5. Chunks are embedded via `sentence-transformers`
6. Vectors + metadata stored in Supabase
7. Repo status updated to `ready`

**Query Flow:**
1. User submits question + repo_id → `POST /query`
2. Question is embedded
3. pgvector similarity search retrieves top-K chunks
4. Chunks + question sent to OpenAI API as context
5. OpenAI returns answer
6. Backend returns answer + source citations to frontend

---

## Section 2 — Folder Structure

```
rag-codebase-qa/
│
├── frontend/                        # Next.js application
│   ├── app/
│   │   ├── page.tsx                 # Home — repo URL input
│   │   ├── repo/
│   │   │   └── [repoId]/
│   │   │       └── page.tsx         # Q&A interface for a repo
│   │   └── layout.tsx
│   ├── components/
│   │   ├── RepoForm.tsx             # URL submission form
│   │   ├── QuestionInput.tsx        # Question input bar
│   │   ├── AnswerDisplay.tsx        # Answer + citations
│   │   ├── CitationCard.tsx         # Individual code citation
│   │   └── StatusBadge.tsx          # Repo indexing status
│   ├── lib/
│   │   └── api.ts                   # Typed API client (fetch wrappers)
│   ├── types/
│   │   └── index.ts                 # Shared TypeScript types
│   └── tailwind.config.ts
│
├── backend/                         # FastAPI application
│   ├── main.py                      # App entry point, router registration
│   ├── config.py                    # Settings via pydantic-settings (.env)
│   ├── database.py                  # Supabase client + connection helpers
│   │
│   ├── routers/
│   │   ├── repos.py                 # POST /repos, GET /repos/{id}
│   │   └── query.py                 # POST /query
│   │
│   ├── services/
│   │   ├── ingestion.py             # Repo fetch, file filtering
│   │   ├── chunker.py               # Chunking logic
│   │   ├── embedder.py              # sentence-transformers wrapper
│   │   ├── indexer.py               # Orchestrates ingestion → embed → store
│   │   └── retriever.py             # pgvector similarity search
│   │
│   ├── llm/
│   │   └── gpt_4o_mini.py                  # OpenAI API client, prompt builder
│   │
│   ├── models/
│   │   └── schemas.py               # Pydantic request/response models
│   │
│   └── utils/
│       ├── file_filter.py           # Extension + path allow/deny lists
│       └── github.py                # GitHub URL parsing helpers
│
├── .env.example
├── README.md
└── PROJECT_PROGRESS.md
```

**Why this structure:**
- Mirrors standard FastAPI and Next.js conventions, making it immediately readable to any developer
- `services/` separates business logic from HTTP routing — routers stay thin
- `llm/` is isolated so swapping OpenAI for another provider only touches one file
- No monorepo tooling needed at portfolio scale

---

## Section 3 — Database Design

### Technology: Supabase PostgreSQL + pgvector

**Chosen approach:** Single Supabase project, two tables (`repos`, `chunks`), pgvector extension enabled on the `chunks` table.

**Alternatives considered:**
| Option | Verdict |
|---|---|
| Pinecone (managed vector DB) | Adds an external service, cost, and complexity for no benefit at this scale |
| Weaviate / Qdrant (self-hosted) | Requires running a separate process; contradicts "no Docker" constraint |
| SQLite + sqlite-vec | Can't be used with Supabase; not production-ready for vector search |
| pgvector in Supabase | ✅ Single service, SQL joins possible, free tier sufficient, easy auth |

### Schema

#### Table: `repos`

```sql
CREATE TABLE repos (
    id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    github_url    TEXT NOT NULL UNIQUE,
    owner         TEXT NOT NULL,
    repo_name     TEXT NOT NULL,
    default_branch TEXT NOT NULL DEFAULT 'main',
    status        TEXT NOT NULL DEFAULT 'pending',
    -- status values: 'pending' | 'indexing' | 'ready' | 'failed'
    error_message TEXT,
    file_count    INTEGER,
    chunk_count   INTEGER,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);
```

#### Table: `chunks`

```sql
CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE chunks (
    id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    repo_id       UUID NOT NULL REFERENCES repos(id) ON DELETE CASCADE,

    -- Source location
    file_path     TEXT NOT NULL,       -- e.g. "src/utils/parser.py"
    language      TEXT,                -- e.g. "python", "typescript"
    start_line    INTEGER NOT NULL,
    end_line      INTEGER NOT NULL,

    -- Content
    content       TEXT NOT NULL,       -- raw code text of this chunk
    content_hash  TEXT NOT NULL,       -- SHA-256 of content (dedup guard)

    -- Chunk identity
    chunk_index   INTEGER NOT NULL,    -- position within the file
    chunk_type    TEXT,                -- 'function' | 'class' | 'block' | 'file_header'

    -- Vector
    embedding     VECTOR(768) NOT NULL, -- jinaai/jina-embeddings-v2-base-code produces 768 dims

    created_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Index for repo-scoped queries
CREATE INDEX ON chunks (repo_id);
```

**Why Exact Nearest Neighbor (ENN) instead of Vector Index (IVFFlat/HNSW):**
- Vector indexes like IVFFlat and HNSW perform Approximate Nearest Neighbor (ANN) search and are subject to the "post-filtering trap" when strongly filtered by `repo_id`.
- Because chunks are partitioned by `repo_id` (a few thousand chunks at most per repo), a B-Tree index on `repo_id` followed by sequential exact distance calculation guarantees 100% recall with zero noticeable speed penalty.

---

## Section 4 — Data Models (Pydantic)

These are the canonical shapes shared between backend logic and API responses.

```
RepoCreate       { github_url: str }
RepoResponse     { id, github_url, owner, repo_name, status, chunk_count, created_at }

QueryRequest     { repo_id: UUID, question: str, top_k: int = 5 }
ChunkCitation    { file_path, start_line, end_line, language, content, score }
QueryResponse    { answer: str, citations: list[ChunkCitation] }

IndexingStatus   { repo_id, status, file_count, chunk_count, error_message }
```

The `ChunkCitation` model is the key object passed from retriever → LLM prompt builder → API response → frontend renderer.

---

## Section 5 — API Contracts

### Base URL: `http://localhost:8000`

---

#### `POST /repos`
Submit a repository for indexing.

**Request body:**
```json
{ "github_url": "https://github.com/owner/repo" }
```

**Response `202 Accepted`:**
```json
{
  "id": "uuid",
  "github_url": "...",
  "owner": "...",
  "repo_name": "...",
  "status": "pending",
  "created_at": "..."
}
```

**Notes:** Returns immediately. Indexing runs in the background (FastAPI `BackgroundTasks`). If the URL was already indexed, returns the existing record.

---

#### `GET /repos/{repo_id}`
Poll indexing status.

**Response `200`:**
```json
{
  "id": "uuid",
  "status": "ready",         // pending | indexing | ready | failed
  "chunk_count": 842,
  "file_count": 34,
  "error_message": null
}
```

**Frontend polls this at ~2s intervals until `status` is `ready` or `failed`.**

---

#### `POST /query`
Ask a question about an indexed repository.

**Request body:**
```json
{
  "repo_id": "uuid",
  "question": "How does the authentication middleware work?",
  "top_k": 5
}
```

**Response `200`:**
```json
{
  "answer": "The authentication middleware...",
  "citations": [
    {
      "file_path": "src/middleware/auth.py",
      "start_line": 12,
      "end_line": 48,
      "language": "python",
      "content": "def authenticate(request):\n    ...",
      "score": 0.91
    }
  ]
}
```

**Error responses:**
- `404` — repo_id not found
- `409` — repo not yet in `ready` status
- `422` — validation error
- `500` — LLM or retrieval failure

---

## Section 6 — Processing Workflows

### 6.1 Repository Ingestion Workflow

```
POST /repos received
       │
       ▼
Parse & validate GitHub URL
  Extract: owner, repo_name, branch
       │
       ▼
Check if repo already exists in DB
  ├─ EXISTS & status=ready → return existing record
  └─ NEW → insert row (status=pending), enqueue background task
       │
       ▼
[Background Task begins]
       │
       ▼
Set status = 'indexing'
       │
       ▼
Fetch file tree via GitHub Contents API
  GET https://api.github.com/repos/{owner}/{repo}/git/trees/{branch}?recursive=1
       │
       ▼
Filter file list
  Keep: .py .ts .tsx .js .jsx .go .java .rs .rb .cpp .c .h .cs .md .json .yaml
  Drop: node_modules/, .git/, dist/, build/, __pycache__/, *.lock, binaries
  Cap:  max 500 files per repo (portfolio guard)
       │
       ▼
Fetch each file content via GitHub raw URL
  (sequential with small delay to respect rate limits)
       │
       ▼
Chunk each file → list of Chunk objects
       │
       ▼
Embed all chunks (batch)
       │
       ▼
Upsert chunks into Supabase (batch inserts)
       │
       ▼
Update repo: status='ready', file_count, chunk_count
```

**Why GitHub API (not git clone):**
- No filesystem management or subprocess complexity
- Works in any hosting environment without git installed
- Rate limit (60 unauthenticated / 5000 with token) is sufficient for portfolio scale
- Authenticated via `GITHUB_TOKEN` env var

---

### 6.2 Chunking Strategy

**Chosen approach: Hybrid — AST-aware for supported languages, sliding window fallback for others.**

#### Supported languages (AST-aware):
Python, JavaScript/TypeScript — use the `tree-sitter` library to extract:
- Top-level function definitions
- Class definitions (with their methods as sub-chunks)
- Module-level docstrings / file header comments

Each extracted node becomes one chunk. If a function exceeds 80 lines, it is split further with a 20-line overlap.

#### Fallback (sliding window):
For all other file types (Go, Rust, Markdown, JSON, etc.) — fixed sliding window:
- Window size: **60 lines**
- Overlap: **15 lines**
- Rationale: simple, predictable, no parser dependency

#### Chunk metadata captured per chunk:
```
file_path      — relative path from repo root
language       — detected from extension
start_line     — 1-indexed
end_line       — 1-indexed
chunk_type     — 'function' | 'class' | 'block' | 'file_header' | 'sliding_window'
chunk_index    — position index within the file
content        — raw text
content_hash   — SHA-256 for deduplication
```

**Why not pure sliding window?**
Semantic boundaries (functions, classes) are the natural unit of code meaning. Splitting across function boundaries reduces retrieval relevance. AST-aware chunking produces chunks that match the grain of questions ("how does X function work?").

**Why not purely AST-aware?**
Not every language has a reliable Python library for AST parsing. Sliding window as fallback ensures coverage.

**Alternatives considered:**
| Approach | Issue |
|---|---|
| Line-count only (e.g. 50 lines) | Cuts across logical boundaries constantly |
| File-level chunking | Too coarse; a 500-line file wastes context and dilutes retrieval |
| Semantic segmentation via LLM | Expensive, slow, overkill for Phase 0 |

---

### 6.3 Embedding Workflow

```
chunks: list[Chunk]
       │
       ▼
Extract content strings
       │
       ▼
Batch encode via SentenceTransformer('jinaai/jina-embeddings-v2-base-code')
  model.encode(texts, batch_size=8, show_progress_bar=False)
       │
       ▼
Returns: numpy array of shape (N, 384)
       │
       ▼
Convert to list[list[float]] for Supabase insertion
       │
       ▼
Bulk insert into chunks table
```

**Model loaded once at startup** (FastAPI lifespan event), not per request.

**Why `jinaai/jina-embeddings-v2-base-code`:**
- Already in the project spec
- 768 dimensions — small, fast, good enough for code similarity
- Runs on CPU without GPU requirement
- 14k+ stars on HuggingFace; well-tested

**Alternative:** `text-embedding-ada-002` (OpenAI) — better quality but adds API cost per indexing run and a network round trip. Not worth it for a portfolio project.

---

### 6.4 Retrieval Workflow

```
QueryRequest { repo_id, question, top_k }
       │
       ▼
Embed question using same SentenceTransformer model
       │
       ▼
pgvector cosine similarity search, scoped to repo_id:

  SELECT id, file_path, start_line, end_line, language, content,
         1 - (embedding <=> query_vec) AS score
  FROM chunks
  WHERE repo_id = :repo_id
  ORDER BY embedding <=> :query_vec
  LIMIT :top_k;
       │
       ▼
Return list[ChunkCitation] sorted by score desc
```

**Why cosine similarity over L2 distance:**
Cosine similarity is standard for sentence-transformer embeddings (unit-normalized vectors). L2 distance would produce equivalent ranking here, but cosine is the conventional choice and matches how the model was trained.

**top_k default = 5:** Enough context for OpenAI without blowing the context window. Adjustable per query.

---

### 6.5 OpenAI Answer-Generation Workflow

```
question: str
citations: list[ChunkCitation]
       │
       ▼
Build system prompt:
  "You are a code assistant. Answer questions about the repository 
   using only the code snippets provided. If the user asks personal 
   or out-of-domain questions, politely reject them with exactly: 
   'Please ask questions related to the project.' 
   Otherwise, if the answer is not in the provided snippets, say so. 
   Be concise and cite file paths."
       │
       ▼
Build user message:
  "Question: {question}

   Relevant code snippets:
   [1] File: src/auth/middleware.py (lines 12-48)
   ```python
   {content}
   ```

   [2] File: ...
   "
       │
       ▼
POST to OpenAI API
  model: gpt-4o-mini (or configured default)
  max_tokens: 1024
  temperature: 0.2  (low — factual, grounded answers)
       │
       ▼
Parse response text
       │
       ▼
Return QueryResponse { answer, citations }
```

**Why temperature 0.2:** We want factual, grounded answers anchored to retrieved code, not creative generation.

**Why include full chunk content in prompt:** OpenAI needs to see the actual code to reason about it. Reference numbers `[1]`, `[2]` allow the frontend to link answer text to citation cards if desired in a future phase.

---

## Section 7 — Design Decisions & Tradeoffs

### Decision 1: Background task via FastAPI `BackgroundTasks` (not Celery/Redis)

**Chosen:** FastAPI's built-in `BackgroundTasks`  
**Alternative:** Celery + Redis worker  
**Tradeoff:** `BackgroundTasks` runs in-process — if the server restarts mid-indexing, the task is lost. Celery persists tasks. However, Celery requires Redis, a separate worker process, and significant configuration. For a portfolio project with low concurrency, `BackgroundTasks` is sufficient. The frontend polls status; if status stays `pending` after a restart, users can resubmit.  
**Decision:** `BackgroundTasks` now. Phase 9 can introduce a task queue if needed.

---

### Decision 2: GitHub API (not `git clone`)

**Chosen:** GitHub Contents API + raw file fetching  
**Alternative:** `subprocess.run(['git', 'clone', url])`  
**Tradeoff:** `git clone` gives the full repo locally, making it easier to run `tree-sitter` on all files. GitHub API requires individual file fetches (rate-limited). However, `git clone` requires disk management, cleanup logic, and git to be installed. For portfolio scale (< 500 files), the API approach is cleaner.  
**Decision:** GitHub API. Phase 9 could add clone-based ingestion for large repos.

---

### Decision 3: Polling for indexing status (not WebSockets)

**Chosen:** `GET /repos/{id}` polling every 2 seconds  
**Alternative:** WebSocket connection or Server-Sent Events  
**Tradeoff:** Polling is simple to implement and debug. WebSockets add connection management complexity for no meaningful UX improvement on a task that takes 10–60 seconds.  
**Decision:** Polling. Revisit in Phase 8 if UX demands it.

---

### Decision 4: Single embedding model loaded at startup

**Chosen:** Load `jinaai/jina-embeddings-v2-base-code` once in FastAPI lifespan  
**Alternative:** Load on-demand per request  
**Tradeoff:** Loading the model takes ~2 seconds and ~90MB RAM. Loading per request would make every indexing and query request pay that cost. Loading at startup is the correct pattern.  
**Decision:** Lifespan-loaded singleton.

---

### Decision 5: Re-index on exact URL match only (no dedup by content)

**Chosen:** If the same `github_url` is submitted again and status is `ready`, return the existing record.  
**Alternative:** Hash the repo content tree and re-index only if changed  
**Tradeoff:** Content-aware dedup requires fetching the tree on every submission. Simpler to treat the URL as the identity key. Users can trigger a forced re-index via a future `DELETE /repos/{id}` + resubmit flow.  
**Decision:** URL-based dedup for Phase 0.

---

## Section 8 — Risks & Future Improvements

### Risks

| Risk | Mitigation |
|---|---|
| GitHub API rate limit (60 req/hr unauth) | Require `GITHUB_TOKEN` in env; authenticated limit is 5000/hr |
| Large repos (10k+ files) hit file cap | 500-file cap with clear error message; Phase 9 adds smarter filtering |
| Background task lost on server restart | Status stays `pending`; user can resubmit; Phase 9 adds persistent task tracking |
| OpenAI API unavailability | Wrap in try/except; return 503 with user-friendly message |
| Slow embedding on CPU for large repos | Batch size tuning; Phase 9 could offload to async worker |
| Prompt exceeds OpenAI context window | Cap top_k at 5; chunk content at 100 lines max; add character budget guard |

### Future Improvements (Phase 9 candidates)

- **Re-indexing:** `DELETE /repos/{id}` to allow fresh indexing of updated repos
- **Persistent task queue:** Replace `BackgroundTasks` with a lightweight queue (e.g. `arq` with Redis) for reliability
- **Vector Index Re-evaluation:** If repository scale ever exceeds what ENN can handle quickly, consider partitioned HNSW indexes.
- **Hybrid search:** Combine BM25 (keyword) + vector search for better precision on symbol names
- **Answer streaming:** Stream OpenAI response tokens to the frontend for better perceived performance
- **Rate limiting:** Per-IP limits on `/repos` and `/query` endpoints
- **Auth:** Supabase Auth for user-scoped repo collections

---

## Section 9 — Phase 0 Completion Checklist

- [x] System architecture designed and documented
- [x] Folder structure defined
- [x] Database schema designed (repos + chunks tables with pgvector)
- [x] Data models defined (Pydantic shapes)
- [x] API contracts defined (3 endpoints with full request/response shapes)
- [x] Repository ingestion workflow designed
- [x] Chunking strategy selected (hybrid AST-aware + sliding window)
- [x] Embedding workflow designed
- [x] Retrieval workflow designed
- [x] OpenAI answer-generation workflow designed (prompt template defined)
- [x] Error handling strategy defined
- [x] Major design decisions documented with tradeoffs
- [x] Risks identified with mitigations
- [x] Future scalability path identified

---

## What Phase 1 Should Build

**Phase 1 — Project Skeleton**

Phase 1 creates the empty but runnable project scaffolding based on the decisions above. No business logic yet.

Specifically:

**Backend:**
- Initialize FastAPI project with the exact folder structure from Section 2
- `main.py` with app creation, CORS middleware, and router stubs registered
- `config.py` using `pydantic-settings` loading from `.env`: `SUPABASE_URL`, `SUPABASE_KEY`, `GITHUB_TOKEN`, `OPENAI_API_KEY`
- `database.py` with Supabase client initialization
- `routers/repos.py` and `routers/query.py` as stubs returning placeholder `{"status": "not implemented"}` responses
- `models/schemas.py` with all Pydantic models from Section 4
- `requirements.txt` with pinned versions: `fastapi`, `uvicorn`, `supabase`, `pydantic-settings`, `sentence-transformers`, `httpx`

**Database:**
- SQL migration file (not applied yet, just written) for the `repos` and `chunks` tables from Section 3

**Frontend:**
- Initialize Next.js project with Tailwind CSS
- `lib/api.ts` with typed fetch wrappers for the 3 API endpoints (using the response shapes from Section 5)
- `types/index.ts` with TypeScript types matching the Pydantic models
- Page stubs: `/` (home) and `/repo/[repoId]` with placeholder UI
- Component files created but empty: `RepoForm`, `QuestionInput`, `AnswerDisplay`, `CitationCard`, `StatusBadge`

**Nothing else.** No ingestion logic, no embedding, no LLM calls. Phase 1 is purely structural — the skeleton on which all subsequent phases hang.