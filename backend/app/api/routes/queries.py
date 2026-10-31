import logging
from fastapi import APIRouter, Depends, HTTPException, status

from app.api.dependencies import get_query_service
from app.schemas.query import QueryRequest
from app.schemas.response import GenerationResponse
from app.services.query_service import QueryService
from app.shared.exceptions import RetrievalError

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/queries", tags=["queries"])


@router.post("", response_model=GenerationResponse)
async def submit_query(
    request: QueryRequest,
    query_service: QueryService = Depends(get_query_service),
) -> GenerationResponse:
    """Submit a question about a repository and receive a structured, citation-grounded response."""
    try:
        return await query_service.query(
            repo_id=request.repository_id,
            raw_query=request.query,
            options=request.options,
        )
    except RetrievalError as exc:
        msg = str(exc)
        if "not found" in msg.lower():
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=msg) from exc
        if "still indexing" in msg.lower():
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=msg) from exc
        if "indexing failed" in msg.lower():
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=msg) from exc
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=msg) from exc
    except Exception as exc:
        logger.exception("Unexpected error processing query for repo %s: %s", request.repository_id, exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while answering your question. Please try again.",
        ) from exc
