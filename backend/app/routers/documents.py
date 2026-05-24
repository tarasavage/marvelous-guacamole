import math
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import settings
from app.db import get_db
from app.models.document import Document, DocumentStatus
from app.schemas.document import (
    DocumentDetailResponse,
    DocumentListResponse,
    DocumentSummaryItem,
    JobResponse,
    Progress,
    UploadResponse,
)
from app.services.pdf_validation import MAX_FILE_SIZE_BYTES, PDFValidationError, validate_pdf_bytes
from app.services.storage import delete_pdf, sanitize_filename, save_pdf
from app.tasks.document import process_document_task

router = APIRouter()


def _progress_for(doc: Document) -> Progress:
    pages_processed = min(doc.current_batch * 3, doc.total_pages) if doc.total_pages else 0
    return Progress(
        current_batch=doc.current_batch,
        total_batches=doc.total_batches,
        pages_processed=pages_processed,
        total_pages=doc.total_pages,
    )


def _document_or_404(db: Session, document_id: str) -> Document:
    doc = db.get(Document, document_id)
    if doc is None:
        raise HTTPException(status_code=404, detail="Document not found")
    return doc


@router.post("/documents", response_model=UploadResponse, status_code=201)
async def upload_document(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
) -> UploadResponse:
    if file.filename is None or file.filename.strip() == "":
        raise HTTPException(status_code=400, detail="Missing file")

    data = await file.read()
    if len(data) > MAX_FILE_SIZE_BYTES:
        raise HTTPException(status_code=413, detail="PDF exceeds maximum size of 50 MB")

    try:
        page_count = validate_pdf_bytes(data)
    except PDFValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    saved_path: Path | None = None
    document_id: str | None = None

    try:
        document_id, saved_path = save_pdf(data, settings.data_dir)
        total_batches = math.ceil(page_count / 3) if page_count else 0

        doc = Document(
            id=document_id,
            original_filename=sanitize_filename(file.filename),
            file_path=str(saved_path),
            status=DocumentStatus.PENDING.value,
            total_pages=page_count,
            total_batches=total_batches,
            current_batch=0,
        )
        db.add(doc)
        db.commit()

        try:
            process_document_task.delay(document_id)
        except Exception as exc:
            db.delete(doc)
            db.commit()
            delete_pdf(saved_path)
            raise HTTPException(
                status_code=500, detail="Failed to enqueue document processing"
            ) from exc
    except HTTPException:
        raise
    except Exception as exc:
        db.rollback()
        if saved_path is not None:
            delete_pdf(saved_path)
        raise HTTPException(status_code=500, detail="Failed to save document") from exc

    return UploadResponse(job_id=document_id, document_id=document_id)


@router.get("/jobs/{job_id}", response_model=JobResponse)
def get_job(job_id: str, db: Session = Depends(get_db)) -> JobResponse:
    doc = _document_or_404(db, job_id)
    return JobResponse(
        status=doc.status,
        stage=doc.stage,
        progress=_progress_for(doc),
        error=doc.error_message,
    )


@router.get("/documents", response_model=DocumentListResponse)
def list_documents(db: Session = Depends(get_db)) -> DocumentListResponse:
    rows = db.scalars(
        select(Document)
        .where(Document.status == DocumentStatus.COMPLETED.value)
        .order_by(Document.completed_at.desc(), Document.uploaded_at.desc())
        .limit(5)
    ).all()

    items = [
        DocumentSummaryItem(
            id=doc.id,
            filename=doc.original_filename,
            uploaded_at=doc.uploaded_at,
            status=doc.status,
            summary_preview=(
                doc.summary[:150] + "…" if doc.summary and len(doc.summary) > 150 else doc.summary
            ),
        )
        for doc in rows
    ]
    return DocumentListResponse(items=items)


@router.get("/documents/{document_id}", response_model=DocumentDetailResponse)
def get_document(document_id: str, db: Session = Depends(get_db)) -> DocumentDetailResponse:
    doc = _document_or_404(db, document_id)
    return DocumentDetailResponse(
        id=doc.id,
        filename=doc.original_filename,
        uploaded_at=doc.uploaded_at,
        completed_at=doc.completed_at,
        status=doc.status,
        stage=doc.stage,
        summary=doc.summary,
        error_message=doc.error_message,
        progress=_progress_for(doc),
    )
