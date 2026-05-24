from app.exceptions import DocumentNotFoundError
from app.mappers.document import to_job_response
from app.repositories.document import DocumentRepository
from app.schemas.document import JobResponse


class GetJobUseCase:
    def __init__(self, repo: DocumentRepository) -> None:
        self._repo = repo

    def execute(self, job_id: str) -> JobResponse:
        document = self._repo.get_by_id(job_id)
        if document is None:
            raise DocumentNotFoundError
        return to_job_response(document)
