import uuid

from app.retrieval.commit_diff_chunking import chunk_commit_file
from app.retrieval.commit_diff_indexer import _create_commit_diff_point_id
from tests.test_commit_diff_chunking import _file_input


def test_commit_diff_point_id_is_deterministic_and_hunk_specific() -> None:
    repository_id = uuid.uuid4()
    chunks = chunk_commit_file(_file_input())

    first_id = _create_commit_diff_point_id(repository_id, chunks[0])

    assert first_id == _create_commit_diff_point_id(repository_id, chunks[0])
    assert first_id != _create_commit_diff_point_id(repository_id, chunks[1])
    assert uuid.UUID(first_id).version == 5
