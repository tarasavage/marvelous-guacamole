from fastapi import APIRouter, File, HTTPException, UploadFile

from app.dependencies import (
    GetDocumentUseCaseDep,
    GetJobUseCaseDep,
    ListDocumentsUseCaseDep,
    UploadDocumentUseCaseDep,
)
from app.exceptions import (
    DocumentNotFoundError,
    EnqueueError,
    UploadPersistenceError,
    UploadValidationError,
)
from app.schemas.document import (
    DocumentDetailResponse,
    DocumentListResponse,
    JobResponse,
    UploadResponse,
)

router = APIRouter()


@router.post("/documents", response_model=UploadResponse, status_code=201)
async def upload_document(
    use_case: UploadDocumentUseCaseDep,
    file: UploadFile = File(...),
) -> UploadResponse:
    data = await file.read()
    try:
        return use_case.execute(file.filename, data)
    except UploadValidationError as exc:
        detail = str(exc)
        status_code = 413 if "maximum size" in detail else 400
        raise HTTPException(status_code=status_code, detail=detail) from exc
    except EnqueueError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    except UploadPersistenceError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.get("/jobs/{job_id}", response_model=JobResponse)
def get_job(job_id: str, use_case: GetJobUseCaseDep) -> JobResponse:
    try:
        return use_case.execute(job_id)
    except DocumentNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Document not found") from exc


@router.get("/documents", response_model=DocumentListResponse)
def list_documents(use_case: ListDocumentsUseCaseDep) -> DocumentListResponse:
    return use_case.execute()


@router.get("/documents/{document_id}", response_model=DocumentDetailResponse)
def get_document(document_id: str, use_case: GetDocumentUseCaseDep) -> DocumentDetailResponse:
    try:
        return use_case.execute(document_id)
    except DocumentNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Document not found") from exc
