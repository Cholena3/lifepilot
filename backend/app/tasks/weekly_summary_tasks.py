"""Celery tasks for weekly summary generation.

Requirement 34: Weekly Summary
- Generate summary of activities across all modules when a week ends
- Send via user's preferred channel
"""

import logging
from datetime import date
from typing import Optional
from uuid import UUID

from celery import shared_task

from app.core.database import async_session_maker
from app.repositories.weekly_summary import WeeklySummaryRepository
from app.services.weekly_summary import WeeklySummaryService, get_last_completed_week

logger = logging.getLogger(__name__)


@shared_task(
    name="generate_weekly_summary",
    bind=True,
    max_retries=3,
    default_retry_delay=300,  # 5 minutes
)
def generate_weekly_summary_task(
    self,
    user_id: str,
    week_start: Optional[str] = None,
    send_notification: bool = True,
) -> dict:
    """Generate weekly summary for a single user.
    
    Validates: Requirements 34.1, 34.4
    
    Args:
        user_id: User's UUID as string
        week_start: Optional week start date (YYYY-MM-DD). Defaults to last completed week.
        send_notification: Whether to send notification after generation
        
    Returns:
        Dict with summary_id and notification_sent status
    """
    import asyncio
    
    async def _generate():
        async with async_session_maker() as session:
            try:
                service = WeeklySummaryService(session)
                
                # Parse week_start if provided
                parsed_week_start = None
                if week_start:
                    parsed_week_start = date.fromisoformat(week_start)
                
                user_uuid = UUID(user_id)
                
                if send_notification:
                    summary, notification_sent = await service.generate_and_send_summary(
                        user_uuid, parsed_week_start
                    )
                else:
                    summary = await service.generate_weekly_summary(
                        user_uuid, parsed_week_start
                    )
                    notification_sent = False
                
                await session.commit()
                
                logger.info(
                    f"Generated weekly summary {summary.id} for user {user_id}, "
                    f"notification_sent={notification_sent}"
                )
                
                return {
                    "summary_id": str(summary.id),
                    "user_id": user_id,
                    "week_start": str(summary.week_start),
                    "week_end": str(summary.week_end),
                    "notification_sent": notification_sent,
                    "total_activities": summary.metrics.get("total_activities", 0),
                }
                
            except Exception as e:
                await session.rollback()
                logger.exception(f"Error generating weekly summary for user {user_id}: {e}")
                raise self.retry(exc=e)
    
    return asyncio.run(_generate())


@shared_task(
    name="generate_all_weekly_summaries",
    bind=True,
)
def generate_all_weekly_summaries_task(
    self,
    week_start: Optional[str] = None,
    send_notifications: bool = True,
) -> dict:
    """Generate weekly summaries for all users.
    
    Validates: Requirements 34.1
    
    This task is typically scheduled to run every Monday morning
    to generate summaries for the previous week.
    
    Args:
        week_start: Optional week start date (YYYY-MM-DD). Defaults to last completed week.
        send_notifications: Whether to send notifications after generation
        
    Returns:
        Dict with count of summaries generated and any errors
    """
    import asyncio
    
    async def _generate_all():
        async with async_session_maker() as session:
            try:
                repo = WeeklySummaryRepository(session)
                
                # Get all user IDs
                user_ids = await repo.get_all_user_ids_with_activity()
                
                logger.info(f"Generating weekly summaries for {len(user_ids)} users")
                
                # Queue individual tasks for each user
                for user_id in user_ids:
                    generate_weekly_summary_task.delay(
                        str(user_id),
                        week_start,
                        send_notifications,
                    )
                
                return {
                    "users_queued": len(user_ids),
                    "week_start": week_start or str(get_last_completed_week()[0]),
                }
                
            except Exception as e:
                logger.exception(f"Error queuing weekly summary generation: {e}")
                raise
    
    return asyncio.run(_generate_all())


@shared_task(
    name="cleanup_old_weekly_summaries",
    bind=True,
)
def cleanup_old_weekly_summaries_task(
    self,
    retention_weeks: int = 52,
) -> dict:
    """Clean up weekly summaries older than retention period.
    
    Args:
        retention_weeks: Number of weeks to retain summaries (default: 52 weeks / 1 year)
        
    Returns:
        Dict with count of deleted summaries
    """
    import asyncio
    from datetime import timedelta
    from sqlalchemy import delete, and_
    
    async def _cleanup():
        async with async_session_maker() as session:
            try:
                from app.models.weekly_summary import WeeklySummary
                
                cutoff_date = date.today() - timedelta(weeks=retention_weeks)
                
                stmt = delete(WeeklySummary).where(
                    WeeklySummary.week_end < cutoff_date
                )
                result = await session.execute(stmt)
                await session.commit()
                
                deleted_count = result.rowcount
                logger.info(
                    f"Cleaned up {deleted_count} weekly summaries older than {cutoff_date}"
                )
                
                return {
                    "deleted_count": deleted_count,
                    "cutoff_date": str(cutoff_date),
                }
                
            except Exception as e:
                await session.rollback()
                logger.exception(f"Error cleaning up old weekly summaries: {e}")
                raise
    
    return asyncio.run(_cleanup())
