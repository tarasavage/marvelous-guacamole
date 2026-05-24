import tempfile
from collections.abc import Generator
from pathlib import Path
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

from app import db as db_module
from app.config import settings
from app.db import get_db, init_db
from app.main import app


@pytest.fixture()
def data_dir(tmp_path: Path) -> Path:
    path = tmp_path / "data"
    path.mkdir()
    return path


@pytest.fixture()
def document_repo(data_dir: Path):
    init_db(str(data_dir))
    assert db_module.SessionLocal is not None
    session = db_module.SessionLocal()
    from app.repositories.document import DocumentRepository

    repo = DocumentRepository(session)
    try:
        yield repo
    finally:
        session.close()


@pytest.fixture()
def client(data_dir: Path, monkeypatch: pytest.MonkeyPatch) -> Generator[TestClient, None, None]:
    monkeypatch.setattr(settings, "data_dir", str(data_dir))
    init_db(str(data_dir))
    enqueue = MagicMock()
    monkeypatch.setattr("app.tasks.document.process_document_task.delay", enqueue)

    def override_get_db() -> Generator:
        assert db_module.SessionLocal is not None
        session = db_module.SessionLocal()
        try:
            yield session
        finally:
            session.close()

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
