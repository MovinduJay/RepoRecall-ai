from fastapi import APIRouter

from app.retrieval.diff_search import search_diff_hunks
from app.retrieval.vector_store import search_similar
from app.schemas.search import (
    DiffSearchRequest,
    DiffSearchResponse,
    SemanticSearchRequest,
    SemanticSearchResponse,
)

router = APIRouter(prefix="/search", tags=["search"])


@router.post("/semantic", response_model=SemanticSearchResponse)
async def semantic_search(request: SemanticSearchRequest) -> SemanticSearchResponse:
    results = await search_similar(
        repository_id=request.repository_id,
        query=request.query,
        limit=request.limit,
        minimum_score=request.minimum_score,
    )

    return SemanticSearchResponse(query=request.query, results=results)


@router.post("/diffs", response_model=DiffSearchResponse)
async def diff_search(request: DiffSearchRequest) -> DiffSearchResponse:
    results = await search_diff_hunks(
        repository_id=request.repository_id,
        query=request.query,
        limit=request.limit,
        minimum_score=request.minimum_score,
    )

    return DiffSearchResponse(query=request.query, results=results)
