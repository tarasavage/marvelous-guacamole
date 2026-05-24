---
title: "PDF Summary AI — Project Requirements & Architecture Decisions"
date: 2026-05-24
category: architecture-patterns
module: pdf-summary-ai
problem_type: architecture_pattern
component: documentation
severity: high
applies_when:
  - "Implementing the COXIT PDF Summary AI take-home assignment"
  - "Making scope or architecture decisions for this project"
  - "Onboarding to the codebase before writing code"
tags:
  - pdf-summary-ai
  - requirements
  - fastapi
  - vue
  - openai
  - vision-extraction
  - docker
  - take-home
---

# PDF Summary AI — Project Requirements & Architecture Decisions

## Context

This document captures all requirements and architecture decisions gathered during an interactive requirements session for the **COXIT PDF Summary AI take-home assignment** (Full-Stack position). The assignment asks for a web app that accepts large PDFs (up to 50 MB, 100 pages), parses content including images and tables, generates AI summaries via OpenAI, and displays the last 5 processed documents. Expected build time: 2–3 hours.

**Assignment deliverables:** GitHub repo with meaningful commits, README (setup, API docs, Docker usage), Dockerfile + docker-compose.yml, Loom demo recording.

Decisions below are **locked** unless explicitly revisited.

---

## Assignment Baseline (from COXIT spec)

| Requirement | Detail |
|-------------|--------|
| PDF upload | Users upload a PDF file |
| PDF parsing | Must support PDFs with **images and tables** |
| Summary generation | OpenAI API |
| History | Show last **5** processed documents |
| Evaluation | Code quality, functionality, documentation, Docker |
| Constraints | Up to **50 MB**, up to **100 pages** |

---

## Architecture Overview

```
┌─────────────┐     poll      ┌──────────────┐   Celery/Redis  ┌─────────────────┐
│  Vue 3 SPA  │ ◄──────────► │ FastAPI API  │ ───────────────► │ Celery worker   │
│  (Naive UI) │   REST       │  + SQLite    │                  │ PDF → Vision    │
└─────────────┘              └──────────────┘                  │ → Summary       │
       │                            │                           └────────┬────────┘
       │                            │                                    │
       │                            ▼                                    ▼
       │                     ./data/db.sqlite                     OpenAI gpt-4o-mini
       │                     ./data/uploads/{uuid}.pdf
       └──────────────────────────────────────────────────────────────────────────
```

**Implementation note:** The repo uses **Celery + Redis** with a dedicated `worker` Compose service (`--concurrency=1`) instead of an in-process asyncio queue. Job polling, single-worker semantics, and status values are unchanged.

**Processing pipeline:**

1. User uploads PDF → validate → save to disk → create job (`pending`)
2. Single worker picks job → rasterize pages → vision extraction (3 pages/call) → concat → one summary call → save → `completed`
3. Frontend polls job status; history shows last 5 completed documents

---

## Locked Decisions

### 1. Tech Stack

| Layer | Choice |
|-------|--------|
| Backend | **Python 3.12 + FastAPI** |
| Frontend | **Vue 3 + Vite + Naive UI** |
| Database | **SQLite** |
| File storage | **Local filesystem** (`./data/uploads/`) |
| AI | **OpenAI `gpt-4o-mini`** |

**Rationale:** Strong PDF rasterization (PyMuPDF), clean async API, auto-generated OpenAPI docs for README, Vue skills match repo tooling.

---

### 2. Persistence & History Scope

- **SQLite** stores document metadata + summary (not full extraction text)
- **PDFs** stored on disk at `data/uploads/{document_uuid}.pdf`
- **History scope:** **Global** — no user auth, no per-session isolation
- **History limit:** Last **5 completed** documents only
- **Failed jobs:** Not shown in history (errors visible on current upload UI only)
- **PDF retention:** Keep files on disk after processing; **no re-download UI** in v1

**SQLite schema (conceptual):**

