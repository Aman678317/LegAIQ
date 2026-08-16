"""Celery application for background document processing."""
from celery import Celery

from app.config import get_settings

settings = get_settings()

celery_app = Celery(
    "jurisiva",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="Asia/Kolkata",
    enable_utc=True,
    task_track_started=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,  # long OCR tasks: fair dispatch
    task_time_limit=1800,          # 30 min hard cap
    task_soft_time_limit=1500,
)


@celery_app.task(bind=True, name="jobs.poll_and_dispatch")
def poll_and_dispatch(self):
    """Poll the jobs table and dispatch queued jobs to the right task.

    Render worker runs this every few seconds via beat.
    """
    from app.workers.dispatcher import dispatch_pending_jobs
    return dispatch_pending_jobs()


celery_app.conf.beat_schedule = {
    "poll-jobs": {
        "task": "jobs.poll_and_dispatch",
        "schedule": 5.0,
    },
}
