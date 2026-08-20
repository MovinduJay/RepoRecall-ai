from __future__ import annotations

from app.workflow.confidence import MAX_RETRIES
from app.workflow.state import InvestigationState

HISTORICAL_FIX_CONTEXT = "historical bug fix pull request root cause regression"


def rewrite_query(state: InvestigationState) -> dict[str, list[str] | int]:
    """Create one deterministic retrieval retry focused on software evidence."""

    retry_count = state.get("retry_count", 0)
    if retry_count >= MAX_RETRIES:
        raise ValueError("Maximum query rewrite attempts reached.")

    rewritten_query = _build_rewritten_query(state)
    rewritten_queries = [*state.get("rewritten_queries", []), rewritten_query]
    return {
        "rewritten_queries": rewritten_queries,
        "retry_count": retry_count + 1,
    }


def _build_rewritten_query(state: InvestigationState) -> str:
    signals = list(
        dict.fromkeys(
            [
                *state.get("extracted_errors", []),
                *state.get("extracted_paths", []),
            ]
        )
    )
    context = " ".join(signals) if signals else HISTORICAL_FIX_CONTEXT
    return f"{context}\n{state['query']}"
