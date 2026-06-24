from uuid import UUID
from fastapi import APIRouter, BackgroundTasks, HTTPException, status
from models.schemas import IndexingStatus, RepoCreate, RepoResponse

router = APIRouter(prefix="/repos", tags=["repos"])

@router.post("", response_model=RepoResponse, status_code=status.HTTP_202_ACCEPTED)
async def submit_repo(payload: RepoCreate, background_tasks: BackgroundTasks) -> RepoResponse:
    # TODO (Phase 2): check if repo exists, insert into DB, enqueue background task
    raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED,
                        detail="Ingestion not yet implemented â€” coming in Phase 2.")

@router.get("/{repo_id}", response_model=IndexingStatus)
async def get_repo_status(repo_id: UUID) -> IndexingStatus:
    # TODO (Phase 2): fetch repo record from DB and return real status
    raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED,
                        detail="Status polling not yet implemented â€” coming in Phase 2.")
