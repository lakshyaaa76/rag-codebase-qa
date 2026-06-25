"""
Chunk database operations.

All direct Supabase interactions for the `chunks` table live here.
Mirrors the pattern established by services/repo_store.py for the `repos` table.

The only public function needed by Phase 4/5 is insert_chunks(), which takes
a list of ChunkResult objects plus their parallel embeddings and writes them
to Supabase in batches.

Phase 6 will add the similarity-search query used by the retriever.
"""

from __future__ import annotations

import logging
from uuid import UUID

from database import supabase
from services.chunker import ChunkResult

logger = logging.getLogger(__name__)

TABLE = "chunks"

# Supabase REST API has a practical row limit per request. 200 rows is
# conservative enough to stay well within payload size limits while keeping
# the number of round trips low for typical repos.
_INSERT_BATCH_SIZE = 200


def insert_chunks(
    repo_id: UUID,
    chunks: list[ChunkResult],
    embeddings: list[list[float]],
) -> int:
    """
    Insert all chunks for a repository into the `chunks` table.

    Rows are inserted in batches of _INSERT_BATCH_SIZE to avoid exceeding
    Supabase's request payload limits.

    Args:
        repo_id:    UUID of the parent repo row.
        chunks:     List of ChunkResult objects from services/chunker.py.
        embeddings: Parallel list of 384-dim float vectors from services/embedder.py.
                    Must be the same length as chunks.

    Returns:
        Total number of rows inserted.

    Raises:
        ValueError: if len(chunks) != len(embeddings).
        Exception:  re-raises any Supabase client error.
    """
    if len(chunks) != len(embeddings):
        raise ValueError(
            f"chunks ({len(chunks)}) and embeddings ({len(embeddings)}) must have equal length."
        )

    if not chunks:
        return 0

    repo_id_str = str(repo_id)
    rows = [
        {
            "repo_id":      repo_id_str,
            "file_path":    chunk.file_path,
            "language":     chunk.language,
            "start_line":   chunk.start_line,
            "end_line":     chunk.end_line,
            "content":      chunk.content,
            "content_hash": chunk.content_hash,
            "chunk_index":  chunk.chunk_index,
            "chunk_type":   chunk.chunk_type,
            "embedding":    embedding,
        }
        for chunk, embedding in zip(chunks, embeddings)
    ]

    total_inserted = 0
    for batch_start in range(0, len(rows), _INSERT_BATCH_SIZE):
        batch = rows[batch_start : batch_start + _INSERT_BATCH_SIZE]
        result = supabase.table(TABLE).insert(batch).execute()
        total_inserted += len(result.data)
        logger.debug(
            "Inserted batch %d-%d (%d rows) for repo %s",
            batch_start, batch_start + len(batch) - 1, len(batch), repo_id_str,
        )

    logger.info("Inserted %d chunks total for repo %s", total_inserted, repo_id_str)
    return total_inserted


def delete_chunks_for_repo(repo_id: UUID) -> None:
    """
    Delete all chunks belonging to a repo.

    In practice the ON DELETE CASCADE on the FK handles this automatically
    when a repo row is deleted. This function exists for explicit use in
    re-indexing workflows (Phase 9 candidate) where the repo row is kept
    but its chunks need to be replaced.
    """
    supabase.table(TABLE).delete().eq("repo_id", str(repo_id)).execute()
    logger.info("Deleted all chunks for repo %s", repo_id)