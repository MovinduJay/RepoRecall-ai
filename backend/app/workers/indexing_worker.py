from __future__ import annotations

import asyncio
import logging
import uuid
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert

from app.core.config import settings
from app.db.session import dispose_engine, get_session_factory
from app.ingestion.github_client import GitHubApiClient, GitHubApiError
from app.ingestion.normalizers import (
    CommitFileInput,
    PullRequestFileInput,
    RawDocumentInput,
    normalize_commit,
    normalize_commit_file,
    normalize_issue,
    normalize_issue_comment,
    normalize_pull_request,
    normalize_pull_request_file,
    normalize_pull_request_review_comment,
)
from app.models.commit_file import CommitFile
from app.models.indexing_job import IndexingJob
from app.models.pull_request_file import PullRequestFile
from app.models.raw_document import RawDocument
from app.models.repository import Repository
from app.retrieval.commit_diff_indexer import index_repository_commit_diffs
from app.retrieval.diff_indexer import index_repository_diffs
from app.retrieval.indexer import index_repository_documents

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)
logger = logging.getLogger("reporecall.indexing-worker")

PULL_REQUESTS_WITH_FILES_LIMIT = 10
FILES_PER_PULL_REQUEST_LIMIT = 100
COMMITS_WITH_FILES_LIMIT = 10
FILES_PER_COMMIT_LIMIT = 100
DATABASE_WRITE_BATCH_SIZE = 500


async def claim_next_job() -> uuid.UUID | None:
    async with get_session_factory()() as session, session.begin():
        result = await session.execute(
            select(IndexingJob)
            .where(IndexingJob.status == "pending")
            .order_by(IndexingJob.created_at.asc())
            .with_for_update(skip_locked=True)
            .limit(1)
        )
        job = result.scalar_one_or_none()
        if job is None:
            return None

        job.status = "running"
        job.started_at = datetime.now(UTC)
        job.error_message = None
        return job.id


async def process_job(job_id: uuid.UUID) -> None:
    async with get_session_factory()() as session:
        job = await session.get(IndexingJob, job_id)
        if job is None:
            logger.warning("Indexing job %s disappeared before processing", job_id)
            return

        repository = await session.get(Repository, job.repository_id)
        if repository is None:
            await _mark_failed(job_id, "Repository no longer exists")
            return

        client = GitHubApiClient()
        try:
            repository_data = await client.get_repository(repository.owner, repository.name)
            issues = await client.list_issues(
                repository.owner, repository.name, job.max_items_per_source
            )
            pull_requests = await client.list_pull_requests(
                repository.owner, repository.name, job.max_items_per_source
            )
            pull_request_files = await _fetch_pull_request_files(
                client=client,
                owner=repository.owner,
                name=repository.name,
                pull_requests=pull_requests,
            )
            issue_comments = await client.list_issue_comments(
                repository.owner, repository.name, job.max_items_per_source
            )
            review_comments = await client.list_pull_request_review_comments(
                repository.owner, repository.name, job.max_items_per_source
            )
            commits = await client.list_commits(
                repository.owner, repository.name, job.max_items_per_source
            )
            commit_files = await _fetch_commit_files(
                client=client,
                owner=repository.owner,
                name=repository.name,
                commits=commits,
            )

            documents = [normalize_issue(item) for item in issues]
            documents.extend(normalize_pull_request(item) for item in pull_requests)
            documents.extend(normalize_issue_comment(item) for item in issue_comments)
            documents.extend(
                normalize_pull_request_review_comment(item) for item in review_comments
            )
            documents.extend(normalize_commit(item) for item in commits)

            await _upsert_documents(repository.id, documents)
            await _upsert_pull_request_files(repository.id, pull_request_files)
            await _upsert_commit_files(repository.id, commit_files)
            await _index_repository_content(repository.id)
            latest_sha = commits[0].get("sha") if commits else repository.latest_indexed_sha
            await _mark_completed(
                job_id=job.id,
                repository_id=repository.id,
                issues_count=len(issues),
                pull_requests_count=len(pull_requests),
                commits_count=len(commits),
                documents_count=len(documents),
                default_branch=repository_data.get("default_branch") or repository.default_branch,
                latest_sha=latest_sha,
            )
            logger.info(
                "Completed job %s for %s/%s: %s documents, %s pull request files, "
                "and %s commit files",
                job.id,
                repository.owner,
                repository.name,
                len(documents),
                len(pull_request_files),
                len(commit_files),
            )
        except Exception as exc:
            logger.exception("Indexing job %s failed", job.id)
            await _mark_failed(job.id, str(exc)[:2000])
        finally:
            await client.close()


