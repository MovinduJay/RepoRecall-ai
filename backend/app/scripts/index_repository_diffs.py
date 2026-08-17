from __future__ import annotations

import argparse
import asyncio
import uuid

from app.db.session import get_session_factory
from app.retrieval.diff_indexer import index_repository_diffs


async def run(repository_id: uuid.UUID) -> None:
    session_factory = get_session_factory()
    async with session_factory() as session:
        result = await index_repository_diffs(session=session, repository_id=repository_id)

    print("Diff indexing completed")
    print(f"Files loaded: {result['files_loaded']}")
    print(f"Diff chunks indexed: {result['chunks_indexed']}")
    print(f"Stale diff chunks deleted: {result['chunks_deleted']}")


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Index one repository's PR diffs into Qdrant.")
    parser.add_argument("repository_id", help="UUID of the repository stored in PostgreSQL.")
    return parser.parse_args()


if __name__ == "__main__":
    arguments = parse_arguments()
    asyncio.run(run(repository_id=uuid.UUID(arguments.repository_id)))
