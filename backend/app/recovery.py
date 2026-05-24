from app import db as db_module
from app.repositories.document import DocumentRepository
from app.tasks.document import process_document_task


def recover_stuck_jobs() -> None:
    if db_module.SessionLocal is None:
        return

    with db_module.SessionLocal() as session:
        document_ids = DocumentRepository(session).list_non_terminal_ids()

    for document_id in document_ids:
        process_document_task.delay(document_id)