async def _upsert_documents(
    repository_id: uuid.UUID,
    documents: list[RawDocumentInput],
) -> None:
    if not documents:
        return

    values = [
        {
            "id": uuid.uuid4(),
            "repository_id": repository_id,
            "source_type": document.source_type,
            "source_id": document.source_id,
            "source_number": document.source_number,
            "title": document.title,
            "body": document.body,
            "html_url": document.html_url,
            "author": document.author,
            "state": document.state,
            "document_metadata": document.document_metadata,
            "content_hash": document.content_hash,
            "github_created_at": document.github_created_at,
            "github_updated_at": document.github_updated_at,
        }
        for document in documents
    ]

    async with get_session_factory()() as session, session.begin():
        for start in range(0, len(values), DATABASE_WRITE_BATCH_SIZE):
            batch = values[start : start + DATABASE_WRITE_BATCH_SIZE]
            statement = insert(RawDocument).values(batch)
            statement = statement.on_conflict_do_update(
                constraint="uq_raw_document_repository_source",
                set_={
                    "source_number": statement.excluded.source_number,
                    "title": statement.excluded.title,
                    "body": statement.excluded.body,
                    "html_url": statement.excluded.html_url,
                    "author": statement.excluded.author,
                    "state": statement.excluded.state,
                    "document_metadata": statement.excluded.document_metadata,
                    "content_hash": statement.excluded.content_hash,
                    "github_created_at": statement.excluded.github_created_at,
                    "github_updated_at": statement.excluded.github_updated_at,
                    "ingested_at": datetime.now(UTC),
                },
            )
            await session.execute(statement)


async def _fetch_pull_request_files(
    *,
    client: GitHubApiClient,
    owner: str,
    name: str,
    pull_requests: list[dict],
) -> list[PullRequestFileInput]:
    normalized_files: list[PullRequestFileInput] = []

    for pull_request in pull_requests[:PULL_REQUESTS_WITH_FILES_LIMIT]:
        pull_request_number = pull_request.get("number")
        if not isinstance(pull_request_number, int):
            continue

        try:
            file_items = await client.list_pull_request_files(
                owner=owner,
                name=name,
                pull_request_number=pull_request_number,
                max_items=FILES_PER_PULL_REQUEST_LIMIT,
            )
        except GitHubApiError as exc:
            if exc.status_code != 422:
                raise
            logger.warning(
                "Skipping unavailable diff for %s/%s pull request #%s: %s",
                owner,
                name,
                pull_request_number,
                exc,
            )
            continue
        normalized_files.extend(
            normalize_pull_request_file(pull_request_number, item) for item in file_items
        )

    return normalized_files


async def _index_repository_content(repository_id: uuid.UUID) -> None:
    """Populate every Qdrant collection before an indexing job completes."""

    async with get_session_factory()() as session:
        document_result = await index_repository_documents(session, repository_id)
        diff_result = await index_repository_diffs(session, repository_id)
        commit_diff_result = await index_repository_commit_diffs(session, repository_id)

    logger.info(
        "Indexed repository %s in Qdrant: %s document chunks, %s PR diff chunks, "
        "and %s commit diff chunks",
        repository_id,
        document_result["chunks_indexed"],
        diff_result["chunks_indexed"],
        commit_diff_result["chunks_indexed"],
    )


async def _upsert_pull_request_files(
    repository_id: uuid.UUID,
    files: list[PullRequestFileInput],
) -> None:
    if not files:
        return

    values = [
        {
            "id": uuid.uuid4(),
            "repository_id": repository_id,
            "pull_request_number": file.pull_request_number,
            "file_path": file.file_path,
            "previous_file_path": file.previous_file_path,
            "status": file.status,
            "sha": file.sha,
            "additions": file.additions,
            "deletions": file.deletions,
            "changes": file.changes,
            "patch": file.patch,
            "blob_url": file.blob_url,
            "raw_url": file.raw_url,
            "contents_url": file.contents_url,
            "content_hash": file.content_hash,
        }
        for file in files
    ]

    statement = insert(PullRequestFile).values(values)
    statement = statement.on_conflict_do_update(
        constraint="uq_pull_request_file_repository_pr_path",
        set_={
            "previous_file_path": statement.excluded.previous_file_path,
            "status": statement.excluded.status,
            "sha": statement.excluded.sha,
            "additions": statement.excluded.additions,
            "deletions": statement.excluded.deletions,
            "changes": statement.excluded.changes,
            "patch": statement.excluded.patch,
            "blob_url": statement.excluded.blob_url,
            "raw_url": statement.excluded.raw_url,
            "contents_url": statement.excluded.contents_url,
            "content_hash": statement.excluded.content_hash,
            "ingested_at": datetime.now(UTC),
        },
    )

    async with get_session_factory()() as session, session.begin():
        await session.execute(statement)


