import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from app.evaluation.dataset import load_evaluation_dataset


def test_load_evaluation_dataset_validates_cases_and_canonical_ids(tmp_path: Path) -> None:
    path = _write_dataset(
        tmp_path,
        {
            "version": 1,
            "repository": "acme/billing",
            "cases": [
                {
                    "case_id": "duplicate-message-after-reconnect",
                    "query": "Messages are processed twice after reconnecting.",
                    "relevant_evidence": [
                        {"source_type": "pull_request", "source_id": "184"},
                        {"source_type": "commit", "source_id": "abc123"},
                    ],
                    "notes": "Issue linked both fixes in its timeline.",
                }
            ],
        },
    )

    dataset = load_evaluation_dataset(path)

    assert dataset.repository == "acme/billing"
    assert dataset.cases[0].relevant_ids == {"pull_request:184", "commit:abc123"}


def test_dataset_rejects_duplicate_case_ids(tmp_path: Path) -> None:
    case = {
        "case_id": "same-case",
        "query": "Database timeout",
        "relevant_evidence": [{"source_type": "pull_request", "source_id": "10"}],
    }
    path = _write_dataset(
        tmp_path,
        {"version": 1, "repository": "acme/repo", "cases": [case, case]},
    )

    with pytest.raises(ValidationError, match="case IDs must be unique"):
        load_evaluation_dataset(path)


def test_dataset_rejects_missing_or_duplicate_ground_truth(tmp_path: Path) -> None:
    duplicate = {"source_type": "commit", "source_id": "abc123"}
    path = _write_dataset(
        tmp_path,
        {
            "version": 1,
            "repository": "acme/repo",
            "cases": [
                {
                    "case_id": "case-one",
                    "query": "Timeout",
                    "relevant_evidence": [duplicate, duplicate],
                }
            ],
        },
    )

    with pytest.raises(ValidationError, match="evidence references must be unique"):
        load_evaluation_dataset(path)


def test_dataset_reports_invalid_json_and_missing_file(tmp_path: Path) -> None:
    invalid_path = tmp_path / "invalid.json"
    invalid_path.write_text("not json", encoding="utf-8")

    with pytest.raises(ValueError, match="not valid JSON"):
        load_evaluation_dataset(invalid_path)
    with pytest.raises(ValueError, match="Could not read"):
        load_evaluation_dataset(tmp_path / "missing.json")


def test_curated_fastapi_dataset_is_valid() -> None:
    dataset_path = Path(__file__).parents[1] / "evaluation_data" / "fastapi.json"

    dataset = load_evaluation_dataset(dataset_path)

    assert dataset.repository == "fastapi/fastapi"
    assert len(dataset.cases) == 4
    assert all(case.relevant_ids for case in dataset.cases)


def _write_dataset(tmp_path: Path, content: dict[str, object]) -> Path:
    path = tmp_path / "evaluation.json"
    path.write_text(json.dumps(content), encoding="utf-8")
    return path
