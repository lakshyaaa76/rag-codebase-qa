"""
Router: /repos

Endpoints:
  POST /repos            — submit a GitHub repository URL for indexing
  GET  /repos/{repo_id}  — poll the indexing status of a repository

Phase 2: both endpoints fully implemented.
Phase 5: background task wired to the real indexing pipeline.
  _run_indexing() now calls services/indexer.py which orchestrates
  ingestion → chunking → embedding → vector storage.
"""

import logging
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, HTTPException, Request, status

from models.schemas import IndexingStatus, RepoCreate, RepoResponse
from services import repo_store
from services.ingestion import fetch_default_branch
from utils.github import InvalidGitHubURLError, parse_github_url

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/repos", tags=["repos"])


# ---------------------------------------------------------------------------
# Background task — real pipeline (Phase 5)
# ---------------------------------------------------------------------------

async def _run_indexing(repo_id: UUID, request: Request) -> None:
    """
    Background task: run the full indexing pipeline for a repository.

    Retrieves the embedding model from app.state (loaded at startup in main.py)
    and passes it into index_repository() alongside the repo_id.

    Any exception is handled inside index_repository() which guarantees
    the repo status is set to 'failed' rather than left stuck in 'indexing'.
    """
    from services.indexer import index_repository  # local import avoids circular refs

    model = request.app.state.embedding_model
    await index_repository(repo_id=repo_id, model=model)


# ---------------------------------------------------------------------------
# POST /repos
# ---------------------------------------------------------------------------

@router.post(
    "",
    response_model=RepoResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Submit a repository for indexing",
)
async def submit_repo(
    payload: RepoCreate,
    background_tasks: BackgroundTasks,
    request: Request,
) -> RepoResponse:
    """
    Accept a GitHub repository URL and queue it for indexing.

    Behaviour:
      - If the URL has already been submitted and is ready/indexing/pending,
        return the existing record immediately (idempotent).
      - If the URL is in 'failed' state, reset it to 'pending' and re-queue.
      - Otherwise, create a new record and enqueue the indexing task.

    Returns 202 immediately. Poll GET /repos/{id} for status updates.
    """
    # --- Parse and validate the URL ---
    try:
        parsed = parse_github_url(payload.github_url)
    except InvalidGitHubURLError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc))

    normalized_url = f"https://github.com/{parsed.owner}/{parsed.repo_name}"

    # --- Idempotency check ---
    existing = repo_store.get_repo_by_url(normalized_url)
    if existing and existing["status"] in ("pending", "indexing", "ready"):
        return RepoResponse(**existing)

    # --- Resolve the default branch via GitHub API ---
    try:
        branch = parsed.branch or await fetch_default_branch(parsed.owner, parsed.repo_name)
    except Exception as exc:
        logger.error("Failed to fetch default branch for %s: %s", normalized_url, exc)
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Could not reach GitHub repository: {exc}",
        )

    # --- Create or reset the DB record ---
    if existing and existing["status"] == "failed":
        from database import supabase
        supabase.table("repos").update({
            "status": "pending",
            "error_message": None,
            "default_branch": branch,
        }).eq("id", existing["id"]).execute()
        repo_row = repo_store.get_repo_by_url(normalized_url)
    else:
        repo_row = repo_store.create_repo(
            github_url=normalized_url,
            owner=parsed.owner,
            repo_name=parsed.repo_name,
            default_branch=branch,
        )

    repo_id = UUID(repo_row["id"])

    # --- Enqueue background indexing task ---
    # request is passed so _run_indexing can access app.state.embedding_model
    background_tasks.add_task(_run_indexing, repo_id, request)
    logger.info("Enqueued indexing task for repo %s (%s)", repo_id, normalized_url)

    return RepoResponse(**repo_row)


# ---------------------------------------------------------------------------
# GET /repos/{repo_id}
# ---------------------------------------------------------------------------

@router.get(
    "/{repo_id}",
    response_model=IndexingStatus,
    summary="Get repository indexing status",
)
async def get_repo_status(repo_id: UUID) -> IndexingStatus:
    """
    Return the current indexing status for a repository.

    Poll this endpoint every ~2 seconds after submitting a repo.
    Status values: pending | indexing | ready | failed
    """
    row = repo_store.get_repo_by_id(repo_id)
    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Repository {repo_id} not found.",
        )
    return IndexingStatus(
        id=row["id"],
        status=row["status"],
        file_count=row.get("file_count"),
        chunk_count=row.get("chunk_count"),
        error_message=row.get("error_message"),
    )