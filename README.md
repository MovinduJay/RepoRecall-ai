# RepoRecall AI

**A RAG-powered engineering memory system that connects new software bugs to similar issues and verified fixes from a repository’s GitHub history.**

RepoRecall AI helps developers avoid solving the same problem twice. A developer can submit a bug description, stack trace, failing test, or error message, and the system searches historical issues, pull requests, commits, code changes, review discussions, and regression tests to explain how similar problems were resolved before.

> **Project status:** This repository is being built milestone by milestone. The current version provides the backend foundation, PostgreSQL integration, Qdrant connectivity, repository registration, health checks, database migrations, a Docker development environment, and initial tests. GitHub ingestion, hybrid retrieval, LangGraph orchestration, and the web interface are included in the roadmap below.

---

## The problem

Engineering teams often encounter bugs that have already been fixed somewhere in the same codebase. Unfortunately, the useful evidence may be scattered across thousands of GitHub issues, pull requests, commit messages, code diffs, review comments, and tests.

Traditional keyword search works well only when the developer knows the exact terminology used in the old discussion. The same problem may be described using completely different words:

```text
Current bug:
"Duplicate invoices appear after RabbitMQ reconnects"

Historical pull request:
"Prevent message redelivery from repeating billing operations"
```

RepoRecall uses **Retrieval-Augmented Generation**, or **RAG**, to retrieve semantically and technically relevant historical fixes before asking an LLM to explain them.

The generated response is grounded in actual repository evidence instead of relying only on the model’s general knowledge.

---

## What RepoRecall will do

A developer will be able to:

1. Connect a public GitHub repository.
2. Index issues, pull requests, commits, code diffs, review comments, and test changes.
3. Submit a bug report, stack trace, failing test, or code snippet.
4. Retrieve similar historical problems using semantic and keyword search.
5. Receive a ranked explanation of how those problems were fixed.
6. Open the original GitHub issue, pull request, commit, file, or test used as evidence.
7. See a confidence score and receive an honest abstention when reliable evidence is unavailable.

### Example query

```text
The RabbitMQ consumer creates duplicate invoices after the connection is restored.
The same message appears to be processed twice.
```

### Expected RepoRecall response

```text
A similar problem was resolved in PR #184.

Likely cause:
The message was acknowledged before the database transaction completed,
allowing RabbitMQ to redeliver it after a connection failure.

Historical fix:
- Moved acknowledgement after the transaction commit
- Added an idempotency check using the message ID
- Added a redelivery integration test

Evidence:
- PR #184
- Commit 8f21c4a
- src/billing/InvoiceConsumer.java
- InvoiceConsumerIntegrationTest.java
```

---

## Why RAG?

RepoRecall is not intended to invent a fix from scratch. The answer should already exist somewhere in the repository’s engineering history.

RAG is appropriate because it allows the application to:

* Search repository-specific knowledge that a general LLM does not know.
* Find related problems even when their descriptions use different wording.
* Combine exact technical matches with semantic similarity.
* Stay current as new issues, commits, and pull requests are added.
* Ground every explanation in traceable GitHub evidence.
* Reduce hallucinations by refusing to answer when retrieval confidence is low.

---

## Architecture

RepoRecall begins as a **modular monolith with a separate background worker**.

This keeps the system simple to develop and deploy while isolating long-running repository indexing from user-facing API requests.

```text
                         ┌──────────────────────────┐
                         │   Next.js Web Client     │
                         │   Planned milestone      │
                         └────────────┬─────────────┘
                                      │
                                HTTPS / SSE
                                      │
                                      ▼
┌───────────────────────────────────────────────────────────────┐
│                  FastAPI Modular Monolith                     │
│                                                               │
│  Repository API   Investigation API   Evaluation API          │
│         │                  │                  │                │
│         │          LangGraph RAG workflow     │                │
│         │             Planned milestone      │                │
└─────────┼──────────────────┼──────────────────┼────────────────┘
          │                  │                  │
          ▼                  ▼                  ▼
┌─────────────────┐  ┌─────────────────┐  ┌─────────────────────┐
│   PostgreSQL    │  │     Qdrant      │  │ Background Worker   │
│                 │  │                 │  │ Planned milestone   │
│ repositories    │  │ embeddings      │  │                     │
│ indexing jobs   │  │ document chunks │  │ GitHub ingestion    │
│ investigations  │  │ metadata        │  │ code parsing        │
│ feedback        │  │ hybrid search   │  │ embedding           │
└─────────────────┘  └─────────────────┘  └─────────────────────┘
```

