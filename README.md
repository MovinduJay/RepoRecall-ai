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
- index and search engineering history with Qdrant;
- combine semantic and keyword retrieval, rerank results, and diversify sources;
- run a bounded LangGraph investigation with evidence-grounded citations;
- generate answers with OpenAI or a free local Ollama model.

## Run locally

```bash
cp .env.example .env
# Add a GitHub token to .env to receive a higher API rate limit.
docker compose up --build
```

Open Swagger at `http://localhost:8000/docs`.

### Free local answer generation

Install Ollama on the host, then download the default lightweight model:

```bash
ollama pull qwen2.5:3b
```

Configure the Docker API to reach Ollama in `.env`:

```env
OLLAMA_BASE_URL=http://host.docker.internal:11434
OLLAMA_MODEL=qwen2.5:3b
```

No OpenAI key is required. Leave `OPENAI_API_KEY` empty; when both providers are
configured, OpenAI takes precedence.

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

Qdrant stores document embeddings used by semantic and hybrid retrieval.
```
