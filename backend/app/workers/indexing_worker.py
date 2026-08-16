from __future__ import annotations

import asyncio
import logging
import uuid
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert

from app.core.config import settings
from app.db.session import dispose_engine, get_session_factory
from app.ingestion.github_client import GitHubApiClient
from app.ingestion.normalizers import (
    RawDocumentInput,
    normalize_commit,
    normalize_issue,
    normalize_issue_comment,
    normalize_pull_request,
)
from app.models.indexing_job import IndexingJob
from app.models.raw_document import RawDocument
from app.models.repository import Repository

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)
logger = logging.getLogger("reporecall.indexing-worker")


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
            issue_comments = await client.list_issue_comments(
                repository.owner, repository.name, job.max_items_per_source
            )
            commits = await client.list_commits(
                repository.owner, repository.name, job.max_items_per_source
            )

            documents = [normalize_issue(item) for item in issues]
            documents.extend(normalize_pull_request(item) for item in pull_requests)
            documents.extend(normalize_issue_comment(item) for item in issue_comments)
            documents.extend(normalize_commit(item) for item in commits)

            await _upsert_documents(repository.id, documents)
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
                "Completed job %s for %s/%s: %s documents",
                job.id,
                repository.owner,
                repository.name,
                len(documents),
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

    statement = insert(RawDocument).values(values)
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
