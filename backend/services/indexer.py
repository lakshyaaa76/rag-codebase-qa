"""
Indexing pipeline orchestrator.

Wires together every prior phase into a single end-to-end workflow:

  Phase 2 — ingestion:  fetch file tree + file contents from GitHub
  Phase 3 — chunking:   split each file into ChunkResult objects
  Phase 4 — embedding:  encode chunk content into 384-dim vectors
  Phase 4 — storage:    insert chunks + vectors into Supabase

Called as a FastAPI BackgroundTask from routers/repos.py after a repo
row is created and set to status='pending'.

Error handling strategy:
  - Any unhandled exception in index_repository() is caught at the top level.
  - The repo status is set to 'failed' with the exception message.
  - The exception is re-logged at ERROR level with a full traceback.
  - This guarantees the repo never stays stuck in 'indexing' indefinitely.

The embedding model is passed in as an argument (not imported globally) so
the function can be called from the background task with the app.state instance
and is also straightforward to test with a mock model.
"""

from __future__ import annotations

import logging
import traceback
from typing import TYPE_CHECKING
from uuid import UUID

from services import repo_store
from services.chunk_store import insert_chunks
from services.chunker import chunk_file
from services.embedder import embed_chunks
from services.ingestion import fetch_file_tree, fetch_repo_files

if TYPE_CHECKING:
    from sentence_transformers import SentenceTransformer

logger = logging.getLogger(__name__)


async def index_repository(
    repo_id: UUID,
    model: "SentenceTransformer",
) -> None:
    """
    Run the full indexing pipeline for a repository.

    Steps:
      1. Mark the repo as 'indexing'.
      2. Read owner, repo_name, default_branch from the DB row.
      3. Fetch the filtered file tree from GitHub.
      4. Fetch each file's content from GitHub.
      5. Chunk every file.
      6. Embed all chunks in one batch call.
      7. Insert chunks + embeddings into Supabase.
      8. Mark the repo as 'ready' with final file_count and chunk_count.

    On any exception:
      - Marks the repo as 'failed' with the exception message.
      - Logs the full traceback at ERROR level.

    Args:
        repo_id: UUID of the repo row (must already exist in DB).
        model:   Loaded SentenceTransformer from app.state.embedding_model.
    """
    logger.info("Indexing pipeline started for repo %s", repo_id)

    # ------------------------------------------------------------------ #
    # Step 1 — transition to 'indexing'
    # ------------------------------------------------------------------ #
    try:
        repo_store.set_status_indexing(repo_id)
    except Exception as exc:
        logger.error("Failed to set status=indexing for repo %s: %s", repo_id, exc)
        return  # Can't proceed if we can't even read the row

    # ------------------------------------------------------------------ #
    # Steps 2–8 — full pipeline, all errors caught here
    # ------------------------------------------------------------------ #
    try:
        # Step 2 — load repo metadata
        repo_row = repo_store.get_repo_by_id(repo_id)
        if repo_row is None:
            raise RuntimeError(f"Repo row {repo_id} not found after status update.")

        owner        = repo_row["owner"]
        repo_name    = repo_row["repo_name"]
        branch       = repo_row["default_branch"]

        logger.info(
            "Indexing %s/%s @ %s (repo_id=%s)",
            owner, repo_name, branch, repo_id,
        )

        # Step 3 — fetch filtered file tree
        file_paths = await fetch_file_tree(owner, repo_name, branch)
        if not file_paths:
            raise RuntimeError(
                f"No indexable files found in {owner}/{repo_name}. "
                "The repository may be empty or all files were filtered out."
            )
        logger.info("File tree: %d files to fetch", len(file_paths))

        # Step 4 — fetch file contents
        fetched_files = await fetch_repo_files(owner, repo_name, branch, file_paths)
        if not fetched_files:
            raise RuntimeError(
                f"All {len(file_paths)} files were skipped (binary, empty, or non-UTF-8). "
                "Nothing to index."
            )
        logger.info("Fetched %d files successfully", len(fetched_files))

        # Step 5 — chunk all files
        all_chunks = []
        for fetched_file in fetched_files:
            file_chunks = chunk_file(fetched_file)
            all_chunks.extend(file_chunks)

        if not all_chunks:
            raise RuntimeError("Chunking produced zero chunks. Nothing to embed.")

        logger.info(
            "Chunking complete: %d files → %d chunks",
            len(fetched_files), len(all_chunks),
        )

        # Step 6 — embed all chunks
        logger.info("Embedding %d chunks...", len(all_chunks))
        embeddings = embed_chunks(model, all_chunks)
        logger.info("Embedding complete.")

        # Step 7 — store chunks + vectors
        inserted = insert_chunks(repo_id, all_chunks, embeddings)
        logger.info("Stored %d chunk rows in Supabase.", inserted)

        # Step 8 — mark ready
        repo_store.set_status_ready(
            repo_id,
            file_count=len(fetched_files),
            chunk_count=inserted,
        )
        logger.info(
            "Indexing complete for repo %s: %d files, %d chunks.",
            repo_id, len(fetched_files), inserted,
        )

    except Exception as exc:
        error_msg = f"{type(exc).__name__}: {exc}"
        logger.error(
            "Indexing failed for repo %s:\n%s",
            repo_id,
            traceback.format_exc(),
        )
        repo_store.set_status_failed(repo_id, error_msg)