async def _fetch_commit_files(
    *,
    client: GitHubApiClient,
    owner: str,
    name: str,
    commits: list[dict],
) -> list[CommitFileInput]:
    normalized_files: list[CommitFileInput] = []

    for commit in commits[:COMMITS_WITH_FILES_LIMIT]:
        commit_sha = commit.get("sha")
        if not isinstance(commit_sha, str) or not commit_sha:
            continue

        file_items = await client.list_commit_files(
            owner=owner,
            name=name,
            commit_sha=commit_sha,
            max_items=FILES_PER_COMMIT_LIMIT,
        )
        normalized_files.extend(normalize_commit_file(commit_sha, item) for item in file_items)

    return normalized_files


async def _upsert_commit_files(
    repository_id: uuid.UUID,
    files: list[CommitFileInput],
) -> None:
    if not files:
        return

    values = [
        {
            "id": uuid.uuid4(),
            "repository_id": repository_id,
            "commit_sha": file.commit_sha,
            "file_path": file.file_path,
            "file_sha": file.file_sha,
            "previous_file_path": file.previous_file_path,
            "status": file.status,
            "additions": file.additions,
            "deletions": file.deletions,
            "changes": file.changes,
            "patch": file.patch,
            "blob_url": file.blob_url,
            "raw_url": file.raw_url,
            "contents_url": file.contents_url,
            "content_hash": file.content_hash,
        }
        for file in files
    ]

    statement = insert(CommitFile).values(values)
    statement = statement.on_conflict_do_update(
        constraint="uq_commit_file_repository_commit_path",
        set_={
            "file_sha": statement.excluded.file_sha,
            "previous_file_path": statement.excluded.previous_file_path,
            "status": statement.excluded.status,
            "additions": statement.excluded.additions,
            "deletions": statement.excluded.deletions,
            "changes": statement.excluded.changes,
            "patch": statement.excluded.patch,
            "blob_url": statement.excluded.blob_url,
            "raw_url": statement.excluded.raw_url,
            "contents_url": statement.excluded.contents_url,
            "content_hash": statement.excluded.content_hash,
            "ingested_at": datetime.now(UTC),
        },
    )

    async with get_session_factory()() as session, session.begin():
        await session.execute(statement)


async def _mark_completed(
    *,
    job_id: uuid.UUID,
    repository_id: uuid.UUID,
    issues_count: int,
    pull_requests_count: int,
    commits_count: int,
    documents_count: int,
    default_branch: str,
    latest_sha: str | None,
) -> None:
    async with get_session_factory()() as session, session.begin():
        job = await session.get(IndexingJob, job_id)
        repository = await session.get(Repository, repository_id)
        if job is None or repository is None:
            return

        job.status = "completed"
        job.issues_processed = issues_count
        job.pull_requests_processed = pull_requests_count
        job.commits_processed = commits_count
        job.documents_upserted = documents_count
        job.completed_at = datetime.now(UTC)

        repository.default_branch = default_branch
        repository.latest_indexed_sha = latest_sha
        repository.indexing_status = "completed"


async def _mark_failed(job_id: uuid.UUID, error_message: str) -> None:
    async with get_session_factory()() as session, session.begin():
        job = await session.get(IndexingJob, job_id)
        if job is None:
            return
        repository = await session.get(Repository, job.repository_id)

        job.status = "failed"
        job.error_message = error_message
        job.completed_at = datetime.now(UTC)
        if repository is not None:
            repository.indexing_status = "failed"


async def run_worker() -> None:
    logger.info("RepoRecall indexing worker started")
    try:
        while True:
            job_id = await claim_next_job()
            if job_id is None:
                await asyncio.sleep(settings.worker_poll_interval_seconds)
                continue
            await process_job(job_id)
    finally:
        await dispose_engine()


def main() -> None:
    try:
        asyncio.run(run_worker())
    except KeyboardInterrupt:
        logger.info("RepoRecall indexing worker stopped")


if __name__ == "__main__":
    main()
