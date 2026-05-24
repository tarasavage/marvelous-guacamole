import fitz

MAX_FILE_SIZE_BYTES = 50 * 1024 * 1024
MAX_PAGE_COUNT = 100
PDF_MAGIC = b"%PDF"


class PDFValidationError(ValueError):
    pass


def validate_pdf_bytes(data: bytes) -> int:
    if not data:
        raise PDFValidationError("File is empty")

    if len(data) > MAX_FILE_SIZE_BYTES:
        raise PDFValidationError("PDF exceeds maximum size of 50 MB")

    if not data.startswith(PDF_MAGIC):
        raise PDFValidationError("File is not a valid PDF")

    try:
        doc = fitz.open(stream=data, filetype="pdf")
    except Exception as exc:
        raise PDFValidationError("Invalid or unreadable PDF") from exc

    try:
        page_count = doc.page_count
        if page_count == 0:
            raise PDFValidationError("PDF has no pages")
        if page_count > MAX_PAGE_COUNT:
            raise PDFValidationError(f"PDF exceeds maximum of {MAX_PAGE_COUNT} pages")
        return page_count
    finally:
        doc.close()
