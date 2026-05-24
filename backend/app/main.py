from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.db import init_db
from app.logging_config import configure_logging
from app.recovery import recover_stuck_jobs
from app.routers import documents, root


@asynccontextmanager
async def lifespan(_app: FastAPI):
    configure_logging(settings.log_level)
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
