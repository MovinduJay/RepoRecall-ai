from __future__ import annotations

from typing import Any

from langgraph.graph import END, START, StateGraph

from app.generation.provider import AnswerProvider
from app.workflow.answer_generation import generate_answer
from app.workflow.confidence import assess_confidence, route_after_confidence
from app.workflow.query_rewriting import rewrite_query
from app.workflow.query_understanding import understand_query
from app.workflow.retrieval import retrieve_candidates
from app.workflow.state import InvestigationState

ABSTENTION_MESSAGE = (
    "RepoRecall could not find sufficiently reliable repository evidence for this query."
)


def abstain(_: InvestigationState) -> dict[str, Any]:
    return {"answer": ABSTENTION_MESSAGE, "citations": []}


def build_investigation_graph(
    answer_provider: AnswerProvider | None = None,
) -> Any:
    """Compile the bounded retrieval, retry, and abstention workflow."""

    builder = StateGraph(InvestigationState)
    builder.add_node("understand_query", understand_query)
    builder.add_node("retrieve_candidates", retrieve_candidates)
    builder.add_node("assess_confidence", assess_confidence)
    builder.add_node("rewrite_query", rewrite_query)
    builder.add_node("abstain", abstain)
    if answer_provider is not None:

        async def generate_grounded_answer(
            state: InvestigationState,
        ) -> dict[str, str | list[str]]:
            return await generate_answer(state, answer_provider)

        builder.add_node("generate_answer", generate_grounded_answer)

    builder.add_edge(START, "understand_query")
    builder.add_edge("understand_query", "retrieve_candidates")
    builder.add_edge("retrieve_candidates", "assess_confidence")
    sufficient_destination = "generate_answer" if answer_provider is not None else END
    builder.add_conditional_edges(
        "assess_confidence",
        route_after_confidence,
        {
            "sufficient": sufficient_destination,
            "rewrite": "rewrite_query",
            "abstain": "abstain",
        },
    )
    builder.add_edge("rewrite_query", "retrieve_candidates")
    builder.add_edge("abstain", END)
    if answer_provider is not None:
        builder.add_edge("generate_answer", END)
    return builder.compile()
