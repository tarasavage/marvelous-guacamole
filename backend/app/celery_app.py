from celery import Celery
from celery.signals import worker_process_init

from app.config import settings

celery_app = Celery("pdf_summary", broker=settings.redis_url, include=["app.tasks.document"])

celery_app.conf.update(
    task_ignore_result=True,
    worker_prefetch_multiplier=1,
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
)


@worker_process_init.connect
def init_worker_db(**_kwargs) -> None:
    from app.db import init_db

    init_db(settings.data_dir)
