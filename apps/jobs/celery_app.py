"""
Celery app for QERS: Redis broker, sim task queue.
"""

from celery import Celery
import os

REDIS_URL = os.environ.get("REDIS_URL", "redis://localhost:6379/0")

app = Celery(
    "qers",
    broker=REDIS_URL,
    backend=REDIS_URL,
    include=["apps.jobs.tasks"],
)
app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    task_track_started=True,
    task_time_limit=3600,  # 1 hour max per sim
    worker_prefetch_multiplier=1,  # one task at a time per worker
)
