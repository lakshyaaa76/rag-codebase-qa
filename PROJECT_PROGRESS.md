# Project Status

## Current Phase: Phase 8 — Frontend & UX

---

## Phase Checklist

### Phase 0 — Architecture & Design
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

**Architectural Assumptions Introduced:**
- Repo uniqueness keyed on exact `github_url` string
- 500-file cap per repo (portfolio safeguard)
- Chunk embedding dimension: 384 (all-MiniLM-L6-v2)
- Status lifecycle: `pending → indexing → ready | failed`

**Unresolved Questions (deferred to later phases):**
- tree-sitter exact grammar packages to install (Phase 3)
- Grok model string to use — `grok-3` assumed, confirm at Phase 7
- Supabase project region (user decision)
- Whether to add `DELETE /repos/{id}` for re-indexing (Phase 9 candidate)

---

### Phase 1 — Project Skeleton
**Status: COMPLETED**

**Purpose:** Create the initial frontend and backend structure based on Phase 0 decisions. No business logic — runnable scaffolding only.

**Deliverables completed:**
- FastAPI app (`main.py`) with CORS middleware, lifespan hook, router registration, `/health` endpoint
- `config.py` — pydantic-settings loading all env vars from `backend/.env`
- `database.py` — Supabase client singleton
- `models/schemas.py` — all Pydantic models: `RepoCreate`, `RepoResponse`, `IndexingStatus`, `QueryRequest`, `ChunkCitation`, `QueryResponse`, `ErrorResponse`
- `routers/repos.py` — `POST /repos` and `GET /repos/{id}` stubs (501 Not Implemented)
- `routers/query.py` — `POST /query` stub (501 Not Implemented)
- `services/` — five stub modules: `ingestion.py`, `chunker.py`, `embedder.py`, `indexer.py`, `retriever.py`
- `llm/grok.py` — stub with prompt design notes
- `utils/file_filter.py` — fully implemented allow/deny lists (usable from Phase 2)
- `utils/github.py` — fully implemented GitHub URL parser (usable from Phase 2)
- `backend/requirements.txt` — pinned dependencies
- `database/001_initial_schema.sql` — complete migration for `repos` + `chunks` tables with pgvector, IVFFlat index, and `updated_at` trigger
- Next.js 15 + Tailwind CSS frontend scaffold
- `frontend/types/index.ts` — TypeScript types mirroring all Pydantic models
- `frontend/lib/api.ts` — typed fetch wrappers for all 3 endpoints
- `frontend/components/` — five component stubs: `RepoForm`, `StatusBadge`, `QuestionInput`, `CitationCard`, `AnswerDisplay`
- `frontend/app/page.tsx` — home page stub
- `frontend/app/repo/[repoId]/page.tsx` — Q&A page stub
- `frontend/app/layout.tsx`, `globals.css`, config files
- `.env.example`, `.gitignore`

**Assumptions introduced:**
- `utils/file_filter.py` and `utils/github.py` are fully implemented (not stubbed) since they have no dependencies and will be needed immediately in Phase 2
- Frontend uses `@/` path alias (maps to `frontend/` root) via `tsconfig.json`
- `NEXT_PUBLIC_API_URL` env var controls backend URL for the frontend client

---

### Phase 2 — Repository Ingestion
**Status: COMPLETED**

**Purpose:** Implement repository acquisition and processing — GitHub API file tree fetch, file content retrieval, DB insert, background task wiring.

**Deliverables completed:**
- `services/ingestion.py` — fully implemented:
  - `fetch_default_branch()` — resolves default branch via GitHub Repos API
  - `fetch_file_tree()` — recursive Git Trees API call, applies `is_allowed()` filter, enforces 500-file cap
  - `fetch_file_content()` — fetches raw file content, skips binary/non-UTF-8 files silently
  - `fetch_repo_files()` — orchestrates sequential fetch of all files with rate-limit delay
  - `FetchedFile` dataclass — carries `file_path`, `content`, `language`, `content_hash`
  - `_detect_language()` — extension-to-language-label mapping for 20+ file types
- `services/repo_store.py` — new module, all `repos` table DB operations:
  - `create_repo()`, `get_repo_by_url()`, `get_repo_by_id()`
  - `set_status_indexing()`, `set_status_ready()`, `set_status_failed()`
