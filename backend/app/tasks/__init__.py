"""Celery app configuration for async task processing.

Validates: Requirements 32.5, 36.6
"""

from celery import Celery

from app.core.config import get_settings

settings = get_settings()

# Create Celery app
celery_app = Celery(
    "lifepilot",
    broker=str(settings.redis_url),
    backend=str(settings.redis_url),
    include=[
        "app.tasks.notification_tasks",
        "app.tasks.ocr_tasks",
        "app.tasks.document_expiry_tasks",
        "app.tasks.budget_tasks",
        "app.tasks.medicine_tasks",
        "app.tasks.exam_tasks",
        "app.tasks.weekly_summary_tasks",
        "app.tasks.account_tasks",
        "app.tasks.admin_alerting_tasks",
    ],
)

# Celery configuration
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=300,  # 5 minutes max per task
    task_soft_time_limit=240,  # 4 minutes soft limit
    worker_prefetch_multiplier=1,
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    result_expires=3600,  # Results expire after 1 hour
)

# Beat schedule for periodic tasks
celery_app.conf.beat_schedule = {
    "process-queued-notifications-every-5-minutes": {
        "task": "app.tasks.notification_tasks.process_all_queued_notifications",
        "schedule": 300.0,  # Every 5 minutes
    },
    "send-scheduled-notifications-every-minute": {
        "task": "app.tasks.notification_tasks.send_due_scheduled_notifications",
        "schedule": 60.0,  # Every minute
    },
    "reprocess-failed-ocr-documents-hourly": {
        "task": "app.tasks.ocr_tasks.reprocess_failed_documents",
        "schedule": 3600.0,  # Every hour
    },
    "check-document-expiry-daily": {
        "task": "app.tasks.document_expiry_tasks.check_document_expiry",
        "schedule": 86400.0,  # Every 24 hours (daily)
    },
    "archive-expired-budgets-daily": {
        "task": "app.tasks.budget_tasks.archive_expired_budgets",
        "schedule": 86400.0,  # Every 24 hours (daily)
    },
    # Medicine tracking tasks
    "process-dose-reminders-every-minute": {
        "task": "app.tasks.medicine_tasks.process_pending_dose_reminders",
        "schedule": 60.0,  # Every minute
    },
    "process-missed-doses-every-5-minutes": {
        "task": "app.tasks.medicine_tasks.process_missed_doses",
        "schedule": 300.0,  # Every 5 minutes
    },
    "process-refill-alerts-daily": {
        "task": "app.tasks.medicine_tasks.process_refill_alerts",
        "schedule": 86400.0,  # Every 24 hours (daily)
    },
    "schedule-daily-doses": {
        "task": "app.tasks.medicine_tasks.schedule_daily_doses",
        "schedule": 86400.0,  # Every 24 hours (daily)
    },
    # Exam deadline reminder task
    "check-exam-deadline-reminders-daily": {
        "task": "app.tasks.exam_tasks.check_exam_deadline_reminders",
        "schedule": 86400.0,  # Every 24 hours (daily)
    },
    # Exam data scraping tasks - Validates: Requirements 5.1
    "scrape-all-exam-sources-daily": {
        "task": "app.tasks.exam_tasks.run_all_exam_scrapers",
        "schedule": 86400.0,  # Every 24 hours (daily)
    },
    # Individual scraper tasks for more granular control
    "scrape-tcs-exams-daily": {
        "task": "app.tasks.exam_tasks.scrape_tcs_exams",
        "schedule": 86400.0,  # Every 24 hours (daily)
    },
    "scrape-infosys-exams-daily": {
        "task": "app.tasks.exam_tasks.scrape_infosys_exams",
        "schedule": 86400.0,  # Every 24 hours (daily)
    },
    "scrape-gate-exams-weekly": {
        "task": "app.tasks.exam_tasks.scrape_gate_exams",
        "schedule": 604800.0,  # Every 7 days (weekly) - GATE updates less frequently
    },
    "scrape-upsc-exams-weekly": {
        "task": "app.tasks.exam_tasks.scrape_upsc_exams",
        "schedule": 604800.0,  # Every 7 days (weekly) - UPSC updates less frequently
    },
    "scrape-naukri-exams-twice-daily": {
        "task": "app.tasks.exam_tasks.scrape_naukri_exams",
        "schedule": 43200.0,  # Every 12 hours (twice daily) - Job portals update frequently
    },
    "scrape-linkedin-exams-twice-daily": {
        "task": "app.tasks.exam_tasks.scrape_linkedin_exams",
        "schedule": 43200.0,  # Every 12 hours (twice daily) - Job portals update frequently
    },
    # Weekly summary generation - Validates: Requirements 34.1
    "generate-weekly-summaries-monday": {
        "task": "generate_all_weekly_summaries",
        "schedule": {
            "crontab": {
                "hour": 8,
                "minute": 0,
                "day_of_week": 1,  # Monday
            }
        },
        "args": (None, True),  # week_start=None (last completed week), send_notifications=True
    },
    # Weekly summary cleanup - remove summaries older than 1 year
    "cleanup-old-weekly-summaries-monthly": {
        "task": "cleanup_old_weekly_summaries",
        "schedule": 2592000.0,  # Every 30 days (monthly)
        "args": (52,),  # retention_weeks=52 (1 year)
    },
    # Account deletion tasks - Validates: Requirements 36.6
    "process-scheduled-account-deletions-daily": {
        "task": "app.tasks.account_tasks.process_scheduled_deletions",
        "schedule": 86400.0,  # Every 24 hours (daily)
    },
    # Admin alerting tasks - Validates: Requirements 38.5
    "check-error-rates-every-5-minutes": {
        "task": "app.tasks.admin_alerting_tasks.check_error_rates",
        "schedule": 300.0,  # Every 5 minutes
    },
}