| Field | Purpose |
|-------|---------|
| `id` | UUID primary key |
| `original_filename` | Sanitized display name |
| `file_path` | Path to stored PDF |
| `status` | `pending`, `queued`, `extracting`, `summarizing`, `completed`, `failed` |
| `summary` | Final TL;DR + bullets (null until complete) |
| `error_message` | Set on failure |
| `failed_at_page` | Optional page range on extraction failure |
| `current_batch`, `total_batches` | Progress during extraction |
| `total_pages` | From validation |
| `uploaded_at`, `completed_at` | Timestamps |

Only **summary** persisted after success — intermediate extraction discarded from memory.

---

### 3. Processing Model

**Async job + polling** (not synchronous HTTP).

| Stage | Behavior |
|-------|----------|
| Upload | `POST /api/documents` returns `{ job_id, document_id }` immediately |
| Processing | **Celery + Redis** background worker (`worker` service, `--concurrency=1`); API dispatches tasks after upload |
| Frontend | Poll `GET /api/jobs/{job_id}` every ~2 seconds |
| Progress UI | Staged: `Uploading` → `Extracting (batch N/M)` → `Summarizing` → `Done` |

**Concurrency:** **Single worker queue** — only one PDF processes at a time. Additional uploads get `pending`/`queued` status and wait. Avoids OpenAI rate limits and keeps scope manageable.

---

### 4. PDF Parsing Strategy — Vision-Based Semantic Extraction

**Deliberately NOT using:** Tesseract OCR, unstructured.io, pdfplumber table reconstruction, or programmatic image extraction.

**Strategy:** Semantic extraction via vision models.

1. Render each PDF page to a **low-res image** (PyMuPDF rasterization — no Poppler/Tesseract in Docker)
2. Pass images to **`gpt-4o-mini` vision** in batches
3. Model outputs:
   - Plain text from the page
   - Tables as **strict Markdown tables**
   - Brief text **captions** for charts/images
4. Concatenate all extraction output
5. Single text-only summary call on the concatenated content

**Rationale:** Preserves table and image semantics in a text digestible format for summarization; keeps Docker lean (no heavy OCR dependencies); robust across varied PDF layouts.

**Risk acknowledged:** 100 dense pages as Markdown may approach `gpt-4o-mini` context limit (~128k tokens). Mitigation: hard-cap at 100 pages at upload; surface clear error if extraction output exceeds model limits. **No chunk summarization / map-reduce** — user explicitly declined.

---

### 5. Vision Extraction Parameters

| Setting | Value |
|---------|-------|
| Pages per API call | **3** (prompt separates pages with `---`) |
| Rasterization | **PyMuPDF** `page.get_pixmap(dpi=150)` |
| Image format | **JPEG, 85% quality** |
| Resolution | **150 DPI** (~1200×1700 px/page) |
| Vision calls for 100 pages | ~34 batches (`ceil(pages / 3)`) |

**Batch prompt shape:** Extract pages N, N+1, N+2; separate with `---`.

---

### 6. OpenAI Call Configuration

| Call type | Model | Temperature | Max output tokens |
|-----------|-------|-------------|-------------------|
| Vision extraction (per 3-page batch) | `gpt-4o-mini` | **0** | **4096** |
| Final summary (text-only) | `gpt-4o-mini` | **0** | **1024** |

- Images sent as base64 `image_url` data URLs in one user message per batch
- **Prompts stored inline** in `backend/app/services/openai.py` (not YAML/template files)

**Extraction system prompt (intent):**

- Output strict Markdown
- Convert tables to Markdown tables
- Describe charts/images with brief captions
- Use the document's primary language

**Summary system prompt (intent):**

- 1–2 sentence TL;DR, then 5–10 bullet key points
- Preserve critical numbers, names, and table data
- Do not invent content not in source
- Use the document's primary language

---

### 7. Language Handling

**Auto-detect only** — no language dropdown in UI.

- Extraction: model outputs in the document's primary language
- Summary: same language as source document
- Prompt instruction: *"Use the document's primary language"*

---

### 8. Summary Output Format

**TL;DR + bullets** (not structured sections, not configurable length).

Example shape:

```
TL;DR: [1–2 sentences]

• Key point 1
• Key point 2
...
• Key point N (5–10 bullets)
```

---

### 9. Upload UX & Validation

