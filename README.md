# PDF Summary AI

Take-home assignment for COXIT Full-Stack position: upload large PDFs, extract content via OpenAI vision, generate summaries, view processing history.

## Requirements & Architecture

All scope and architecture decisions are documented in:

**[docs/solutions/architecture-patterns/pdf-summary-ai-requirements-2026-05-24.md](docs/solutions/architecture-patterns/pdf-summary-ai-requirements-2026-05-24.md)**

## Quick Start (Docker)

**Prerequisites:** Docker Desktop (or Docker Engine + Compose v2)

```bash
cp .env.example .env
# Optional for scaffold: add OPENAI_API_KEY to .env (required for summarization later)

docker compose up --build
```

| Service  | URL                         |
|----------|-----------------------------|
| Frontend | http://localhost:5173       |
| Backend  | http://localhost:8000       |
| API docs | http://localhost:8000/docs  |

The frontend shows a **Backend connected** badge when it can reach the API. Upload and summarization are not implemented yet.

## Project Structure

```
backend/     FastAPI app (Python 3.12)
frontend/    Vue 3 + Vite + Naive UI
data/        Runtime uploads + SQLite (gitignored)
```

## Status

**Scaffold complete** — Docker Compose, backend stub, frontend shell. PDF pipeline next.
