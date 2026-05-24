from datetime import datetime

from pydantic import BaseModel, Field


class UploadResponse(BaseModel):
    job_id: str
    document_id: str


class Progress(BaseModel):
    current_batch: int
    total_batches: int
    pages_processed: int
    total_pages: int


class JobResponse(BaseModel):
    status: str
    stage: str
    progress: Progress
    error: str | None = None


class DocumentSummaryItem(BaseModel):
    id: str
    filename: str
    uploaded_at: datetime
    status: str
    summary_preview: str | None = None


class DocumentDetailResponse(BaseModel):
    id: str
    filename: str
    uploaded_at: datetime
    completed_at: datetime | None = None
    status: str
    stage: str
    summary: str | None = None
    error_message: str | None = None
    progress: Progress


class DocumentListResponse(BaseModel):
    items: list[DocumentSummaryItem] = Field(default_factory=list)
