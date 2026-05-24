from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import select

from app.config import settings
from app import db as db_module
from app.db import init_db
from app.models.document import NON_TERMINAL_STATUSES, Document
from app.routers import documents, root
from app.tasks.document import process_document_task


def recover_stuck_jobs() -> None:
    if db_module.SessionLocal is None:
        return

    with db_module.SessionLocal() as db:
        document_ids = db.scalars(
            select(Document.id).where(Document.status.in_([s.value for s in NON_TERMINAL_STATUSES]))
        ).all()

    for document_id in document_ids:
        process_document_task.delay(document_id)


@asynccontextmanager
async def lifespan(_app: FastAPI):
    init_db(settings.data_dir)
    recover_stuck_jobs()
    yield


app = FastAPI(title="PDF Summary AI", version="0.2.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(root.router)
app.include_router(documents.router, prefix="/api")
