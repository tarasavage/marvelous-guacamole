import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class DocumentStatus(str, enum.Enum):
    PENDING = "pending"
    QUEUED = "queued"
    EXTRACTING = "extracting"
    SUMMARIZING = "summarizing"
    COMPLETED = "completed"
    FAILED = "failed"


STAGE_LABELS: dict[DocumentStatus, str] = {
    DocumentStatus.PENDING: "Pending",
    DocumentStatus.QUEUED: "Queued",
    DocumentStatus.EXTRACTING: "Extracting",
    DocumentStatus.SUMMARIZING: "Summarizing",
    DocumentStatus.COMPLETED: "Done",
    DocumentStatus.FAILED: "Failed",
}

NON_TERMINAL_STATUSES = (
    DocumentStatus.PENDING,
    DocumentStatus.QUEUED,
    DocumentStatus.EXTRACTING,
    DocumentStatus.SUMMARIZING,
)


class Document(Base):
    __tablename__ = "documents"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    original_filename: Mapped[str] = mapped_column(String(200))
    file_path: Mapped[str] = mapped_column(String(512))
    status: Mapped[str] = mapped_column(String(32), default=DocumentStatus.PENDING.value)
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    failed_at_page: Mapped[int | None] = mapped_column(Integer, nullable=True)
    current_batch: Mapped[int] = mapped_column(Integer, default=0)
    total_batches: Mapped[int] = mapped_column(Integer, default=0)
    total_pages: Mapped[int] = mapped_column(Integer, default=0)
    uploaded_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    @property
    def status_enum(self) -> DocumentStatus:
        return DocumentStatus(self.status)

    @property
    def stage(self) -> str:
        return STAGE_LABELS.get(self.status_enum, self.status)
