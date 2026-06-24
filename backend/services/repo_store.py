"""
Repository database operations.

All direct Supabase interactions for the `repos` table live here.
Keeps the router and indexer thin — they call these functions,
not the Supabase client directly.

Functions follow a simple pattern:
  - Accept plain Python types (str, UUID, etc.)
  - Return dicts (raw Supabase rows) or raise on error
  - Callers convert to Pydantic models as needed
"""

import logging
from uuid import UUID

from database import supabase

logger = logging.getLogger(__name__)

TABLE = "repos"


def create_repo(
    github_url: str,
    owner: str,
    repo_name: str,
    default_branch: str,
) -> dict:
    """
    Insert a new repo row with status='pending'.

    Returns the inserted row as a dict.
    Raises an exception if the insert fails (e.g. duplicate URL).
    """
    result = (
        supabase.table(TABLE)
        .insert({
            "github_url": github_url,
            "owner": owner,
            "repo_name": repo_name,
            "default_branch": default_branch,
            "status": "pending",
        })
        .execute()
    )
    return result.data[0]


def get_repo_by_url(github_url: str) -> dict | None:
    """Return the repo row matching github_url, or None if not found."""
    result = (
        supabase.table(TABLE)
        .select("*")
        .eq("github_url", github_url)
        .limit(1)
        .execute()
    )
    return result.data[0] if result.data else None


def get_repo_by_id(repo_id: UUID) -> dict | None:
    """Return the repo row matching repo_id, or None if not found."""
    result = (
        supabase.table(TABLE)
        .select("*")
        .eq("id", str(repo_id))
        .limit(1)
        .execute()
    )
    return result.data[0] if result.data else None


def set_status_indexing(repo_id: UUID) -> None:
    """Transition repo to status='indexing'."""
    supabase.table(TABLE).update({"status": "indexing"}).eq("id", str(repo_id)).execute()
    logger.info("Repo %s → indexing", repo_id)


def set_status_ready(repo_id: UUID, file_count: int, chunk_count: int) -> None:
    """Transition repo to status='ready' and record final counts."""
    supabase.table(TABLE).update({
        "status": "ready",
        "file_count": file_count,
        "chunk_count": chunk_count,
    }).eq("id", str(repo_id)).execute()
    logger.info("Repo %s → ready (%d files, %d chunks)", repo_id, file_count, chunk_count)


def set_status_failed(repo_id: UUID, error_message: str) -> None:
    """Transition repo to status='failed' and store the error message."""
    # Truncate to avoid overflowing the column for very long tracebacks
    truncated = error_message[:1000]
    supabase.table(TABLE).update({
        "status": "failed",
        "error_message": truncated,
    }).eq("id", str(repo_id)).execute()
    logger.error("Repo %s → failed: %s", repo_id, truncated)