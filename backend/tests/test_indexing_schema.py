import pytest
from pydantic import ValidationError

from app.schemas.indexing_job import RepositorySyncRequest


def test_sync_limit_is_optional() -> None:
    assert RepositorySyncRequest().max_items_per_source is None


def test_sync_limit_is_bounded() -> None:
    with pytest.raises(ValidationError):
        RepositorySyncRequest(max_items_per_source=501)
