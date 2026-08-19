from __future__ import annotations

import re
from typing import Any

from app.workflow.state import InvestigationState

ERROR_PATTERN = re.compile(
    r"\b(?:[A-Za-z_][A-Za-z0-9_.]*)(?:Error|Exception)\b"
)
PATH_PATTERN = re.compile(
    r"(?<![\w.])(?:[A-Za-z]:)?(?:[/\\]?[A-Za-z0-9_.-]+)+"
    r"\.(?:py|pyi|js|jsx|ts|tsx|java|kt|go|rs|rb|php|cs|cpp|c|h|html|css|json|ya?ml)\b"
)


def understand_query(state: InvestigationState) -> dict[str, Any]:
    """Extract exact software signals that can guide later retrieval filters."""

    query = state["query"]
    return {
        "extracted_errors": _unique_matches(ERROR_PATTERN, query),
        "extracted_paths": [
            match.replace("\\", "/") for match in _unique_matches(PATH_PATTERN, query)
        ],
        "metadata_filters": dict(state.get("metadata_filters", {})),
    }


def _unique_matches(pattern: re.Pattern[str], text: str) -> list[str]:
    return list(dict.fromkeys(match.group(0) for match in pattern.finditer(text)))
