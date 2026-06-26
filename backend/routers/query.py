"""
Router: /query

Endpoints:
  POST /query — ask a natural-language question about an indexed repository

Phase 6: retrieval fully implemented.
  - Validates repo exists and is in 'ready' status.
  - Embeds the question and retrieves top-K chunks via pgvector.
  - Returns citations with a placeholder answer string.

Phase 7 will replace the placeholder answer with a real Grok-generated response.
"""

import logging
from uuid import UUID

from fastapi import APIRouter, HTTPException, Request, status

from models.schemas import QueryRequest, QueryResponse
from services import repo_store
from services.retriever import retrieve_chunks

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/query", tags=["query"])


@router.post(
    "",
    response_model=QueryResponse,
    summary="Ask a question about an indexed repository",
)
async def query_repo(payload: QueryRequest, request: Request) -> QueryResponse:
    """
    Retrieve relevant code chunks for a question and return them as citations.

    Phase 6 behaviour:
      - 404 if repo_id is not found.
      - 409 if the repo is not yet in 'ready' status.
      - Embeds the question, runs similarity search, returns citations.
      - answer field is a placeholder — real answer generation added in Phase 7.

    Request body:
      - repo_id:   UUID of a 'ready' indexed repository
      - question:  natural-language question about the codebase
      - top_k:     number of chunks to retrieve (default 5, max 20)
    """
    # --- Validate repo exists and is ready ---
    repo_row = repo_store.get_repo_by_id(payload.repo_id)
    if repo_row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Repository {payload.repo_id} not found.",
        )

    if repo_row["status"] != "ready":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                f"Repository is not ready for queries. "
                f"Current status: '{repo_row['status']}'. "
                "Wait for indexing to complete before querying."
            ),
        )

    # --- Retrieve relevant chunks ---
    model = request.app.state.embedding_model
    citations = retrieve_chunks(
        model=model,
        repo_id=payload.repo_id,
        question=payload.question,
        top_k=payload.top_k,
    )

    if not citations:
        logger.info(
            "No chunks retrieved for repo %s — query: '%s...'",
            payload.repo_id, payload.question[:60],
        )

    # --- Return response (answer is placeholder until Phase 7) ---
    # TODO (Phase 7): replace placeholder with Grok-generated answer
    placeholder_answer = (
        "Answer generation is not yet implemented. "
        "See the citations below for relevant code snippets."
    )

    return QueryResponse(answer=placeholder_answer, citations=citations)