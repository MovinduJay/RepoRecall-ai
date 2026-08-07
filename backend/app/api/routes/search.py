from fastapi import APIRouter

from app.retrieval.vector_store import search_similar
from app.schemas.search import SemanticSearchRequest, SemanticSearchResponse

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
