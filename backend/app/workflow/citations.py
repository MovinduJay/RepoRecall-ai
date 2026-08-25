from __future__ import annotations

from app.retrieval.reranker import RerankedSearchResult
from app.workflow.state import InvestigationState


class InvalidCitationError(ValueError):
    pass


def validate_citations(
    proposed_citations: list[str],
    evidence: list[RerankedSearchResult],
) -> list[str]:
    """Allow only exact URLs from the retrieved evidence set."""

    evidence_urls = {result.html_url for result in evidence}
    normalized_citations = list(
        dict.fromkeys(citation.strip() for citation in proposed_citations if citation.strip())
    )
    invalid_citations = [
        citation for citation in normalized_citations if citation not in evidence_urls
    ]
    if invalid_citations:
        raise InvalidCitationError(
            "Generated citations are not present in retrieved evidence: "
            + ", ".join(invalid_citations)
        )
    return normalized_citations


def validate_state_citations(state: InvestigationState) -> dict[str, list[str]]:
    return {
        "citations": validate_citations(
            state.get("citations", []),
            state.get("retrieved_results", []),
        )
    }
