"""
Router: /query

Endpoints:
  POST /query — ask a natural-language question about an indexed repository

Phase 6: retrieval fully implemented.
Phase 7: OpenAI answer generation wired in. Full pipeline now active:
  validate repo → retrieve chunks → generate answer via OpenAI → return response.
"""

import logging

from fastapi import APIRouter, HTTPException, Request, status

from llm.gpt_4o_mini import generate_answer
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
    Retrieve relevant code chunks and generate a grounded answer via OpenAI.

    Steps:
      1. Validate repo exists (404) and is 'ready' (409).
      2. Embed question, retrieve top-K chunks via pgvector.
      3. Send question + chunks to OpenAI API.
      4. Return answer + citations.

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

    # --- Generate answer via OpenAI ---
    try:
        answer = await generate_answer(
            question=payload.question,
            citations=citations,
        )
    except Exception as exc:
        logger.error(
            "OpenAI API call failed for repo %s: %s",
            payload.repo_id, exc,
        )
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Answer generation failed: {exc}",
        )

    if "Please ask questions related to the project." in answer:
        citations = []

    return QueryResponse(answer=answer, citations=citations)