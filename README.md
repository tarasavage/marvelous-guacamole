# PDF Summary AI

COXIT Full-Stack take-home: upload PDFs (up to 50 MB / 100 pages), extract content with OpenAI vision (`gpt-4o-mini`), and display TL;DR + bullet summaries with recent history.

Full requirements and architecture decisions: [docs/solutions/architecture-patterns/pdf-summary-ai-requirements-2026-05-24.md](docs/solutions/architecture-patterns/pdf-summary-ai-requirements-2026-05-24.md)

## Architecture

```
Browser (Vue 3)  ──REST/poll──►  FastAPI API  ──enqueue──►  Redis
                                      │                         │
                                      ▼                         ▼
                                 SQLite + PDFs            Celery worker
                                      │                   (vision → summary)
                                      └──────────────────► OpenAI
```

1. User uploads a PDF in the Vue UI (or via API).
2. FastAPI validates, stores the file, creates a job in SQLite, and dispatches a Celery task.
3. A single Celery worker rasterizes pages (PyMuPDF), runs batched vision extraction, then one summary call.
4. The frontend polls job status every ~2s; completed summaries appear in a history panel (last 5).

**Stack:** FastAPI · Celery · Redis · SQLite · Vue 3 · Vite · Naive UI · OpenAI `gpt-4o-mini`

## Quick Start

```bash
cp .env.example .env
# Edit .env — set OPENAI_API_KEY (see below)
docker compose up --build
```

| URL | Purpose |
|-----|---------|
| http://localhost:5173 | Web UI (primary demo) |
| http://localhost:8000/docs | OpenAPI / Swagger |
| http://localhost:8000 | REST API |

## OpenAI API Key

1. Create a key at [platform.openai.com/api-keys](https://platform.openai.com/api-keys).
2. Add to `.env`:
   ```
   OPENAI_API_KEY=sk-...
   ```
3. Restart Compose so **backend** and **worker** pick it up:
   ```bash
   docker compose up --build
   ```

Both services read the same `.env`. Without a key, uploads succeed but jobs fail with a clear error.

## Docker Services

| Service | Port | Role |
|---------|------|------|
| `frontend` | 5173 | Vue dev server (Vite hot reload) |
| `backend` | 8000 | FastAPI API + SQLite |
| `worker` | — | Celery consumer (`--concurrency=1`) |
| `redis` | — | Celery broker (internal) |

**Volumes:**

- `./data` → `/app/data` on backend/worker (SQLite + uploaded PDFs)
- `./backend/app` → hot reload for Python
- `./frontend` → hot reload for Vue

**Environment** (see `.env.example`):

| Variable | Purpose |
|----------|---------|
| `OPENAI_API_KEY` | OpenAI auth (backend + worker) |
| `DATA_DIR` | Upload + DB path inside containers |
| `REDIS_URL` | Celery broker |
| `VITE_API_URL` | API base URL for browser |

## API

Interactive docs: **http://localhost:8000/docs**

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/api/documents` | Upload PDF (`file` field) → `{ job_id, document_id }` |
| `GET` | `/api/jobs/{job_id}` | Poll status, stage, progress, error |
| `GET` | `/api/documents` | Last 5 completed summaries |
| `GET` | `/api/documents/{id}` | Full metadata + summary |

### Job status flow

`pending` → `queued` → `extracting` (batch N/M) → `summarizing` → `completed` | `failed`

### curl example

```bash
curl -F "file=@sample.pdf" http://localhost:8000/api/documents
curl http://localhost:8000/api/jobs/{id}
curl http://localhost:8000/api/documents/{id}
```

## Demo / Loom

Recording checklist: [docs/demo/loom-script.md](docs/demo/loom-script.md)

**Loom link:** _(add your recording URL here before submission)_

## Limitations

- Max **50 MB**, **100 pages** per PDF
- **Single worker** — one PDF processes at a time; others queue
- Dense documents may hit OpenAI context limits (clear error, no map-reduce)
- Worker crash during extraction **restarts from batch 1** (extraction not checkpointed)
- No auth, delete, PDF re-download, or automated tests (by design for take-home scope)

## Project Structure

```
backend/     FastAPI API, Celery tasks, OpenAI/PyMuPDF services
frontend/    Vue 3 + Naive UI
docker-compose.yml
data/        Uploads + SQLite (gitignored, created at runtime)
docs/        Requirements, plans, demo script
```
