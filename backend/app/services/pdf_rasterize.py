import fitz

DPI = 150
JPEG_QUALITY = 85
PAGES_PER_BATCH = 3


def rasterize_batch(file_path: str, batch_index: int, total_pages: int) -> list[bytes]:
    """Rasterize pages for a 1-based batch index. Returns JPEG bytes per page."""
    start_page = (batch_index - 1) * PAGES_PER_BATCH
    end_page = min(batch_index * PAGES_PER_BATCH, total_pages)

    images: list[bytes] = []
    doc = fitz.open(file_path)
    try:
        for page_num in range(start_page, end_page):
            page = doc.load_page(page_num)
            pixmap = page.get_pixmap(dpi=DPI)
            images.append(pixmap.tobytes("jpeg", jpg_quality=JPEG_QUALITY))
    finally:
        doc.close()

    return images
