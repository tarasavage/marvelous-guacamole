# PDF Summary AI

Take-home assignment for COXIT Full-Stack position: upload large PDFs, extract content via OpenAI vision, generate summaries.

## Requirements & Architecture

**[docs/solutions/architecture-patterns/pdf-summary-ai-requirements-2026-05-24.md](docs/solutions/architecture-patterns/pdf-summary-ai-requirements-2026-05-24.md)**

## Quick Start (Docker)

```bash
cp .env.example .env
# Add OPENAI_API_KEY to .env — required for end-to-end summarization
docker compose up --build
```

| Service  | URL                         |
|----------|-----------------------------|
| Frontend | http://localhost:5173       |
| Backend  | http://localhost:8000       |
| API docs | http://localhost:8000/docs  |

Stack: **FastAPI** + **Celery worker** + **Redis** + **SQLite** + **Vue 3** + **OpenAI gpt-4o-mini**.

## API

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/api/documents` | Upload PDF (`file` field) → `{ job_id, document_id }` |
| `GET` | `/api/jobs/{job_id}` | Poll job status + progress |
| `GET` | `/api/documents` | Last 5 completed summaries |
| `GET` | `/api/documents/{id}` | Full document metadata |

### Job status flow

`pending` → `queued` → `extracting` (batch N/M) → `summarizing` → `completed` | `failed`

### Example

```bash
# Upload
curl -F "file=@sample.pdf" http://localhost:8000/api/documents

# Poll job (same UUID for job_id and document_id)
curl http://localhost:8000/api/jobs/{id}

# Fetch summary when completed
curl http://localhost:8000/api/documents/{id}
```

## Limitations

- Max **50 MB**, **100 pages** per PDF
- **Single worker** — one PDF processes at a time; others queue
- Dense documents may hit OpenAI context limits (clear error, no map-reduce)
- Worker crash during extraction **restarts from batch 1** (extraction not checkpointed)
- `OPENAI_API_KEY` required in `.env` for backend and worker services

## Project Structure

```
backend/     FastAPI API + Celery tasks
worker/      Celery consumer (same image as backend)
redis/       Task broker
frontend/    Vue 3 + Naive UI
data/        Uploads + SQLite (gitignored)
```

## Status

**Milestone 5 complete** — upload UI, job polling with staged progress, history with inline summary expand. Submission polish (Loom, expanded README) is optional follow-up.