- `routers/repos.py` — fully implemented (replacing Phase 1 stubs):
  - `POST /repos`: validates URL, normalises it, idempotency check, resolves branch, creates DB record, enqueues background task
  - `GET /repos/{repo_id}`: reads from DB, returns `IndexingStatus`, 404 if not found
  - Background task `_run_indexing`: stub that sets status=failed with "Phase 5" message (real pipeline in Phase 5)

**Implementation decisions made:**
- Added `services/repo_store.py` as a new module not explicitly named in Phase 0. Rationale: keeping all Supabase table operations for `repos` in one place makes the router and indexer easier to read and test. This is an organisational refinement, not an architectural change.
- URL normalisation: the URL stored in DB is always `https://github.com/{owner}/{repo}` (trailing slashes, `/tree/branch` suffixes, and case stripped). Idempotency key is the normalised URL, not the raw submitted string.
- Re-submission of a `failed` repo resets it to `pending` in-place rather than creating a new row. This preserves the repo's UUID across retry attempts, which matters for any future UI that links directly to `/repo/{id}`.
- Background task is a coroutine (`async def`) to allow `await` inside it in Phase 5 when the real async indexing pipeline is wired in.

**Deviations from Phase 0 design:**
- None. All decisions follow the Phase 0 architecture exactly.

**Unresolved questions carried forward:**
- `_run_indexing` background task body is a stub — Phase 5 replaces it with `services/indexer.py`

---

### Phase 3 — Chunking Engine
**Status: COMPLETED**
**Purpose:** Implement code chunk generation strategy.

**Deliverables completed:**
- `services/chunker.py` — fully implemented:
  - `ChunkResult` dataclass — all fields the `chunks` table expects except `repo_id` and `embedding`
  - `chunk_file(fetched_file)` — public entry point; dispatches to AST-aware or sliding window
  - `_chunk_ast_aware()` — extracts top-level functions and classes via tree-sitter; falls back gracefully on any parse failure
  - `_get_top_level_nodes()` — isolated tree-sitter call; all grammar imports in try/except for safe degradation
  - `_sliding_window()` — 60-line window, 15-line overlap, parameterised `start_offset` for whole files and node sub-ranges
  - Oversized AST nodes (> 80 lines) sub-chunked with sliding window, preserving `chunk_type`
  - Uncovered file regions emitted as `file_header` (line 1) or `block`; blank-only runs skipped
  - `content_hash` SHA-256, deterministic; `chunk_index` sequential from 0 per file
- `backend/requirements.txt` — three new pinned packages added:
  - `tree-sitter==0.21.3`, `tree-sitter-python==0.21.0`, `tree-sitter-javascript==0.21.4`

**Implementation decisions made:**
- **tree-sitter 0.21.3 pinned** — resolved Phase 0 open question. API is `Language(capsule, name)` + `parser.set_language(lang)`. Pinned to prevent silent breakage on upgrade to 0.22+.
- **Single JS grammar for TypeScript** — `tree-sitter-javascript` handles `.ts`/`.tsx`. A dedicated `tree-sitter-typescript` adds a second grammar dependency with marginal benefit at portfolio scale.
- **`_get_top_level_nodes` fully isolated** — tree-sitter imports are inside the function. Backend starts and works even without tree-sitter installed; affected files fall back to sliding window.
- **Class methods not extracted as sub-chunks** — methods included in the class chunk body. Extracting them would fragment small classes and duplicate context. Revisit in Phase 9 if retrieval quality demands it.
- **`chunk_index` ordering** — AST nodes emitted in tree order, uncovered regions appended after. Not strictly line-ascending; acceptable since retrieval uses cosine similarity, not line order.
- **Export unwrapping for JS/TS** — `export function foo()` and `function foo()` both produce `function` chunk type via `export_statement` unwrapping.

**Deviations from Phase 0 design:**
- Method-level sub-chunking of classes deferred (see above).
- All other Phase 0 chunking decisions implemented exactly as specified.

**Manual actions required before Phase 4:**
- Install the three new tree-sitter packages:
  ```powershell
  cd backend
  .\.venv\Scripts\Activate.ps1
  pip install -r requirements.txt
  ```

