from __future__ import annotations

from typing import Literal, cast

from app.workflow.state import InvestigationState

DEFAULT_CONFIDENCE_THRESHOLD = 0.05
MAX_RETRIES = 1

ConfidenceDecision = Literal["sufficient", "rewrite", "abstain"]


def assess_confidence(
    state: InvestigationState,
    *,
    threshold: float = DEFAULT_CONFIDENCE_THRESHOLD,
) -> dict[str, float | ConfidenceDecision]:
    """Assess retrieved evidence and permit at most one controlled retry."""

    if not 0 <= threshold <= 1:
        raise ValueError("Confidence threshold must be between 0 and 1.")

    results = state.get("retrieved_results", [])
    confidence = max((result.score for result in results), default=0.0)
    decision: ConfidenceDecision
    if confidence >= threshold:
        decision = "sufficient"
    elif state.get("retry_count", 0) < MAX_RETRIES:
        decision = "rewrite"
    else:
        decision = "abstain"

    return {"confidence": confidence, "decision": decision}


def route_after_confidence(state: InvestigationState) -> ConfidenceDecision:
    """Return the previously assessed branch for graph conditional routing."""

    decision = state.get("decision")
    if decision not in {"sufficient", "rewrite", "abstain"}:
        raise ValueError("Confidence decision is missing or invalid.")
    return cast(ConfidenceDecision, decision)
