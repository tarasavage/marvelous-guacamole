from app.exceptions import DocumentNotFoundError
from app.mappers.document import to_detail_response
from app.repositories.document import DocumentRepository
from app.schemas.document import DocumentDetailResponse


class GetDocumentUseCase:
    def __init__(self, repo: DocumentRepository) -> None:
        self._repo = repo

    def execute(self, document_id: str) -> DocumentDetailResponse:
        document = self._repo.get_by_id(document_id)
        if document is None:
            raise DocumentNotFoundError
        return to_detail_response(document)
