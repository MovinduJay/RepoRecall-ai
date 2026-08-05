import pytest
from pydantic import ValidationError

from app.schemas.repository import RepositoryCreate


def test_extracts_owner_and_repository_name() -> None:
    payload = RepositoryCreate(github_url="https://github.com/fastapi/fastapi")
    assert payload.owner_and_name() == ("fastapi", "fastapi")


def test_accepts_git_suffix() -> None:
    payload = RepositoryCreate(github_url="https://github.com/qdrant/qdrant.git")
    assert payload.github_url == "https://github.com/qdrant/qdrant"


def test_rejects_non_github_url() -> None:
    with pytest.raises(ValidationError):
        RepositoryCreate(github_url="https://example.com/owner/repository")
