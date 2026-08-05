# RepoRecall AI

RepoRecall AI is a RAG-powered engineering assistant that searches a GitHub repository's issues, pull requests, commits, and code history to find similar past bugs and explain how they were fixed using traceable source evidence.

The project is built with **Python, FastAPI, LangGraph, PostgreSQL, and Qdrant**. It uses a modular-monolith architecture with a separate background worker for long-running repository indexing.

## Current milestone

The current version can:

- register public GitHub repositories;
- create asynchronous repository-sync jobs;
- fetch issues, pull requests, and commits through the GitHub REST API;
- normalize and upsert the retrieved records into PostgreSQL;
- track indexing progress and failures;
- list the raw documents collected for a repository.

Vector embeddings, hybrid retrieval, reranking, and the LangGraph investigation workflow come next.

## Run locally

```bash
cp .env.example .env
# Add a GitHub token to .env to receive a higher API rate limit.
docker compose up --build
```

Open Swagger at `http://localhost:8000/docs`.

## Basic flow

1. Register a repository with `POST /api/v1/repositories`.
2. Start ingestion with `POST /api/v1/repositories/{repository_id}/sync`.
3. Check progress with `GET /api/v1/indexing-jobs/{job_id}`.
4. Inspect collected data with `GET /api/v1/repositories/{repository_id}/documents`.

## Architecture

```text
Client
  |
FastAPI API ───────── PostgreSQL
  |                       |
  └── creates job         └── repositories, jobs, raw documents
          |
     Python worker ───── GitHub REST API

Qdrant is already part of the environment and will store embeddings in the next milestone.
```
