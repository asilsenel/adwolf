"""
Ad Platform MVP - Celery Application

Celery configuration and app initialization.
"""

from celery import Celery
from celery.schedules import crontab

from app.core.config import settings


# Create Celery app
celery_app = Celery(
    "adplatform",
    broker=settings.redis_url,
    backend=settings.redis_url,
    include=[
        "app.tasks.sync_tasks",
        "app.tasks.insight_tasks",
    ],
)

# Celery configuration
celery_app.conf.update(
    # Task settings
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone=settings.default_timezone,
    enable_utc=True,
    
    # Task execution settings
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    
    # Result settings
    result_expires=3600,  # 1 hour
    
    # Worker settings
    worker_prefetch_multiplier=1,
    worker_concurrency=4,
    
    # Task routing
    task_routes={
        "app.tasks.sync_tasks.*": {"queue": "sync"},
        "app.tasks.insight_tasks.*": {"queue": "insights"},
    },
    
    # Beat schedule (periodic tasks)
    beat_schedule={
        # Daily sync at 6 AM Istanbul time
        "daily-sync-all-accounts": {
            "task": "app.tasks.sync_tasks.sync_all_accounts",
            "schedule": crontab(hour=6, minute=0),
            "options": {"queue": "sync"},
        },
        # Generate insights after sync (7 AM)
        "daily-generate-insights": {
            "task": "app.tasks.insight_tasks.generate_daily_insights",
            "schedule": crontab(hour=7, minute=0),
            "options": {"queue": "insights"},
        },
        # Daily digest at 9 AM
        "daily-digest": {
            "task": "app.tasks.insight_tasks.send_daily_digests",
            "schedule": crontab(hour=9, minute=0),
            "options": {"queue": "insights"},
        },
    },
)
