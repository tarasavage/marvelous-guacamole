class DocumentNotFoundError(Exception):
    pass


class UploadValidationError(Exception):
    pass


class UploadPersistenceError(Exception):
    pass


class EnqueueError(UploadPersistenceError):
    pass