---

---

### Phase 4 — Embedding & Vector Storage
**Status: COMPLETED**
**Purpose:** Implement embeddings and vector persistence.

**Deliverables completed:**
- `services/embedder.py` — fully implemented:
  - `load_model()` — loads `all-MiniLM-L6-v2` via sentence-transformers; called once at startup
  - `embed_chunks(model, chunks)` — encodes `list[ChunkResult]` → `list[list[float]]` (384 dims, parallel to input)
  - `embed_query(model, question)` — encodes a single question string → `list[float]`
  - `_encode()` — shared internal helper; `normalize_embeddings=True` so cosine similarity equals dot product, consistent with pgvector's `<=>` operator
  - `TYPE_CHECKING` guard on `SentenceTransformer` import so module loads cleanly even without the package installed
- `services/chunk_store.py` — new module, all `chunks` table DB operations:
  - `insert_chunks(repo_id, chunks, embeddings)` — builds rows from parallel lists, inserts in batches of 200, returns total inserted count; raises `ValueError` on length mismatch
  - `delete_chunks_for_repo(repo_id)` — explicit chunk deletion for future re-indexing (Phase 9 candidate); ON DELETE CASCADE on the FK handles implicit deletion
- `main.py` — lifespan updated: model loaded at startup via `load_model()`, stored on `app.state.embedding_model`; TODO comment removed

**Implementation decisions made:**
- **`normalize_embeddings=True` in `_encode()`** — all-MiniLM-L6-v2 is trained with normalised output; explicitly normalising ensures the pgvector `<=>` (cosine) operator gives correct results even if a future model swap doesn't normalise by default.
- **Batch size 64** — conservative safe default for CPU. No config setting added for it at this phase; easy to expose via `settings` in Phase 9 if profiling shows it matters.
- **Batch insert size 200** — Supabase's REST API serialises rows as JSON. At 384 floats × 4 bytes each, 200 rows ≈ 300 KB payload, well within limits. 500 rows could work but 200 gives a comfortable margin.
- **`chunk_store.py` as a new module** — same rationale as `repo_store.py` in Phase 2: all table operations in one place, router/indexer stay thin.
- **Model stored on `app.state`, not a module-level global** — avoids import-time side effects and makes the model injectable for testing. Phase 5 and 6 will access it as `request.app.state.embedding_model` (retriever) and directly as a parameter passed from the indexer background task.

**Deviations from Phase 0 design:**
- None. Phase 0 specified: model loaded once at startup on `app.state`, sentence-transformers, all-MiniLM-L6-v2, 384 dims, batch encoding. All implemented exactly as designed.

**Manual actions required before Phase 5:**
- None additional. `sentence-transformers==3.3.1` was already in `requirements.txt` from Phase 1. Run `pip install -r requirements.txt` if not done since Phase 1.
- On first `uvicorn` startup the model (~90 MB) will be downloaded from HuggingFace and cached in `~/.cache/huggingface/`. Subsequent startups use the cache and take ~2 seconds.

---

---

### Phase 5 — Indexing Pipeline
**Status: COMPLETED**
**Purpose:** Build the end-to-end indexing workflow.

**Deliverables completed:**
- `services/indexer.py` — fully implemented:
  - `index_repository(repo_id, model)` — async orchestrator that runs the full pipeline:
    1. `set_status_indexing()`
    2. Load repo metadata from DB (owner, repo_name, default_branch)
    3. `fetch_file_tree()` — GitHub API filtered file list
    4. `fetch_repo_files()` — fetch content for all files
    5. `chunk_file()` — chunk every fetched file, accumulate all ChunkResults
    6. `embed_chunks()` — encode all chunks in one batch call
    7. `insert_chunks()` — write chunks + vectors to Supabase
    8. `set_status_ready()` — record final file_count and chunk_count
  - Top-level exception handler: any failure sets `status=failed` with the exception message; full traceback logged at ERROR; repo never left stuck in `indexing`
  - Three explicit early-exit RuntimeErrors: empty file tree, all files skipped, zero chunks after chunking