### Why not microservices?

The ingestion, retrieval, and investigation domains are still evolving and do not yet require independent deployments.

A modular monolith avoids unnecessary:

* Service-to-service networking
* Distributed tracing
* Duplicated configuration
* Deployment overhead
* Internal API contracts
* Additional infrastructure

The indexing process will run separately because it is long-running and may later need independent scaling.

When real usage justifies it, ingestion, embedding, or retrieval can be extracted into independent services without redesigning the complete system.

---

## Planned RAG pipeline

```text
Developer query, stack trace, or failing test
                    │
                    ▼
            Query understanding
  - Extract errors, symbols, paths, and technologies
  - Construct repository and metadata filters
                    │
                    ▼
             Parallel retrieval
       - BM25 keyword retrieval
       - Dense semantic retrieval
       - Metadata-filtered retrieval
                    │
                    ▼
          Reciprocal Rank Fusion
                    │
                    ▼
         Cross-encoder reranking
                    │
                    ▼
     Retrieval confidence assessment
             ┌──────┴──────┐
             │             │
       Sufficient      Insufficient
             │             │
             │       Rewrite query and
             │         retry once
             │             │
             ▼             ▼
   Evidence-backed answer or safe abstention
```

### Why hybrid retrieval?

Dense retrieval helps find conceptually similar bug descriptions.

Keyword retrieval is more reliable for exact technical signals such as:

* Exception names
* Method and class names
* File paths
* Dependency versions
* Error codes
* Configuration keys

Using both is more appropriate than relying on only one retrieval method.

---

## Technology stack

### Implemented foundation

| Area                 | Technology           | Purpose                                               |
| -------------------- | -------------------- | ----------------------------------------------------- |
| Backend              | Python 3.12, FastAPI | Asynchronous APIs and generated OpenAPI documentation |
| Validation           | Pydantic             | Typed requests, responses, and configuration          |
| Application database | PostgreSQL 17        | Repository records and future application state       |
| ORM and migrations   | SQLAlchemy, Alembic  | Async database access and schema migrations           |
| Vector database      | Qdrant               | Future embeddings, metadata, and similarity search    |
| Containers           | Docker Compose       | Reproducible local development environment            |
| Testing and quality  | Pytest, Ruff         | Automated tests and static code checks                |

### Planned AI and product stack

| Area                   | Technology                  | Purpose                                                           |
| ---------------------- | --------------------------- | ----------------------------------------------------------------- |
| Workflow orchestration | LangGraph                   | Conditional retrieval, retries, confidence checks, and abstention |
| GitHub ingestion       | GitHub REST API, HTTPX      | Fetch repository history                                          |
| Code parsing           | Tree-sitter, unidiff        | Syntax-aware chunking and diff parsing                            |
| Retrieval              | Dense embeddings, BM25, RRF | Semantic and exact technical search                               |
| Reranking              | Cross-encoder               | Improve the precision of retrieved results                        |
| Frontend               | Next.js, TypeScript         | Repository dashboard and investigation interface                  |
| Streaming              | Server-Sent Events          | Stream investigation progress                                     |
| Delivery               | GitHub Actions              | Testing, code checks, and deployment automation                   |

---

## Current capabilities

* [x] FastAPI application foundation
* [x] Versioned `/api/v1` routes
* [x] PostgreSQL integration using asynchronous SQLAlchemy
* [x] Alembic database migrations
* [x] Qdrant connectivity and readiness checking
* [x] Register public GitHub repositories
* [x] List registered repositories
* [x] Duplicate repository protection
* [x] Liveness and dependency-readiness endpoints
* [x] Docker Compose environment
* [x] Initial API and schema tests
* [x] Ruff configuration

---

## API endpoints

