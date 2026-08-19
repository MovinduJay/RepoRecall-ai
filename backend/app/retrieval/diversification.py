from __future__ import annotations

from typing import Protocol


class SourceResult(Protocol):
    raw_document_id: str


def diversify_by_source[ResultT: SourceResult](
    results: list[ResultT],
    *,
    limit: int,
) -> list[ResultT]:
    """Keep the highest-ranked chunk for each source document."""

    if limit < 1:
        raise ValueError("Limit must be at least 1.")

    diversified: list[ResultT] = []
    seen_document_ids: set[str] = set()
    for result in results:
        if result.raw_document_id in seen_document_ids:
            continue
        seen_document_ids.add(result.raw_document_id)
        diversified.append(result)
        if len(diversified) == limit:
            break
    return diversified