- `routers/repos.py` — updated:
  - `_run_indexing(repo_id, request)` — stub replaced with real call to `index_repository()`; `request` parameter added to access `app.state.embedding_model`
  - `submit_repo()` — `Request` added as a parameter; `background_tasks.add_task(_run_indexing, repo_id, request)` passes the request through

**Implementation decisions made:**
- **Model passed as argument, not imported globally** — `index_repository(repo_id, model)` receives the model explicitly. This keeps the indexer testable with a mock model and avoids any import-time coupling to `app.state`. The router is the only place that reads from `app.state`.
- **Local import of `index_repository` in `_run_indexing`** — `from services.indexer import index_repository` is a local import inside the function to avoid potential circular import chains at module load time (router → indexer → chunker → ingestion, etc.). This is a standard Python pattern for background tasks.
- **`Request` injected into `submit_repo`** — FastAPI injects `Request` automatically when declared as a parameter (no annotation needed beyond the type hint). This is the idiomatic FastAPI pattern for accessing `app.state` from a route handler without globals.
- **Chunking loop is sequential per file** — `for fetched_file in fetched_files: all_chunks.extend(chunk_file(fetched_file))`. Simple and correct. All chunks are accumulated before the single `embed_chunks()` batch call, which is more efficient than embedding per-file.
- **`file_count` = len(fetched_files), not len(file_paths)** — counts successfully fetched files, not the raw file tree count. This is the number the DB stores in `repos.file_count` and what the frontend will display. More accurate than counting before any files are skipped.

**Deviations from Phase 0 design:**
- None. Phase 0 specified: `BackgroundTasks`, orchestrated ingestion→chunk→embed→store pipeline, status transitions. All implemented exactly as designed.

**Manual actions required before Phase 6:**
- None. All dependencies were already installed in prior phases.

---

---

### Phase 6 — Retrieval Layer
**Status: COMPLETED**
**Purpose:** Retrieve relevant code for questions.

**Deliverables completed:**
- `database/002_match_chunks_function.sql` — new migration:
  - `match_chunks(query_embedding, match_repo_id, match_count)` Postgres function
  - Returns `id, repo_id, file_path, language, start_line, end_line, content, chunk_type, similarity`
  - `similarity` computed as `1 - (embedding <=> query_embedding)` (cosine, 0.0–1.0)
  - Scoped to a single `repo_id`; ordered by `embedding <=> query_embedding` ascending (most similar first)
- `services/chunk_store.py` — `search_chunks()` added:
  - Calls `supabase.rpc("match_chunks", {...}).execute()`
  - Passes `query_embedding`, `match_repo_id`, `match_count`; returns `result.data` list of dicts
- `services/retriever.py` — fully implemented:
  - `retrieve_chunks(model, repo_id, question, top_k)` — embeds question, calls `search_chunks`, maps rows to `ChunkCitation` models
  - Malformed rows are logged at WARNING and skipped; never raise for a single bad row
  - Returns `list[ChunkCitation]` sorted by score descending (as returned by pgvector)
- `routers/query.py` — fully implemented:
  - `POST /query` validates repo exists (404) and is `ready` (409)
  - Retrieves `app.state.embedding_model` from `Request`
  - Calls `retrieve_chunks()`, returns `QueryResponse` with citations
  - `answer` field is a placeholder string — replaced in Phase 7

**Implementation decisions made:**
- **RPC function over direct `.select().order()`** — the Supabase PostgREST client's `.order()` only accepts plain column names; it cannot express `ORDER BY embedding <=> $1`. A Postgres function is the standard Supabase pattern for pgvector search and keeps vector math server-side near the index.
- **New DB migration file `002_match_chunks_function.sql`** — same apply-via-Dashboard pattern as migration 001. Kept separate from the schema migration so it can be re-run independently if the function needs updating.
- **`similarity` = `1 - cosine_distance`** — pgvector's `<=>` is cosine *distance* (0 = identical, 2 = opposite). Subtracting from 1 gives an intuitive similarity score (1.0 = identical) that the frontend displays as "% match".
- **`LANGUAGE sql STABLE`** — `STABLE` tells Postgres the function produces the same output for the same inputs within a single query, enabling query planner optimisations. Correct here since we're doing a read-only ordered scan.
- **Placeholder answer in Phase 6** — the `POST /query` endpoint returns a clearly-labelled placeholder string rather than `501`. This means the full request/response contract is testable end-to-end (citations included) without Phase 7 being complete.

