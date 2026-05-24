import logging
from datetime import datetime, timezone
from pathlib import Path

from app.celery_app import celery_app
from app.config import settings
from app import db as db_module
from app.db import init_db
from app.models.document import Document, DocumentStatus
from app.services import openai as openai_service
from app.services.pdf_rasterize import PAGES_PER_BATCH, rasterize_batch

logger = logging.getLogger(__name__)


def _page_range_for_batch(batch_index: int, total_pages: int) -> tuple[int, int]:
    start_page = (batch_index - 1) * PAGES_PER_BATCH + 1
    end_page = min(batch_index * PAGES_PER_BATCH, total_pages)
    return start_page, end_page


def _fail_document(
    session,
    doc: Document,
    message: str,
    *,
    failed_at_page: int | None = None,
) -> None:
    doc.status = DocumentStatus.FAILED.value
    doc.error_message = message
    doc.failed_at_page = failed_at_page
    session.commit()


@celery_app.task(name="process_document")
def process_document_task(document_id: str) -> None:
    if db_module.SessionLocal is None:
        init_db(settings.data_dir)

    with db_module.SessionLocal() as session:
        doc = session.get(Document, document_id)
        if doc is None:
            return

        if doc.status in (DocumentStatus.COMPLETED.value, DocumentStatus.FAILED.value):
            return

        if not settings.openai_api_key:
            _fail_document(session, doc, "OPENAI_API_KEY is not configured")
            return

        if not Path(doc.file_path).is_file():
            _fail_document(session, doc, "Stored PDF file not found")
            return

        try:
            doc.status = DocumentStatus.EXTRACTING.value
            doc.current_batch = 0
            doc.error_message = None
            doc.failed_at_page = None
            doc.summary = None
            doc.completed_at = None
            session.commit()

            chunks: list[str] = []
            for batch_num in range(1, doc.total_batches + 1):
                start_page, end_page = _page_range_for_batch(batch_num, doc.total_pages)
                try:
                    images = rasterize_batch(doc.file_path, batch_num, doc.total_pages)
                    markdown = openai_service.extract_batch(images, start_page, end_page)
                except openai_service.OpenAIServiceError as exc:
                    _fail_document(
                        session,
                        doc,
                        f"Failed on pages {start_page}–{end_page}: {exc}",
                        failed_at_page=start_page,
                    )
                    return
                except Exception as exc:
                    logger.exception("Batch %s failed for document %s", batch_num, document_id)
                    _fail_document(
                        session,
                        doc,
                        f"Failed on pages {start_page}–{end_page}: {exc}",
                        failed_at_page=start_page,
                    )
                    return

                chunks.append(markdown)
                doc.current_batch = batch_num
                session.commit()

            doc.status = DocumentStatus.SUMMARIZING.value
            session.commit()

            full_text = "\n\n".join(chunks)
            try:
                summary = openai_service.summarize(full_text)
            except openai_service.ContextLimitError as exc:
                _fail_document(session, doc, str(exc))
                return
            except openai_service.OpenAIServiceError as exc:
                _fail_document(session, doc, f"Summary generation failed: {exc}")
                return
            except Exception as exc:
                logger.exception("Summary failed for document %s", document_id)
                _fail_document(session, doc, f"Summary generation failed: {exc}")
                return

            doc.summary = summary
            doc.status = DocumentStatus.COMPLETED.value
            doc.completed_at = datetime.now(timezone.utc)
            session.commit()

        except Exception as exc:
            logger.exception("Pipeline failed for document %s", document_id)
            session.rollback()
            doc = session.get(Document, document_id)
            if doc is not None:
                _fail_document(session, doc, f"Processing failed: {exc}")
