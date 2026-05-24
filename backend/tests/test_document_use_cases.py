import io
from unittest.mock import Mock

import fitz
import pytest

from app.exceptions import DocumentNotFoundError, UploadValidationError
from app.models.document import Document, DocumentStatus
from app.use_cases.get_document import GetDocumentUseCase
from app.use_cases.get_job import GetJobUseCase
from app.use_cases.list_documents import ListDocumentsUseCase
from app.use_cases.upload_document import UploadDocumentUseCase


def _minimal_pdf_bytes() -> bytes:
    document = fitz.open()
    document.new_page()
    payload = document.tobytes()
    document.close()
    return payload


def test_get_job_returns_progress(document_repo) -> None:
    document = Document(
        id="doc-1",
        original_filename="sample.pdf",
        file_path="/tmp/sample.pdf",
        status=DocumentStatus.EXTRACTING.value,
        total_pages=6,
        total_batches=2,
        current_batch=1,
    )
    document_repo.add(document)
    document_repo.commit()

    response = GetJobUseCase(document_repo).execute("doc-1")

    assert response.status == DocumentStatus.EXTRACTING.value
    assert response.progress.pages_processed == 3
    assert response.progress.total_pages == 6


def test_get_job_missing_document_raises(document_repo) -> None:
    with pytest.raises(DocumentNotFoundError):
        GetJobUseCase(document_repo).execute("missing")


def test_list_documents_returns_completed_only(document_repo) -> None:
    completed = Document(
        id="done-1",
        original_filename="done.pdf",
        file_path="/tmp/done.pdf",
        status=DocumentStatus.COMPLETED.value,
        summary="Done",
    )
    pending = Document(
        id="pending-1",
        original_filename="pending.pdf",
        file_path="/tmp/pending.pdf",
        status=DocumentStatus.PENDING.value,
    )
    document_repo.add(completed)
    document_repo.add(pending)
    document_repo.commit()

    response = ListDocumentsUseCase(document_repo).execute()

    assert len(response.items) == 1
    assert response.items[0].id == "done-1"


def test_get_document_missing_raises(document_repo) -> None:
    with pytest.raises(DocumentNotFoundError):
        GetDocumentUseCase(document_repo).execute("missing")


def test_upload_document_validates_missing_filename(document_repo, data_dir) -> None:
    use_case = UploadDocumentUseCase(
        repo=document_repo,
        data_dir=str(data_dir),
        enqueue=lambda _document_id: None,
    )

    with pytest.raises(UploadValidationError, match="Missing file"):
        use_case.execute("", _minimal_pdf_bytes())


def test_upload_document_enqueues_and_marks_queued(document_repo, data_dir) -> None:
    enqueue = Mock()
    use_case = UploadDocumentUseCase(
        repo=document_repo,
        data_dir=str(data_dir),
        enqueue=enqueue,
    )

    response = use_case.execute("sample.pdf", _minimal_pdf_bytes())

    enqueue.assert_called_once_with(response.document_id)
    stored = document_repo.get_by_id(response.document_id)
    assert stored is not None
    assert stored.status == DocumentStatus.QUEUED.value


def test_upload_document_rolls_back_on_enqueue_failure(document_repo, data_dir) -> None:
    def failing_enqueue(_document_id: str) -> None:
        raise RuntimeError("broker down")

    use_case = UploadDocumentUseCase(
        repo=document_repo,
        data_dir=str(data_dir),
        enqueue=failing_enqueue,
    )

    with pytest.raises(Exception, match="Failed to enqueue"):
        use_case.execute("sample.pdf", _minimal_pdf_bytes())

    assert document_repo.list_completed(limit=100) == []
    assert not any((data_dir / "uploads").glob("*.pdf"))


def test_upload_endpoint_returns_created_document(client) -> None:
    response = client.post(
        "/api/documents",
        files={"file": ("sample.pdf", io.BytesIO(_minimal_pdf_bytes()), "application/pdf")},
    )

    assert response.status_code == 201
    body = response.json()
    assert body["job_id"] == body["document_id"]


def test_get_job_endpoint_returns_404(client) -> None:
    response = client.get("/api/jobs/missing")

    assert response.status_code == 404
