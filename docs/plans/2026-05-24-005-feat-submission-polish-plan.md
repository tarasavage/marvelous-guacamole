---
title: "feat: Submission polish — README, Loom script, requirements sync (Milestone 6)"
type: feat
status: completed
date: 2026-05-24
origin: docs/solutions/architecture-patterns/pdf-summary-ai-requirements-2026-05-24.md
---

# feat: Submission polish — README, Loom script, requirements sync (Milestone 6)

## Summary

Bring the repo to COXIT submission quality: expand `README.md` to satisfy all six evaluator expectations from the origin doc, add a Loom recording checklist aligned with the suggested demo script, and patch the requirements doc to reflect the implemented Celery + Redis queue (origin still says asyncio). No application code changes unless a tiny doc-adjacent fix is discovered during manual verification.

---

## Problem Frame

M1–M5 deliver a working end-to-end app, but the README is still milestone-oriented and thin on architecture, Docker service detail, and OpenAI setup guidance. The requirements doc is stale on the job queue. Evaluators expect submission-ready documentation and a Loom walkthrough (see origin assignment deliverables, §376–397).

---

## Requirements

- R1. README includes **project description** with architecture summary (see origin README expectations §1).
- R2. README includes **setup** for Docker and env (`cp .env.example .env`, `docker compose up --build`) (see origin §2).
- R3. README includes **API documentation** — endpoint table + link to `http://localhost:8000/docs` (see origin §3).
- R4. README includes **Docker usage** — all Compose services, ports, volumes, hot reload notes (see origin §4, §14).
- R5. README includes **OpenAI key** — how to obtain (platform.openai.com) and configure in `.env` for backend + worker (see origin §5, §14).
- R6. README includes **limitations** — 100 pages, 50 MB, single worker, context window risk, no checkpoint resume (see origin §6).
- R7. Provide **Loom demo script** as a repo artifact evaluators/reviewer can follow; align with origin suggested 7-step script (see origin Loom Demo Script).
- R8. Update requirements doc processing model to document **Celery + Redis** implementation choice without reopening product scope (see M2 plan deferral).
- R9. Remove internal milestone/status tracking from README; frame as submission-ready product (see assignment deliverables).
- R10. Manual verification checklist before recording Loom — confirm full demo path works (see origin §16 — manual verification acceptable).

**Origin flows:** F1–F4 (demo must show upload, progress, summary, history)

---

## Scope Boundaries

- New features, API endpoints, automated tests, CI/CD
- Recording or uploading the Loom video itself (human step outside repo)
- Opening PR / merging to `main` (separate git workflow unless user requests during `/ce-work`)
- Production single-container Docker image
- Rewriting the full requirements doc — surgical Celery note only

### Deferred to Follow-Up Work

- **PR to main:** merge `feat/initial-scaffold` when ready to submit
- **Sample PDF in repo:** optional; use any PDF with tables/images locally for Loom

---

## Context & Research

### Relevant Code and Patterns

- `README.md` — has API table, quick start, limitations; missing architecture diagram prose, full Docker matrix, OpenAI obtain steps, Loom pointer
- `docs/solutions/architecture-patterns/pdf-summary-ai-requirements-2026-05-24.md` — §3 still says "asyncio queue"; §376–397 define submission targets
- `docker-compose.yml` — four services: `backend`, `worker`, `redis`, `frontend`
- `.env.example` — `OPENAI_API_KEY`, `DATA_DIR`, `REDIS_URL`, `VITE_API_URL`
- M5 plan deferred: "Milestone 6 — Submission polish"

### Institutional Learnings

- Origin implementation order step 6: "README + Loom"
- Assignment deliverables: meaningful commits, README, Docker, Loom recording
- Celery + Redis documented in M2 plan as intentional deviation from origin asyncio wording

### External References

- OpenAI API keys: https://platform.openai.com/api-keys

---

## Key Technical Decisions

- **README structure:** Single `README.md` as evaluator entry point — add Architecture, Docker Services, Environment, Demo/Loom sections; keep existing API/Limitations content and expand rather than duplicate.
- **Architecture summary:** Short prose + ASCII or mermaid diagram mirroring origin §49–62 but label queue as Celery/Redis/worker container.
- **Loom artifact:** `docs/demo/loom-script.md` — step checklist with expected UI states and URLs; link from README. Do not embed video URL until user records it (optional placeholder section "Loom link: TBD").
- **Requirements doc patch:** Update §3 Processing Model table and architecture diagram caption to note Celery + Redis + worker service; add one-line "Implementation note" that behavior matches origin (single worker, polling) with different dispatch mechanism.
- **Gitignore hygiene:** Add `frontend/.vite/` and `frontend/tsconfig.tsbuildinfo` if not already ignored — doc-adjacent repo cleanliness, not feature work.
- **Verification gate:** Manual checklist in Loom doc or README before recording; no new test suite.

---

## Open Questions

### Resolved During Planning

- What is M6 scope? → Submission docs + requirements sync + manual demo verification.
- Code changes needed? → Unlikely; only if verification finds a doc-exposed bug.

### Deferred to Implementation

- Whether user adds Loom URL to README after recording
- Which sample PDF to use for demo (local file, not committed)

---

## Implementation Units

- U1. **Expand README for evaluator expectations**

