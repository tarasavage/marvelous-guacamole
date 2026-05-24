# Loom Demo Script — PDF Summary AI

Use this checklist when recording the COXIT submission video. Target length: ~3–5 minutes.

## Pre-flight

- [ ] `.env` exists with a valid `OPENAI_API_KEY`
- [ ] `docker compose up --build` — all four services running (`frontend`, `backend`, `worker`, `redis`)
- [ ] http://localhost:5173 loads; header shows **Backend connected**
- [ ] Sample PDF ready locally (prefer one with **tables and/or images**, under 100 pages)
- [ ] Optional second PDF for queue demo

## Recording steps

### 1. Start services

**Action:** Show terminal with `docker compose up --build` (or already running).

**Say:** Monorepo with FastAPI, Celery worker, Redis, and Vue frontend — single command startup.

---

### 2. Upload a PDF

**Action:** Open http://localhost:5173 → drag-and-drop or pick the sample PDF.

**Expected:** Upload starts; progress area appears (`Queued` → `Extracting`).

**Say:** Client validates PDF type and 50 MB limit; server validates page count.

---

### 3. Staged progress

**Action:** Wait on the upload card while job runs.

**Expected:** Stage label updates — e.g. `Extracting (batch 2/14)`, progress bar moves; then `Summarizing`.

**Say:** Vision extraction batches 3 pages per OpenAI call; frontend polls every 2 seconds.

**Fallback:** If slow, narrate the queued/extracting states — no need to speed up the video.

---

### 4. Completed summary

**Action:** Wait for green **Summary ready** (or open history).

**Expected:** Job reaches `completed`.

**Say:** Worker concatenates extractions and runs one summary call — TL;DR + bullets.

---

### 5. History panel

**Action:** Scroll to **Recent summaries** → click a row to expand.

**Expected:** Full summary text inline; filename, date, status badge on row.

**Say:** Last 5 completed documents only; failed jobs stay on the upload UI.

---

### 6. Queue demo (optional)

**Action:** Upload a second PDF while the first is still processing (or start two in sequence).

**Expected:** Second job shows `Queued` / waits until worker is free.

**Say:** Single Celery worker with concurrency 1 — by design for rate limits and scope.

---

### 7. OpenAPI docs

**Action:** Open http://localhost:8000/docs in a new tab.

**Expected:** Swagger UI with four document endpoints.

**Say:** Minimal REST surface; FastAPI auto-generates docs.

---

## Post-recording

- [ ] Upload Loom video and paste URL into README **Loom link** section
- [ ] Push final commits to GitHub
- [ ] Open PR or merge to default branch per your submission process

## Manual verification log

Run once before recording and note results:

| Check | Pass? |
|-------|-------|
| Upload → completed summary in UI | |
| History expand shows full text | |
| `/docs` loads four endpoints | |
| Invalid file rejected client-side | |
