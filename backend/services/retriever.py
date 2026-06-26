"""
Retrieval service.

Responsible for:
  1. Embedding the user's question via services/embedder.py
  2. Running pgvector cosine similarity search via services/chunk_store.py
  3. Mapping raw DB rows to ChunkCitation Pydantic models
  4. Returning the top-K citations to the query router

Phase 0 design:
  - Cosine similarity, scoped to a single repo_id
  - top_k default = 5 (configurable per request, max 20)
  - Returns list[ChunkCitation] sorted by score descending
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING
from uuid import UUID

from models.schemas import ChunkCitation
from services.chunk_store import search_chunks
from services.embedder import embed_query

if TYPE_CHECKING:
    from sentence_transformers import SentenceTransformer

logger = logging.getLogger(__name__)


def retrieve_chunks(
    model: "SentenceTransformer",
    repo_id: UUID,
    question: str,
    top_k: int = 5,
) -> list[ChunkCitation]:
    """
    Embed a question and retrieve the most relevant code chunks for a repo.

    Steps:
      1. Embed the question with the shared model instance.
      2. Call search_chunks() which runs the match_chunks RPC against pgvector.
      3. Map each returned row to a ChunkCitation Pydantic model.

    Args:
        model:    SentenceTransformer from app.state.embedding_model.
        repo_id:  UUID of the indexed repository to search within.
        question: The user's natural-language question.
        top_k:    Maximum number of chunks to return (1–20).

    Returns:
        list[ChunkCitation] sorted by similarity score descending.
        May be shorter than top_k if the repo has fewer indexed chunks.
    """
    # Step 1 — embed the question
    query_vector = embed_query(model, question)
    logger.debug("Embedded query for repo %s: question='%s...'", repo_id, question[:60])

    # Step 2 — similarity search
    rows = search_chunks(repo_id=repo_id, query_embedding=query_vector, top_k=top_k)

    # Step 3 — map rows to ChunkCitation models
    citations: list[ChunkCitation] = []
    for row in rows:
        try:
            citations.append(
                ChunkCitation(
                    id=row["id"],
                    file_path=row["file_path"],
                    start_line=row["start_line"],
                    end_line=row["end_line"],
                    language=row.get("language"),
                    content=row["content"],
                    score=float(row["similarity"]),
                )
            )
        except (KeyError, ValueError) as exc:
            # Log and skip malformed rows rather than failing the whole request
            logger.warning("Skipping malformed chunk row %s: %s", row.get("id"), exc)

    logger.info(
        "Retrieved %d chunks for repo %s (question='%s...')",
        len(citations), repo_id, question[:60],
    )
    return citations