from app.mappers.document import to_list_response
from app.repositories.document import DocumentRepository
from app.schemas.document import DocumentListResponse


class ListDocumentsUseCase:
    def __init__(self, repo: DocumentRepository) -> None:
        self._repo = repo

    def execute(self, limit: int = 5) -> DocumentListResponse:
        documents = self._repo.list_completed(limit=limit)
        return to_list_response(documents)
