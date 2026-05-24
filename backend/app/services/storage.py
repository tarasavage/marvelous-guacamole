import re
import uuid
from pathlib import Path

_FILENAME_SAFE = re.compile(r"[^a-zA-Z0-9._-]")


def sanitize_filename(filename: str) -> str:
    name = Path(filename).name
    if "\x00" in name or "/" in name or "\\" in name:
        name = Path(name).name.replace("\x00", "")
    sanitized = _FILENAME_SAFE.sub("_", name).strip("._")
    if not sanitized:
        sanitized = "document.pdf"
    return sanitized[:200]


def uploads_dir(data_dir: str) -> Path:
    path = Path(data_dir) / "uploads"
    path.mkdir(parents=True, exist_ok=True)
    return path


def save_pdf(data: bytes, data_dir: str) -> tuple[str, Path]:
    document_id = str(uuid.uuid4())
    dest = uploads_dir(data_dir) / f"{document_id}.pdf"
    temp = dest.with_suffix(".pdf.tmp")
    temp.write_bytes(data)
    temp.rename(dest)
    return document_id, dest


def delete_pdf(path: Path) -> None:
    try:
        path.unlink(missing_ok=True)
    except OSError:
        pass
