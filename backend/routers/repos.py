"""
Router: /repos

Endpoints:
  POST /repos            — submit a GitHub repository URL for indexing
  GET  /repos/{repo_id}  — poll the indexing status of a repository

Phase 2: both endpoints fully implemented.
  - POST /repos: validates URL, checks for existing record, inserts into DB,
    resolves the default branch via GitHub API, then enqueues a background
    indexing task.
  - GET /repos/{repo_id}: reads the repo row from Supabase and returns status.

The background task itself (index_repository) is stubbed here and will be
wired to the real pipeline in Phase 5.
"""

import logging
import traceback
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, HTTPException, status

from models.schemas import IndexingStatus, RepoCreate, RepoResponse
from services import repo_store
from services.ingestion import fetch_default_branch
from utils.github import InvalidGitHubURLError, parse_github_url

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/repos", tags=["repos"])


# ---------------------------------------------------------------------------
# Background task placeholder
# (Phase 5 will replace this with the real indexing pipeline)
# ---------------------------------------------------------------------------

async def _run_indexing(repo_id: UUID) -> None:
    """
    Background task: orchestrate the full indexing pipeline for a repo.

    Phase 2: stub that immediately marks the repo as failed with a clear
    'not yet implemented' message. This lets the status-polling flow be
    verified end-to-end without Phase 3–5 being complete.

    Phase 5 will replace this body with a call to services/indexer.py.
    """
    logger.info("Indexing task started for repo %s (stub — Phase 5 will implement)", repo_id)
    repo_store.set_status_failed(
        repo_id,
        "Indexing pipeline not yet implemented — coming in Phase 5.",
    )


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
        # Re-use the existing row: reset status to pending and clear error
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
    background_tasks.add_task(_run_indexing, repo_id)
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