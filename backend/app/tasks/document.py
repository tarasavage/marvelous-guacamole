from app.celery_app import celery_app
from app.config import settings
from app import db as db_module
from app.db import init_db
from app.models.document import Document, DocumentStatus


@celery_app.task(name="process_document")
def process_document_task(document_id: str) -> None:
    if db_module.SessionLocal is None:
        init_db(settings.data_dir)

    with db_module.SessionLocal() as session:
        doc = session.get(Document, document_id)
        if doc is None:
            return

        if doc.status in (
            DocumentStatus.COMPLETED.value,
            DocumentStatus.FAILED.value,
            DocumentStatus.QUEUED.value,
            DocumentStatus.EXTRACTING.value,
            DocumentStatus.SUMMARIZING.value,
        ):
            return

        doc.status = DocumentStatus.QUEUED.value
        session.commit()
