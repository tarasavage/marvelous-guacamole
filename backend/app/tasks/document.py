from app import db as db_module
from app.celery_app import celery_app
from app.config import settings
from app.db import init_db
from app.repositories.document import DocumentRepository
from app.use_cases.process_document import ProcessDocumentUseCase


@celery_app.task(name="process_document")
def process_document_task(document_id: str) -> None:
    if db_module.SessionLocal is None:
        init_db(settings.data_dir)

    with db_module.SessionLocal() as session:
        ProcessDocumentUseCase(DocumentRepository(session)).execute(document_id)
