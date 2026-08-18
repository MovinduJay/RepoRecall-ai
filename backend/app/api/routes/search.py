from fastapi import APIRouter

from app.retrieval.diff_search import search_diff_hunks
from app.retrieval.hybrid_search import search_hybrid
from app.retrieval.lexical_search import search_lexically
from app.retrieval.vector_store import search_similar
from app.schemas.search import (
    DiffSearchRequest,
    DiffSearchResponse,
    HybridSearchRequest,
    HybridSearchResponse,
    LexicalSearchRequest,
    LexicalSearchResponse,
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


@router.post("/lexical", response_model=LexicalSearchResponse)
async def lexical_search(request: LexicalSearchRequest) -> LexicalSearchResponse:
    results = await search_lexically(
        repository_id=request.repository_id,
        query=request.query,
        limit=request.limit,
    )

    return LexicalSearchResponse(query=request.query, results=results)


@router.post("/hybrid", response_model=HybridSearchResponse)
async def hybrid_search(request: HybridSearchRequest) -> HybridSearchResponse:
    results = await search_hybrid(
        repository_id=request.repository_id,
        query=request.query,
        limit=request.limit,
    )

    return HybridSearchResponse(query=request.query, results=results)


@router.post("/diffs", response_model=DiffSearchResponse)
async def diff_search(request: DiffSearchRequest) -> DiffSearchResponse:
    results = await search_diff_hunks(
        repository_id=request.repository_id,
        query=request.query,
        limit=request.limit,
        minimum_score=request.minimum_score,
    )

    return DiffSearchResponse(query=request.query, results=results)
