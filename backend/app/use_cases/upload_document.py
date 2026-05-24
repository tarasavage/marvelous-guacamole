import math
from collections.abc import Callable
from pathlib import Path

from app.exceptions import EnqueueError, UploadPersistenceError, UploadValidationError
from app.models.document import Document, DocumentStatus
from app.repositories.document import DocumentRepository
from app.schemas.document import UploadResponse
from app.services.pdf_rasterize import PAGES_PER_BATCH
from app.services.pdf_validation import MAX_FILE_SIZE_BYTES, PDFValidationError, validate_pdf_bytes
from app.services.storage import delete_pdf, sanitize_filename, save_pdf


class UploadDocumentUseCase:
    def __init__(
        self,
        repo: DocumentRepository,
        data_dir: str,
        enqueue: Callable[[str], object],
    ) -> None:
        self._repo = repo
        self._data_dir = data_dir
        self._enqueue = enqueue

    def execute(self, filename: str | None, data: bytes) -> UploadResponse:
        if filename is None or filename.strip() == "":
            raise UploadValidationError("Missing file")

        if len(data) > MAX_FILE_SIZE_BYTES:
            raise UploadValidationError("PDF exceeds maximum size of 50 MB")

        try:
            page_count = validate_pdf_bytes(data)
        except PDFValidationError as exc:
            raise UploadValidationError(str(exc)) from exc

        saved_path: Path | None = None
        document_id: str | None = None

        try:
            document_id, saved_path = save_pdf(data, self._data_dir)
            total_batches = math.ceil(page_count / PAGES_PER_BATCH) if page_count else 0

            document = Document(
                id=document_id,
                original_filename=sanitize_filename(filename),
                file_path=str(saved_path),
                status=DocumentStatus.PENDING.value,
                total_pages=page_count,
                total_batches=total_batches,
                current_batch=0,
            )
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
        except (UploadValidationError, EnqueueError):
            raise
        except Exception as exc:
            self._repo.rollback()
            if saved_path is not None:
                delete_pdf(saved_path)
            raise UploadPersistenceError("Failed to save document") from exc

        return UploadResponse(job_id=document_id, document_id=document_id)
