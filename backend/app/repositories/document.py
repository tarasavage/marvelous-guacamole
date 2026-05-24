from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.document import NON_TERMINAL_STATUSES, Document, DocumentStatus


class DocumentRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    @property
    def session(self) -> Session:
        return self._session

    def get_by_id(self, document_id: str) -> Document | None:
        return self._session.get(Document, document_id)

    def list_completed(self, limit: int = 5) -> list[Document]:
        return list(
            self._session.scalars(
                select(Document)
                .where(Document.status == DocumentStatus.COMPLETED.value)
                .order_by(Document.completed_at.desc(), Document.uploaded_at.desc())
                .limit(limit)
            ).all()
        )

    def list_non_terminal_ids(self) -> list[str]:
        return list(
            self._session.scalars(
                select(Document.id).where(
                    Document.status.in_([status.value for status in NON_TERMINAL_STATUSES])
                )
            ).all()
        )

    def add(self, document: Document) -> Document:
        self._session.add(document)
        return document

    def delete(self, document: Document) -> None:
        self._session.delete(document)

    def commit(self) -> None:
        self._session.commit()

    def rollback(self) -> None:
        self._session.rollback()