**Goal:** README satisfies origin §376–386 all six bullets.

**Requirements:** R1–R6, R9

**Dependencies:** None

**Files:**
- Modify: `README.md`

**Approach:**
- Add **Architecture** section: upload → API → Celery worker → OpenAI vision → summary → SQLite; mention Vue polling UI.
- Add **Docker services** table: service name, port (if exposed), role (`backend`, `worker`, `redis`, `frontend`).
- Add **Environment variables** table from `.env.example` with brief purpose.
- Add **OpenAI setup** subsection: create key at platform.openai.com, paste into `.env`, restart compose.
- Prominent link to OpenAPI `/docs`.
- Remove "Milestone N complete" status block; replace with one-line project summary suitable for submission.
- Keep curl examples; add note that browser UI at `:5173` is the primary demo path.

**Patterns to follow:**
- Existing README sections (API table, Limitations)

**Test scenarios:**
- Test expectation: none — documentation; reviewer reads README against origin checklist

**Verification:**
- Each of origin's six README bullets has a clearly labeled section
- New clone can follow README alone to run the app

---

- U2. **Loom demo script artifact**

**Goal:** Checklist for recording the submission video per origin script.

**Requirements:** R7, R10

**Dependencies:** U1 (README links to script)

**Files:**
- Create: `docs/demo/loom-script.md`
- Modify: `README.md` (link under Demo / Submission section)

**Approach:**
- Numbered steps matching origin Loom script (§389–397).
- For each step: action, expected screen, URL, optional talking points.
- Add **Pre-flight checklist:** `.env` with valid key, `docker compose up --build`, sample PDF ready, both `:5173` and `:8000/docs` reachable.
- Add **Failure fallbacks:** what to show if OpenAI slow (queued state) or if second upload demo skipped.
- Note: recording is manual; optional `## Loom recording` placeholder in README for URL.

**Test scenarios:**
- Test expectation: none — human records video following script

**Verification:**
- Script covers all 7 origin steps
- Pre-flight checklist executable without ambiguity

---

- U3. **Sync requirements doc with Celery + Redis**

**Goal:** Requirements doc matches implemented architecture without scope drift.

**Requirements:** R8

**Dependencies:** None

**Files:**
- Modify: `docs/solutions/architecture-patterns/pdf-summary-ai-requirements-2026-05-24.md`

**Approach:**
- In §3 Processing Model: replace "asyncio queue, single worker" with Celery + Redis broker + dedicated `worker` Compose service, `--concurrency=1`.
- Update §49–62 architecture diagram text or add implementation note below it.
- State explicitly: polling contract and single-job semantics unchanged from origin intent.
- Do not change locked product decisions or out-of-scope list.

**Patterns to follow:**
- M2 plan architecture change note

**Test scenarios:**
- Test expectation: none — documentation

**Verification:**
- §3 no longer claims asyncio in-process queue as the implementation
- Celery/Redis/worker mentioned consistently with `docker-compose.yml`

---

- U4. **Repo hygiene and manual verification**

**Goal:** Clean untracked build artifacts; confirm demo path before Loom.

**Requirements:** R10

**Dependencies:** U1, U2

**Files:**
- Modify: `.gitignore` (if needed)
- Modify: `docs/demo/loom-script.md` (verification outcomes section) or README

**Approach:**
- Ignore `frontend/.vite/`, `frontend/tsconfig.tsbuildinfo`, `frontend/dist/` if missing from `.gitignore`.
- Run manual E2E once: upload → extracting progress → completed → history expand; optionally second upload for queue demo.
- Record any blocking bugs found → fix in separate minimal commit during `/ce-work`, or note in plan if out of scope.

**Patterns to follow:**
- Origin Loom script steps 2–5 as acceptance path

**Test scenarios:**
- Test expectation: none — manual verification per origin §16

**Verification:**
- Demo path works with `OPENAI_API_KEY` set
- No stray build cache files required for git cleanliness

---

## System-Wide Impact

- **Interaction graph:** Documentation only; no runtime behavior change.
- **Error propagation:** N/A.
- **State lifecycle risks:** N/A.
- **API surface parity:** N/A.
- **Integration coverage:** Manual Loom rehearsal proves cross-service flow.
- **Unchanged invariants:** Application code, API contract, Docker topology.

---

## Risks & Dependencies

| Risk | Mitigation |
|------|------------|
| README still too milestone-internal | U1 explicitly removes milestone status |
| Loom fails mid-demo (OpenAI latency) | Script includes queued/wait talking points |
| Requirements edit over-scopes | Surgical §3 + diagram note only |
| Verification finds UI bug | U4 allows minimal fix during ce-work |

---

## Documentation / Operational Notes

- User must record Loom externally and optionally paste URL into README.
- Submission also needs meaningful commit history on GitHub — already satisfied on `feat/initial-scaffold`; merge/PR is follow-up.

---

## Sources & References

- **Origin document:** [docs/solutions/architecture-patterns/pdf-summary-ai-requirements-2026-05-24.md](../solutions/architecture-patterns/pdf-summary-ai-requirements-2026-05-24.md)
- Prior plan: [docs/plans/2026-05-24-004-feat-frontend-upload-history-plan.md](2026-05-24-004-feat-frontend-upload-history-plan.md)
- Compose: `docker-compose.yml`
