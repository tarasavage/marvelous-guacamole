# PDF Summary AI

Take-home assignment for COXIT Full-Stack position: upload large PDFs, extract content via OpenAI vision, generate summaries.

## Requirements & Architecture

**[docs/solutions/architecture-patterns/pdf-summary-ai-requirements-2026-05-24.md](docs/solutions/architecture-patterns/pdf-summary-ai-requirements-2026-05-24.md)**

## Quick Start (Docker)

```bash
cp .env.example .env
docker compose up --build
```

| Service  | URL                         |
|----------|-----------------------------|
| Frontend | http://localhost:5173       |
| Backend  | http://localhost:8000       |
| API docs | http://localhost:8000/docs  |
| Redis    | localhost:6379 (internal)   |

Stack: **FastAPI** + **Celery worker** + **Redis** + **SQLite** + **Vue 3**.

## API (Milestone 2)

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/api/documents` | Upload PDF (`file` field) → `{ job_id, document_id }` |
| `GET` | `/api/jobs/{job_id}` | Poll job status + progress |
| `GET` | `/api/documents` | Last 5 completed summaries |
| `GET` | `/api/documents/{id}` | Full document metadata |

### Example

```bash
# Upload
curl -F "file=@sample.pdf" http://localhost:8000/api/documents

# Poll job (same UUID for job_id and document_id)
curl http://localhost:8000/api/jobs/{id}
```

M2 worker advances jobs to `queued` only — vision summarization comes in Milestone 3.

## Project Structure

```
backend/     FastAPI API + Celery tasks
worker/      Celery consumer (same image as backend)
redis/       Task broker
frontend/    Vue 3 + Naive UI
data/        Uploads + SQLite (gitignored)
```

## Status

**Milestone 2 complete** — upload, validation, SQLite, Celery/Redis job dispatch, read APIs.
