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
