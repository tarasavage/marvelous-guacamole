from typing import Annotated

from fastapi import Depends
from sqlalchemy.orm import Session

from app.config import Settings, settings
from app.db import get_db
from app.repositories.document import DocumentRepository
from app.use_cases.get_document import GetDocumentUseCase
from app.use_cases.get_job import GetJobUseCase
from app.use_cases.list_documents import ListDocumentsUseCase
from app.use_cases.upload_document import UploadDocumentUseCase

DbSession = Annotated[Session, Depends(get_db)]


def get_settings() -> Settings:
    return settings


def get_document_repository(db: DbSession) -> DocumentRepository:
    return DocumentRepository(db)


DocumentRepositoryDep = Annotated[DocumentRepository, Depends(get_document_repository)]
SettingsDep = Annotated[Settings, Depends(get_settings)]


def get_get_job_use_case(repo: DocumentRepositoryDep) -> GetJobUseCase:
    return GetJobUseCase(repo)


def get_list_documents_use_case(repo: DocumentRepositoryDep) -> ListDocumentsUseCase:
    return ListDocumentsUseCase(repo)


def get_get_document_use_case(repo: DocumentRepositoryDep) -> GetDocumentUseCase:
    return GetDocumentUseCase(repo)


def get_upload_document_use_case(
    repo: DocumentRepositoryDep,
    app_settings: SettingsDep,
) -> UploadDocumentUseCase:
    from app.tasks.document import process_document_task

    return UploadDocumentUseCase(
        repo=repo,
        data_dir=app_settings.data_dir,
        enqueue=process_document_task.delay,
    )


GetJobUseCaseDep = Annotated[GetJobUseCase, Depends(get_get_job_use_case)]
ListDocumentsUseCaseDep = Annotated[ListDocumentsUseCase, Depends(get_list_documents_use_case)]
GetDocumentUseCaseDep = Annotated[GetDocumentUseCase, Depends(get_get_document_use_case)]
UploadDocumentUseCaseDep = Annotated[UploadDocumentUseCase, Depends(get_upload_document_use_case)]