| Method | Endpoint               | Purpose                                  |
| ------ | ---------------------- | ---------------------------------------- |
| `GET`  | `/health`              | Confirm that the API process is running  |
| `GET`  | `/ready`               | Check PostgreSQL and Qdrant connectivity |
| `POST` | `/api/v1/repositories` | Register a public GitHub repository      |
| `GET`  | `/api/v1/repositories` | List registered repositories             |
| `GET`  | `/docs`                | Open interactive Swagger documentation   |

---

## Getting started

### Prerequisites

* Docker Desktop
* Git

A local Python installation is not required when running the project through Docker.

### 1. Clone the repository

```bash
git clone https://github.com/YOUR_USERNAME/reporecall-ai.git
cd reporecall-ai
```

### 2. Create the environment file

#### Windows PowerShell

```powershell
Copy-Item .env.example .env
```

#### macOS or Linux

```bash
cp .env.example .env
```

### 3. Start the services

```bash
docker compose up --build
```

Docker Compose starts:

* FastAPI at `http://localhost:8000`
* PostgreSQL at `localhost:5432`
* Qdrant HTTP API at `http://localhost:6333`
* Qdrant dashboard at `http://localhost:6333/dashboard`

### 4. Verify the environment

Open:

* Swagger UI: `http://localhost:8000/docs`
* Liveness check: `http://localhost:8000/health`
* Dependency readiness: `http://localhost:8000/ready`
* Qdrant dashboard: `http://localhost:6333/dashboard`

Expected readiness response:

```json
{
  "postgres": "ok",
  "qdrant": "ok"
}
```

---

## Register a repository

Open Swagger UI and run:

```text
POST /api/v1/repositories
```

Example request:

```json
{
  "github_url": "https://github.com/fastapi/fastapi",
  "default_branch": "master"
}
```

### PowerShell example

```powershell
Invoke-RestMethod `
  -Method Post `
  -Uri "http://localhost:8000/api/v1/repositories" `
  -ContentType "application/json" `
  -Body '{"github_url":"https://github.com/fastapi/fastapi","default_branch":"master"}'
```

List registered repositories:

```powershell
Invoke-RestMethod `
  -Uri "http://localhost:8000/api/v1/repositories"
