from sqlalchemy import select

from app import db as db_module
from app.models.document import NON_TERMINAL_STATUSES, Document


def recover_stuck_jobs() -> None:
    from app.tasks.document import process_document_task

    if db_module.SessionLocal is None:
        return

    with db_module.SessionLocal() as db:
        document_ids = db.scalars(
            select(Document.id).where(Document.status.in_([s.value for s in NON_TERMINAL_STATUSES]))
        ).all()

    for document_id in document_ids:
        process_document_task.delay(document_id)
