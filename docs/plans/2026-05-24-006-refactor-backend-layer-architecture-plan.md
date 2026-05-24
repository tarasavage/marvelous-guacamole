---
title: "refactor: Backend layer architecture with FastAPI DI"
type: refactor
status: completed
date: 2026-05-24
---

# refactor: Backend layer architecture with FastAPI DI

## Summary

Refactor the PDF Summary AI backend into thin routers, use-case orchestration, repository persistence, and response mappers — wired with FastAPI `Depends` — while preserving the existing API contract, sync SQLAlchemy, and Celery worker setup.

---

## Requirements

- R1. Routers contain HTTP concerns only (request parsing, status mapping); no SQL or business orchestration.
- R2. Use-cases own application workflows (upload saga, document reads, processing pipeline).
- R3. Repositories own SQLAlchemy access for the `Document` entity.
- R4. Existing `services/` remain infrastructure adapters (OpenAI, PDF, storage).
- R5. Celery task is a thin entry point delegating to the processing use-case.
- R6. API behavior and response schemas remain unchanged for all four endpoints.
- R7. Minimal pytest coverage validates use-cases and API routes.

---

## Scope Boundaries

- No async SQLAlchemy migration
- No new endpoints, auth, or frontend changes
- No Celery/Redis architecture changes
- No rename of `services/` to `infrastructure/`

---

## Key Technical Decisions

- **Layer shape:** `routers` → `use_cases` → `repositories` → `services` (infra), plus `mappers` for ORM→schema conversion and `dependencies.py` for DI wiring.
- **Sync SQLAlchemy retained:** matches Celery worker and existing `get_db()` pattern; no async migration.
- **Domain exceptions:** `DocumentNotFoundError`, `UploadValidationError`, etc. mapped to HTTP status in routers.
- **QUEUED status:** set after successful Celery enqueue (fixes previously unused enum value).
- **Tests:** pytest + TestClient with temp data dir; mock Celery enqueue in API tests.

---

## Implementation Units

- U1. **Foundation layer** — `exceptions.py`, `repositories/document.py`, `dependencies.py`
- U2. **Mappers** — `mappers/document.py`
- U3. **Read use-cases** — `get_job`, `list_documents`, `get_document`
- U4. **Upload use-case** — upload saga with enqueue + rollback
- U5. **Process use-case** — pipeline extracted from Celery task
- U6. **Wire-up** — thin routers, thin task, recovery via repository
- U7. **Tests** — `backend/tests/` with pytest fixtures and use-case/API coverage
