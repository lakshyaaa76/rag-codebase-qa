from fastapi import APIRouter, HTTPException, status
from models.schemas import QueryRequest, QueryResponse

router = APIRouter(prefix="/query", tags=["query"])

@router.post("", response_model=QueryResponse)
async def query_repo(payload: QueryRequest) -> QueryResponse:
    # TODO (Phase 6): embed question, similarity search
    # TODO (Phase 7): send retrieved chunks + question to Grok, return answer
    raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED,
                        detail="Query not yet implemented â€” coming in Phase 6.")
