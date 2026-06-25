from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from config import settings
from routers import repos, query

@asynccontextmanager
async def lifespan(app: FastAPI):
    # TODO (Phase 4): load SentenceTransformer model onto app.state
    print("RAG Codebase Q&A backend started.")
    yield
    print("RAG Codebase Q&A backend shut down.")

app = FastAPI(
    title="RAG Codebase Q&A",
    description="Ask natural-language questions about any GitHub repository.",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(repos.router)
app.include_router(query.router)

@app.get("/health", tags=["meta"])
async def health() -> dict:
    return {"status": "ok", "version": "0.1.0"}
"""
RAG Codebase Q&A — FastAPI application entry point.

Responsibilities:
  - Create the FastAPI app instance
  - Register CORS middleware
  - Register routers
  - Define lifespan (startup/shutdown) for model loading
  - Expose a /health endpoint for local verification
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from config import settings
from routers import repos, query


# ---------------------------------------------------------------------------
# Lifespan — runs on startup and shutdown
# ---------------------------------------------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan manager.

    Startup:
      - Loads all-MiniLM-L6-v2 via sentence-transformers once and stores
        it on app.state.embedding_model. All services (indexer, retriever)
        access the model via this shared instance — no repeated loading.

    Shutdown:
      - No explicit cleanup required; model is released with the process.
    """
    from services.embedder import load_model

    app.state.embedding_model = load_model()
    print("✓ RAG Codebase Q&A backend started.")
    yield
    print("✓ RAG Codebase Q&A backend shut down.")


# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------

app = FastAPI(
    title="RAG Codebase Q&A",
    description=(
        "Ask natural-language questions about any GitHub repository. "
        "Answers are grounded in retrieved code snippets."
    ),
    version="0.1.0",
    lifespan=lifespan,
)


# ---------------------------------------------------------------------------
# Middleware
# ---------------------------------------------------------------------------

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Routers
# ---------------------------------------------------------------------------

app.include_router(repos.router)
app.include_router(query.router)


# ---------------------------------------------------------------------------
# Health check
# ---------------------------------------------------------------------------

@app.get("/health", tags=["meta"], summary="Health check")
async def health() -> dict:
    """Returns 200 OK when the server is running."""
    return {"status": "ok", "version": "0.1.0"}