```

Example response:

```json
[
  {
    "id": "319e6a95-97ab-44ea-b0e1-c77c409d41e7",
    "owner": "fastapi",
    "name": "fastapi",
    "github_url": "https://github.com/fastapi/fastapi",
    "default_branch": "master",
    "indexing_status": "pending",
    "latest_indexed_sha": null,
    "created_at": "2026-08-01T08:30:00Z"
  }
]
```

---

## Run tests and code checks

Run tests inside the API container:

```bash
docker compose exec api pytest
```

Run Ruff:

```bash
docker compose exec api ruff check .
```

---

## Stop the environment

Stop the containers while keeping the database volumes:

```bash
docker compose down
```

Delete the containers and all local PostgreSQL and Qdrant data:

```bash
docker compose down -v
```

---

## Project structure

```text
reporecall-ai/
├── backend/
│   ├── alembic/                 # Database migrations
│   ├── app/
│   │   ├── api/                 # FastAPI routes
│   │   ├── core/                # Settings and configuration
│   │   ├── db/                  # SQLAlchemy base and sessions
│   │   ├── models/              # Database models
│   │   ├── schemas/             # Pydantic schemas
│   │   ├── services/            # Infrastructure integrations
│   │   └── main.py              # FastAPI entry point
│   ├── tests/                   # Automated tests
│   ├── Dockerfile
│   ├── alembic.ini
│   └── pyproject.toml
├── .env.example
├── compose.yaml
└── README.md
```

Planned modules will add:

```text
ingestion/
retrieval/
graph/
generation/
evaluation/
workers/
```

These modules will remain inside the same modular backend codebase.

---

## Roadmap

### Milestone 1: Backend foundation

* [x] FastAPI
* [x] PostgreSQL
* [x] Qdrant
* [x] Docker Compose
* [x] Database migrations
* [x] Health checks
* [x] Repository registration

### Milestone 2: GitHub ingestion

* [ ] Add GitHub token configuration
* [ ] Handle GitHub API rate limits
* [ ] Add indexing-job and raw-document tables
* [ ] Fetch issues, pull requests, comments, and commits
* [ ] Parse unified diffs and changed files
* [ ] Add a separate indexing worker
* [ ] Support incremental synchronization

### Milestone 3: Vector indexing

* [ ] Create source-specific chunking strategies
* [ ] Extract repository, language, file, symbol, issue, and PR metadata
* [ ] Generate dense embeddings
* [ ] Store chunks and metadata in Qdrant
* [ ] Prevent duplicate indexing using content hashes

### Milestone 4: Retrieval and evaluation

* [ ] Implement BM25 retrieval
* [ ] Implement dense semantic retrieval
* [ ] Add metadata filtering
* [ ] Combine rankings using Reciprocal Rank Fusion
* [ ] Add cross-encoder reranking
* [ ] Build a ground-truth dataset from linked issue-fix pairs
* [ ] Measure Recall@K, MRR, and nDCG

### Milestone 5: LangGraph RAG workflow

* [ ] Extract errors, file paths, symbols, and components from queries
* [ ] Retrieve and rerank historical fixes
* [ ] Calculate retrieval confidence
* [ ] Rewrite and retry low-confidence searches once
* [ ] Generate citation-backed answers
* [ ] Validate generated citations
* [ ] Abstain when trustworthy evidence is unavailable

### Milestone 6: Product and deployment

* [ ] Build a Next.js investigation dashboard
* [ ] Stream LangGraph progress using Server-Sent Events
* [ ] Add a retrieval-comparison interface
* [ ] Add an evidence explorer
* [ ] Collect relevance feedback
* [ ] Add retrieval regression tests
* [ ] Add GitHub Actions CI/CD
* [ ] Deploy a public demonstration using free-tier services

---

## Evaluation strategy

RepoRecall will be evaluated using historical GitHub issues linked to the pull requests or commits that resolved them.

```text
Evaluation query:
Issue title + issue description + selected error information

Expected relevant result:
The linked fixing pull request, commit, code change, or regression test
```

### Planned retrieval comparisons

* BM25 only
* Dense retrieval only
* Hybrid retrieval
* Hybrid retrieval with metadata filtering
* Hybrid retrieval with reranking
* Full LangGraph workflow with query rewriting

### Planned metrics

* Recall@5
* Recall@10
* Mean Reciprocal Rank
* nDCG@10
* Linked-fix hit rate
* Citation precision
* Unsupported-claim rate
* Abstention precision
* p50 response latency
* p95 response latency

Results will be published only after running the evaluation. No retrieval improvements will be claimed without measured evidence.

---

## Engineering decisions

### PostgreSQL and Qdrant have different responsibilities

PostgreSQL stores transactional application data such as:

* Repositories
* Indexing jobs
* Investigations
* Search history
* Feedback
* Evaluation runs

Qdrant stores:

* Embedding vectors
* Searchable document chunks
* GitHub metadata
* Semantic-search indexes
* Future sparse-search information

### Repository history is treated as untrusted input

Issue descriptions, review comments, source comments, and commit messages may contain malicious or misleading instructions.

Retrieved repository content will be treated only as evidence, never as system instructions.

Generated citations will be checked against retrieved document identifiers before being returned.

### The system prefers abstention over unsupported answers

When retrieval confidence remains low after a controlled retry, RepoRecall will explain that it could not find reliable historical evidence instead of presenting a guessed solution as fact.

---

## Portfolio objective

RepoRecall is designed to demonstrate practical experience with:

* End-to-end RAG system design
* Python and FastAPI backend development
* LangGraph state and conditional workflows
* Vector databases
* Metadata-aware retrieval
* GitHub API ingestion
* Code and diff parsing
* Retrieval evaluation
* Asynchronous background processing
* PostgreSQL and database migrations
* Docker and CI/CD
* Evidence-backed generation
* Confidence scoring and safe abstention

---

## Status

**Current milestone:** Backend foundation complete
**Next milestone:** GitHub ingestion and asynchronous indexing worker
