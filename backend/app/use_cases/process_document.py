import logging
from datetime import datetime, timezone
from pathlib import Path

from app.config import settings
from app.models.document import Document, DocumentStatus
from app.repositories.document import DocumentRepository
from app.services import openai as openai_service
from app.services.pdf_rasterize import PAGES_PER_BATCH, rasterize_batch

logger = logging.getLogger(__name__)


def page_range_for_batch(batch_index: int, total_pages: int) -> tuple[int, int]:
    start_page = (batch_index - 1) * PAGES_PER_BATCH + 1
    end_page = min(batch_index * PAGES_PER_BATCH, total_pages)
    return start_page, end_page


class ProcessDocumentUseCase:
    def __init__(self, repo: DocumentRepository) -> None:
        self._repo = repo

    def execute(self, document_id: str) -> None:
        document = self._repo.get_by_id(document_id)
        if document is None:
            return

        if document.status in (DocumentStatus.COMPLETED.value, DocumentStatus.FAILED.value):
            return

        if not settings.openai_api_key:
            self._fail_document(document, "OPENAI_API_KEY is not configured")
            return

        if not Path(document.file_path).is_file():
            self._fail_document(document, "Stored PDF file not found")
            return

        try:
            document.status = DocumentStatus.EXTRACTING.value
            document.current_batch = 0
            document.error_message = None
            document.failed_at_page = None
            document.summary = None
            document.completed_at = None
            self._repo.commit()

            chunks: list[str] = []
            for batch_num in range(1, document.total_batches + 1):
                start_page, end_page = page_range_for_batch(batch_num, document.total_pages)
                try:
                    images = rasterize_batch(document.file_path, batch_num, document.total_pages)
                    markdown = openai_service.extract_batch(images, start_page, end_page)
                except openai_service.OpenAIServiceError as exc:
                    self._fail_document(
                        document,
                        f"Failed on pages {start_page}–{end_page}: {exc}",
                        failed_at_page=start_page,
                    )
                    return
                except Exception as exc:
                    logger.exception("Batch %s failed for document %s", batch_num, document_id)
                    self._fail_document(
                        document,
                        f"Failed on pages {start_page}–{end_page}: {exc}",
                        failed_at_page=start_page,
                    )
                    return

                chunks.append(markdown)
                document.current_batch = batch_num
                self._repo.commit()

            document.status = DocumentStatus.SUMMARIZING.value
            self._repo.commit()

            full_text = "\n\n".join(chunks)
            try:
                summary = openai_service.summarize(full_text)
            except openai_service.ContextLimitError as exc:
                self._fail_document(document, str(exc))
                return
            except openai_service.OpenAIServiceError as exc:
                self._fail_document(document, f"Summary generation failed: {exc}")
                return
            except Exception as exc:
                logger.exception("Summary failed for document %s", document_id)
                self._fail_document(document, f"Summary generation failed: {exc}")
                return

            document.summary = summary
            document.status = DocumentStatus.COMPLETED.value
            document.completed_at = datetime.now(timezone.utc)
            self._repo.commit()

        except Exception as exc:
            logger.exception("Pipeline failed for document %s", document_id)
            self._repo.rollback()
            document = self._repo.get_by_id(document_id)
            if document is not None:
                self._fail_document(document, f"Processing failed: {exc}")

    def _fail_document(
        self,
        document: Document,
        message: str,
        *,
        failed_at_page: int | None = None,
    ) -> None:
        document.status = DocumentStatus.FAILED.value
        document.error_message = message
        document.failed_at_page = failed_at_page
        self._repo.commit()
