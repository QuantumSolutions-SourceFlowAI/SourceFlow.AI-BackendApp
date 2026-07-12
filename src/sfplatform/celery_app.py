from celery import Celery

from sfplatform.config import get_settings

_settings = get_settings()
celery_app = Celery("sourceflow", broker=_settings.redis_url, backend=_settings.redis_url,
                    include=["contexts.knowledge_ingestion.infrastructure.celery_tasks"])
celery_app.conf.task_always_eager = False
