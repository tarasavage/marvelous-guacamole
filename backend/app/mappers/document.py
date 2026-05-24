from app.models.document import Document
from app.schemas.document import (
    DocumentDetailResponse,
    DocumentListResponse,
    DocumentSummaryItem,
    JobResponse,
    Progress,
)
from app.services.pdf_rasterize import PAGES_PER_BATCH


def progress_for(document: Document) -> Progress:
    pages_processed = (
        min(document.current_batch * PAGES_PER_BATCH, document.total_pages)
        if document.total_pages
        else 0
    )
    return Progress(
        current_batch=document.current_batch,
        total_batches=document.total_batches,
        pages_processed=pages_processed,
        total_pages=document.total_pages,
    )


def summary_preview(summary: str | None) -> str | None:
    if summary is None:
        return None
    if len(summary) > 150:
        return summary[:150] + "…"
    return summary


def to_job_response(document: Document) -> JobResponse:
    return JobResponse(
        status=document.status,
        stage=document.stage,
        progress=progress_for(document),
        error=document.error_message,
    )


def to_summary_item(document: Document) -> DocumentSummaryItem:
    return DocumentSummaryItem(
        id=document.id,
        filename=document.original_filename,
        uploaded_at=document.uploaded_at,
        status=document.status,
        summary_preview=summary_preview(document.summary),
    )


def to_list_response(documents: list[Document]) -> DocumentListResponse:
    return DocumentListResponse(items=[to_summary_item(document) for document in documents])


def to_detail_response(document: Document) -> DocumentDetailResponse:
    return DocumentDetailResponse(
        id=document.id,
        filename=document.original_filename,
        uploaded_at=document.uploaded_at,
        completed_at=document.completed_at,
        status=document.status,
        stage=document.stage,
        summary=document.summary,
        error_message=document.error_message,
        progress=progress_for(document),
    )