| Check | Where | Rule |
|-------|-------|------|
| File type | Client + server | PDF only (MIME + magic bytes) |
| File size | Client + server | ≤ **50 MB** |
| Page count | Server (PyMuPDF on upload) | ≤ **100 pages** |
| UI | Frontend | Drag-and-drop zone + file picker (single file) |

**Progress display:** Staged progress matching job status (not generic spinner only).

---

### 10. Failure Handling & Retries

| Failure point | Behavior |
|---------------|----------|
| Extraction batch fails | Retry up to **3×** with exponential backoff (2s, 4s, 8s) |
| Still failing | Job → `failed`, message e.g. `"Failed on pages 31–33: {error}"` |
| Summary fails | Retry **2×**, then `failed` |
| Manual retry endpoint | **Not in v1** — user re-uploads |

No best-effort partial extraction (skip failed batches).

---

### 11. Upload Security

| Concern | Handling |
|---------|----------|
| Path traversal | Store as `{uuid}.pdf` on disk — no user-controlled paths |
| Display name | Sanitize to `[a-zA-Z0-9._-]`, max 200 chars; store as `original_filename` |
| Validation | Reject empty files, wrong MIME, `%00`, path separators |
| Auth / rate limiting | **Out of scope** for take-home |

---

### 12. API Surface (Minimal REST — 4 endpoints)

```
POST   /api/documents          multipart PDF → { job_id, document_id }
GET    /api/jobs/{job_id}      → { status, stage, progress, error? }
GET    /api/documents          → last 5 completed [{ id, filename, uploaded_at, status, summary_preview }]
GET    /api/documents/{id}     → full summary + metadata
```

**Job status values:** `pending` | `queued` | `extracting` | `summarizing` | `completed` | `failed`

**Progress object:**

```json
{
  "current_batch": 4,
  "total_batches": 34,
  "pages_processed": 12,
  "total_pages": 100
}
```

FastAPI auto-generates OpenAPI at `/docs` — link from README.

**Not included:** `DELETE`, `/health`, webhooks, PDF re-download.

---

### 13. Frontend (Naive UI)

| Area | Choice |
|------|--------|
| Component library | **Naive UI** (`NUpload`, `NProgress`, `NCollapse`, `NAlert`, `NSpin`) |
| History panel | Minimal rows: filename, date, status badge |
| Interaction | Click row → **inline expand** full summary |
| Mobile responsive | Nice-to-have, not required |

---

### 14. Docker & Local Dev

**Split containers with hot reload (Option D):**

| Service | Port | Notes |
|---------|------|-------|
| `backend` | **8000** | Python 3.12, uvicorn `--reload`, PyMuPDF |
| `frontend` | **5173** | Node 20, Vite dev server |

**Environment:**

- `OPENAI_API_KEY` in `.env` (gitignored), passed to backend
- `VITE_API_URL=http://localhost:8000` for frontend

**Volumes:**

- `./data` → uploads + SQLite (gitignored)

**CORS:** Backend allows `http://localhost:5173`

**README quick start:** `docker compose up` → open `http://localhost:5173`

**Production single-container build:** Documented as optional; not required for v1.

---

### 15. Repository Layout

```
/
├── backend/
│   ├── app/
│   │   ├── main.py
│   │   ├── models/
│   │   ├── routers/
│   │   ├── services/
│   │   │   └── openai.py      # inline prompts
│   │   └── workers/
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/
│   ├── src/
│   ├── package.json
│   └── Dockerfile
├── data/                       # gitignored
├── docker-compose.yml
├── .env.example
└── README.md
```

**`.gitignore`:** `data/`, `.env`, `node_modules/`, `__pycache__/`, `.venv/`

---

### 16. Testing

**No automated tests in v1.** Loom recording serves as manual verification.

---

## Explicit Out of Scope (v1)

- User auth / accounts
- Delete document endpoint
- Re-download original PDF
- Automated tests (unit, integration, E2E)
- CI/CD pipeline
- Full extracted text storage or "view extraction" UI
- Summary chunking / map-reduce for long documents
- OCR / Tesseract / unstructured.io
- Multi-file upload queue UI
- Rate limiting on your API
- Production single-container Docker image
- Email notifications
- Usage tracking / payments
- Manual job retry endpoint
- Health check endpoint
- Language selector dropdown