**Deviations from Phase 0 design:**
- None. Phase 0 specified cosine similarity via pgvector, scoped to `repo_id`, top_k=5 default, returning `ChunkCitation` objects. All implemented exactly as designed.

**Manual actions required before Phase 7:**
- Run migration `002_match_chunks_function.sql` in Supabase Dashboard → SQL Editor:
  ```
  Supabase Dashboard → SQL Editor → paste database/002_match_chunks_function.sql → Run
  ```
  This must be applied before any query requests will return results (the RPC call will 404 without it).

---

---

### Phase 7 — Grok Answer Generation
**Status: COMPLETED**
**Purpose:** Generate grounded answers using retrieved code.

**Deliverables completed:**
- `llm/grok.py` — fully implemented:
  - `build_user_message(question, citations)` — constructs numbered citation blocks `[1]`, `[2]`, ... with file path, line range, language fence, and content; truncates any single chunk exceeding 3,000 chars; returns formatted string
  - `generate_answer(question, citations)` — async function; POSTs to `https://api.x.ai/v1/chat/completions`; reads `settings.grok_model`, `settings.grok_max_tokens`, `settings.grok_temperature`; extracts `choices[0].message.content`; strips whitespace; propagates HTTP and shape errors
  - `_SYSTEM_PROMPT` — 440-char grounding instruction: answer only from provided snippets, cite by number, state clearly if answer not present
- `routers/query.py` — updated:
  - Placeholder string replaced with `await generate_answer(question, citations)`
  - Grok exceptions caught and re-raised as `HTTP 502 Bad Gateway` with the error message in `detail`
  - TODO comment removed

**Implementation decisions made:**
- **`httpx.AsyncClient` over the OpenAI Python SDK** — Grok's OpenAI-compatible endpoint is a simple REST call; adding the OpenAI SDK as a dependency just to wrap one HTTP call is unnecessary weight. `httpx` is already in `requirements.txt` from Phase 2.
- **`502 Bad Gateway` for Grok failures** — a Grok API error (rate limit, outage, bad key) is a downstream service failure, not a client error. `502` is the correct HTTP semantic; the `detail` field carries the exception message so the frontend can show a useful error.
- **`_CHUNK_CONTENT_MAX_CHARS = 3_000`** — conservative cap per chunk. A 60-line chunk at ~50 chars/line is ~3,000 chars naturally; the cap guards against a pathological chunk (e.g. a minified file that slipped through filtering) filling the entire context window.
- **System prompt does not use `LANGUAGE sql STABLE`-style directives** — kept plain English, concise (440 chars). Overly long system prompts at low temperature can cause the model to echo instructions back in the answer.
- **Answer `.strip()`** — Grok sometimes returns leading/trailing whitespace or a trailing newline; stripping before returning keeps the frontend rendering clean.
- **`grok_model` confirmed as `"grok-3"`** — resolves the Phase 0 open question. Value is read from `settings.grok_model` so it can be overridden via `.env` without a code change.

**Deviations from Phase 0 design:**
- None. Phase 0 specified: Grok API, temperature 0.2, max_tokens 1024, system grounding prompt, numbered citation blocks. All implemented exactly as designed.

**Manual actions required before Phase 8:**
- None. No new dependencies added (`httpx` was already present).
- Ensure `GROK_API_KEY` is set in the root `.env` file before running the backend end-to-end.

---

---

### Phase 8 — Frontend & UX
**Status: NOT STARTED**
**Purpose:** Create the complete user experience.

---

### Phase 9 — Production Hardening
**Status: NOT STARTED**
**Purpose:** Add caching, safeguards, monitoring and robustness improvements.

---

## Progress Update Rules

Whenever a phase is completed:

1. Mark the phase as COMPLETED.
2. Update Current Phase.
3. Record key decisions made.
4. Record architectural changes.
5. Record assumptions introduced.
6. Record unresolved questions.
7. Keep this file current throughout the project.

This file is the project's source of truth.