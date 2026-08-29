from __future__ import annotations

from app.retrieval.reranker import RerankedSearchResult
from app.workflow.state import InvestigationState


class InvalidCitationError(ValueError):
    pass


def validate_citations(
    proposed_citations: list[str],
    evidence: list[RerankedSearchResult],
) -> list[str]:
    """Resolve evidence identifiers and allow only retrieved evidence URLs."""

    evidence_urls = {result.html_url for result in evidence}
    evidence_references = {
        f"evidence-{index}": result.html_url for index, result in enumerate(evidence, start=1)
    }
    proposed = [citation.strip() for citation in proposed_citations if citation.strip()]
    invalid_citations = [
        citation
        for citation in proposed
        if citation not in evidence_urls and citation not in evidence_references
    ]
    if invalid_citations:
        raise InvalidCitationError(
            "Generated citations are not present in retrieved evidence: "
            + ", ".join(invalid_citations)
        )
    return list(
        dict.fromkeys(evidence_references.get(citation, citation) for citation in proposed)
    )


def validate_state_citations(state: InvestigationState) -> dict[str, list[str]]:
    return {
        "citations": validate_citations(
            state.get("citations", []),
            state.get("retrieved_results", []),
        )
    }