---

## README Expectations (for submission)

The assignment README should include:

1. **Project description** — what it does, architecture summary
2. **Setup instructions** — local dev and Docker (`cp .env.example .env`, `docker compose up`)
3. **API documentation** — endpoint table + link to `/docs`
4. **Docker usage** — services, ports, volumes
5. **OpenAI key** — how to obtain and configure
6. **Limitations** — 100 pages, 50 MB, single worker, context window risk on dense docs

---

## Loom Demo Script (suggested)

1. `docker compose up`, show both services healthy
2. Upload a PDF with tables and/or images
3. Show staged progress (extracting batch N/M, summarizing)
4. Display completed TL;DR + bullets summary
5. Show history panel with last 5 — click to expand inline
6. Optionally upload a second PDF while first processes — show queued state
7. Briefly show `/docs` OpenAPI page

---

## Decision Log (Q&A Reference)

| # | Question | Decision |
|---|----------|----------|
| Q1 | Tech stack | A — FastAPI + Vue 3 |
| Q2 | Persistence | A — SQLite + filesystem, global history |
| Q3 | Processing | B — Async + polling |
| Q4 | PDF parsing | Vision model semantic extraction (custom) |
| Q5 | Pipeline | 3 pages/call → concat → single summary, no chunking |
| Q6 | Rasterization | B — 150 DPI JPEG 85% |
| Q7 | Summary format | C — TL;DR + bullets |
| Q8 | Language | A — Auto-detect only |
| Q9 | History UI | A — Minimal, inline expand; completed only |
| Q10 | Upload UX | C — Full validation + staged progress |
| Q11 | Failures | B — Auto-retry batches + summary |
| Q12 | Docker | D — Split + hot reload |
| Q13 | API | A — Minimal 4 endpoints |
| Q14 | Tests | A — None |
| Q15 | UI polish | D — Component library |
| Q16 | Library | A — Naive UI |
| Q17 | Persist what | A — Summary only |
| Q18 | Concurrency | A — Single worker queue |
| Q19 | OpenAI params | A — temp=0, deterministic |
| Q20 | Repo layout | A — Monorepo `/backend`, `/frontend` |
| Q21 | Prompts | A — Inline in Python |
| Q22 | Security | A — UUID storage, sanitized names |
| Q23 | Scope | Out-of-scope list confirmed; no additions |

---

## Guidance

When implementing, treat this document as the **source of truth** for scope. If a choice is not listed here, prefer the simplest option that satisfies the COXIT assignment baseline. Do not add features from the out-of-scope list without revisiting this doc.

**Implementation order suggestion:**

1. Docker skeleton + health of both services
2. Upload + validation + SQLite models
3. PyMuPDF rasterization + vision extraction loop
4. Summary call + job status API
5. Frontend upload + polling + history
6. README + Loom

---

## Why This Matters

Documenting requirements before coding prevents scope creep in a 2–3 hour window. The vision-extraction approach is the highest-risk/highest-reward decision — it trades traditional PDF parsing complexity for OpenAI cost and latency, which fits the assignment's emphasis on AI integration and Docker simplicity.

---

## When to Apply

- Before writing any application code for this project
- When evaluating whether a feature request is in or out of scope
- When onboarding or reviewing the take-home submission
- When debugging pipeline behavior (extraction vs summary vs queue)

---

## Examples

**Valid upload flow:**

```
POST /api/documents (report.pdf, 42 pages, 12MB)
→ { job_id: "...", document_id: "..." }
GET /api/jobs/{job_id} → { status: "extracting", progress: { current_batch: 5, total_batches: 14, ... } }
...
GET /api/jobs/{job_id} → { status: "completed" }
GET /api/documents/{id} → { summary: "TL;DR: ...\n\n• ..." }
```

**Rejected upload:**

```
POST /api/documents (101-page.pdf)
→ 400 { detail: "PDF exceeds maximum of 100 pages" }
```

---

## Related

- COXIT take-home assignment brief (objective, deliverables, evaluation criteria)
- OpenAI Vision API docs — multi-image messages, base64 encoding
- PyMuPDF documentation — `Page.get_pixmap()`
