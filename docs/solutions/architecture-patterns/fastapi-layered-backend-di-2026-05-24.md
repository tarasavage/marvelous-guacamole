---
title: "FastAPI layered backend with dependency injection"
date: 2026-05-24
category: architecture-patterns
module: pdf-summary-ai-backend
problem_type: architecture_pattern
component: service_object
severity: high
applies_when:
  - "FastAPI routers contain SQL, orchestration, or response shaping"
  - "Celery tasks duplicate business logic that HTTP handlers also need"
  - "Adding tests requires standing up HTTP to exercise core workflows"
tags:
  - fastapi
  - dependency-injection
  - layered-architecture
  - use-cases
  - repository-pattern
  - celery
  - sqlalchemy
---

# FastAPI layered backend with dependency injection

## Context

The PDF Summary AI backend started as a take-home scaffold: routers owned upload sagas, SQL queries, progress math, and Celery enqueue rollback; the Celery task owned the full processing pipeline with direct `SessionLocal` access. That worked for speed but made routers hard to test and duplicated orchestration boundaries between HTTP and background workers.

## Guidance

Split the backend into four responsibilities, wired with FastAPI `Depends`:

| Layer | Responsibility | Example path |
|-------|----------------|--------------|
| **Router** | HTTP parsing, status mapping | `backend/app/routers/documents.py` |
| **Use-case** | Application workflows | `backend/app/use_cases/upload_document.py` |
| **Repository** | SQLAlchemy persistence | `backend/app/repositories/document.py` |
| **Mapper** | ORM → Pydantic responses | `backend/app/mappers/document.py` |
| **Services** | Infrastructure adapters (unchanged) | `backend/app/services/openai.py` |

Centralize DI in `backend/app/dependencies.py`:

```python
def get_document_repository(db: DbSession) -> DocumentRepository:
    return DocumentRepository(db)

def get_upload_document_use_case(
    repo: DocumentRepositoryDep,
    app_settings: SettingsDep,
) -> UploadDocumentUseCase:
    from app.tasks.document import process_document_task

    return UploadDocumentUseCase(
        repo=repo,
        data_dir=app_settings.data_dir,
        enqueue=process_document_task.delay,
    )

UploadDocumentUseCaseDep = Annotated[UploadDocumentUseCase, Depends(get_upload_document_use_case)]
```

Routers stay thin — call one use-case, map domain exceptions to HTTP:

```python
@router.post("/documents", response_model=UploadResponse, status_code=201)
async def upload_document(
    use_case: UploadDocumentUseCaseDep,
    file: UploadFile = File(...),
) -> UploadResponse:
    data = await file.read()
    try:
        return use_case.execute(file.filename, data)
    except UploadValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
```

Celery tasks become one-liners that reuse the same use-case:

```python
@celery_app.task(name="process_document")
def process_document_task(document_id: str) -> None:
    with db_module.SessionLocal() as session:
        ProcessDocumentUseCase(DocumentRepository(session)).execute(document_id)
```

Use domain exceptions (`DocumentNotFoundError`, `UploadValidationError`, `EnqueueError`) in use-cases; routers translate them to `HTTPException`. Inject enqueue as a callable so upload tests mock Celery without a broker.

**Keep sync SQLAlchemy** when Celery workers share the same DB session pattern — async migration is a separate, larger scope change.

## Why This Matters

Without layers, every test that exercises upload logic needs `TestClient`, multipart fixtures, and a running DB through HTTP. With use-cases + repositories, the same saga runs in unit tests with an in-memory SQLite session and a mocked `enqueue`. Celery and FastAPI share one code path for processing, so recovery and worker behavior cannot drift from API behavior.

## When to Apply

- Routers exceed ~30 lines of non-HTTP logic (SQL, file I/O orchestration, compensation)
- Background tasks open their own DB sessions and duplicate status transitions
- You need tests for business rules without HTTP or Celery infrastructure
- The codebase has one or two entities (this repo) — avoid generic `domain/application/infrastructure` sprawl; `use_cases/` + `repositories/` is enough

## Examples

**Before (router owns saga):**

```python
# routers/documents.py — SQL, storage, enqueue, rollback in handler
doc = Document(...)
db.add(doc)
db.commit()
try:
    process_document_task.delay(document_id)
except Exception:
    db.delete(doc)
    db.commit()
    delete_pdf(saved_path)
    raise HTTPException(status_code=500, ...)
```

**After (use-case owns saga, router maps errors):**

```python
# use_cases/upload_document.py
self._repo.add(document)
self._repo.commit()
try:
    self._enqueue(document_id)
    document.status = DocumentStatus.QUEUED.value
    self._repo.commit()
except Exception as exc:
    self._repo.delete(document)
    self._repo.commit()
    delete_pdf(saved_path)
    raise EnqueueError("Failed to enqueue document processing") from exc
```

**Test without HTTP:**

```python
use_case = UploadDocumentUseCase(repo=document_repo, data_dir=str(data_dir), enqueue=Mock())
response = use_case.execute("sample.pdf", pdf_bytes)
assert document_repo.get_by_id(response.document_id).status == "queued"
```

## Related

- [PDF Summary AI requirements](pdf-summary-ai-requirements-2026-05-24.md) — locked product scope and original scaffold layout
- Plan: `docs/plans/2026-05-24-006-refactor-backend-layer-architecture-plan.md`
- Tests: `backend/tests/test_document_use_cases.py` (9 cases, pytest + temp data dir)
