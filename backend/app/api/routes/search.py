from fastapi import APIRouter

from app.retrieval.diff_search import search_diff_hunks
from app.retrieval.hybrid_search import search_hybrid
from app.retrieval.lexical_search import search_lexically
from app.retrieval.reranked_search import search_reranked
from app.retrieval.vector_store import search_similar
from app.schemas.search import (
    DiffSearchRequest,
    DiffSearchResponse,
    HybridSearchRequest,
    HybridSearchResponse,
    InvestigationRequest,
    InvestigationResponse,
    LexicalSearchRequest,
    LexicalSearchResponse,
    RerankedSearchRequest,
    RerankedSearchResponse,
    SemanticSearchRequest,
    SemanticSearchResponse,
)
from app.workflow.service import run_investigation

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


@router.post("/reranked", response_model=RerankedSearchResponse)
async def reranked_search(request: RerankedSearchRequest) -> RerankedSearchResponse:
    results = await search_reranked(
        repository_id=request.repository_id,
        query=request.query,
        limit=request.limit,
    )

    return RerankedSearchResponse(query=request.query, results=results)


@router.post("/investigate", response_model=InvestigationResponse)
async def investigate(request: InvestigationRequest) -> InvestigationResponse:
    state = await run_investigation(
        repository_id=request.repository_id,
        query=request.query,
    )
    return InvestigationResponse(
        query=state["query"],
        decision=state["decision"],
        confidence=state["confidence"],
        retry_count=state["retry_count"],
        extracted_errors=state["extracted_errors"],
        extracted_paths=state["extracted_paths"],
        rewritten_queries=state["rewritten_queries"],
        evidence=state["retrieved_results"],
        answer=state.get("answer"),
        citations=state["citations"],
        generation_error=state.get("generation_error"),
    )


@router.post("/diffs", response_model=DiffSearchResponse)
async def diff_search(request: DiffSearchRequest) -> DiffSearchResponse:
    results = await search_diff_hunks(
        repository_id=request.repository_id,
        query=request.query,
        limit=request.limit,
        minimum_score=request.minimum_score,
    )

    return DiffSearchResponse(query=request.query, results=results)
