"""Celery tasks for notification processing.

Validates: Requirements 31.4, 32.5
"""

import asyncio
import logging
from datetime import datetime, timezone
from typing import Optional
from uuid import UUID

from app.tasks import celery_app

logger = logging.getLogger(__name__)


def run_async(coro):
    """Helper to run async code in sync context."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


@celery_app.task(
    name="app.tasks.notification_tasks.send_scheduled_notification",
    bind=True,
    max_retries=3,
    default_retry_delay=60,
)
def send_scheduled_notification(
    self,
    notification_id: str,
) -> dict:
    """Send a scheduled notification at its scheduled time.
    
    Validates: Requirements 32.5
    
    Args:
        notification_id: UUID of the notification to send
        
    Returns:
        Dict with success status and details
    """
    async def _send():
        from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
        from sqlalchemy.orm import sessionmaker
        
        from app.core.config import get_settings
        from app.models.notification import NotificationStatus
        from app.repositories.notification import NotificationRepository
        from app.services.notification import NotificationService
        
        settings = get_settings()
        engine = create_async_engine(str(settings.database_url))
        async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
        
        async with async_session() as db:
            try:
                repo = NotificationRepository(db)
                notification = await repo.get_notification_by_id(UUID(notification_id))
                
                if notification is None:
                    logger.error(f"Notification {notification_id} not found")
                    return {"success": False, "error": "Notification not found"}
                
                # Check if notification is still pending/scheduled
                if notification.status not in [NotificationStatus.PENDING, NotificationStatus.QUEUED]:
                    logger.info(f"Notification {notification_id} already processed (status: {notification.status})")
                    return {"success": True, "message": "Already processed"}
                
                # Send the notification
                service = NotificationService(db)
                result = await service.send_notification(
                    user_id=notification.user_id,
                    title=notification.title,
                    body=notification.body,
                    channel=notification.channel,
                )
                
                await db.commit()
                
                return {
                    "success": result.success,
                    "notification_id": str(result.notification_id) if result.notification_id else None,
                    "channel_used": result.channel_used.value if result.channel_used else None,
                    "error": result.error,
                }
                
            except Exception as e:
                logger.exception(f"Error sending scheduled notification {notification_id}: {e}")
                await db.rollback()
                raise self.retry(exc=e)
    
    return run_async(_send())


@celery_app.task(
    name="app.tasks.notification_tasks.process_queued_notifications",
    bind=True,
    max_retries=3,
    default_retry_delay=60,
)
def process_queued_notifications(
    self,
    user_id: str,
) -> dict:
    """Process notifications queued during quiet hours for a specific user.
    
    Validates: Requirements 31.4
    
    Args:
        user_id: UUID of the user whose queued notifications to process
        
    Returns:
        Dict with success status and count of processed notifications
    """
    async def _process():
        from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
        from sqlalchemy.orm import sessionmaker
        
        from app.core.config import get_settings
        from app.services.notification import NotificationService
        
        settings = get_settings()
        engine = create_async_engine(str(settings.database_url))
        async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
        
        async with async_session() as db:
            try:
                service = NotificationService(db)
                results = await service.process_queued_notifications(UUID(user_id))
                
                await db.commit()
                
                successful = sum(1 for r in results if r.success)
                failed = len(results) - successful
                
                return {
                    "success": True,
                    "user_id": user_id,
                    "total_processed": len(results),
                    "successful": successful,
                    "failed": failed,
                }
                
            except Exception as e:
                logger.exception(f"Error processing queued notifications for user {user_id}: {e}")
                await db.rollback()
                raise self.retry(exc=e)
    
    return run_async(_process())


@celery_app.task(
    name="app.tasks.notification_tasks.send_notification_batch",
    bind=True,
    max_retries=3,
    default_retry_delay=60,
)
def send_notification_batch(
    self,
    user_id: str,
    notifications: list[dict],
) -> dict:
    """Send batched notifications to a user.
    
    Validates: Requirements 31.6
    
    Args:
        user_id: UUID of the target user
        notifications: List of notification dicts with title, body, channel
        
    Returns:
        Dict with success status and details
    """
    async def _send_batch():
        from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
        from sqlalchemy.orm import sessionmaker
        
        from app.core.config import get_settings
        from app.models.notification import NotificationChannel
        from app.services.notification import NotificationService
        
        settings = get_settings()
        engine = create_async_engine(str(settings.database_url))
        async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
        
        async with async_session() as db:
            try:
                service = NotificationService(db)
                
                # Convert dict notifications to tuples
                notification_tuples = [
                    (n["title"], n["body"], NotificationChannel(n["channel"]))
                    for n in notifications
                ]
                
                result = await service.batch_notifications(
                    UUID(user_id),
                    notification_tuples,
                )
                
                await db.commit()
                
                return {
                    "success": result.success,
                    "notification_id": str(result.notification_id) if result.notification_id else None,
                    "channel_used": result.channel_used.value if result.channel_used else None,
                    "batch_size": len(notifications),
                    "error": result.error,
                }
                
            except Exception as e:
                logger.exception(f"Error sending notification batch to user {user_id}: {e}")
                await db.rollback()
                raise self.retry(exc=e)
    
    return run_async(_send_batch())


@celery_app.task(
    name="app.tasks.notification_tasks.process_all_queued_notifications",
)
def process_all_queued_notifications() -> dict:
    """Periodic task to process all queued notifications for users outside quiet hours.
    
    Validates: Requirements 31.4
    
    Returns:
        Dict with success status and count of users processed
    """
    async def _process_all():
        from sqlalchemy import select
        from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
        from sqlalchemy.orm import sessionmaker
        
        from app.core.config import get_settings
        from app.models.notification import Notification, NotificationStatus
        from app.services.notification import NotificationService
        
        settings = get_settings()
        engine = create_async_engine(str(settings.database_url))
        async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
        
        async with async_session() as db:
            try:
                # Get distinct user IDs with queued notifications
                stmt = (
                    select(Notification.user_id)
                    .where(Notification.status == NotificationStatus.QUEUED)
                    .distinct()
                )
                result = await db.execute(stmt)
                user_ids = [row[0] for row in result.fetchall()]
                
                processed_users = 0
                total_notifications = 0
                
                for user_id in user_ids:
                    service = NotificationService(db)
                    
                    # Check if user is still in quiet hours
                    if not await service.is_in_quiet_hours(user_id):
                        results = await service.process_queued_notifications(user_id)
                        processed_users += 1
                        total_notifications += len(results)
                
                await db.commit()
                
                return {
                    "success": True,
                    "users_processed": processed_users,
                    "notifications_processed": total_notifications,
                }
                
            except Exception as e:
                logger.exception(f"Error processing all queued notifications: {e}")
                await db.rollback()
                return {"success": False, "error": str(e)}
    
    return run_async(_process_all())


@celery_app.task(
    name="app.tasks.notification_tasks.send_due_scheduled_notifications",
)
def send_due_scheduled_notifications() -> dict:
    """Periodic task to send notifications that are due (scheduled_at <= now).
    
    Validates: Requirements 32.5
    
    Returns:
        Dict with success status and count of notifications sent
    """
    async def _send_due():
        from sqlalchemy import select
        from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
        from sqlalchemy.orm import sessionmaker
        
        from app.core.config import get_settings
        from app.models.notification import Notification, NotificationStatus
        from app.services.notification import NotificationService
        
        settings = get_settings()
        engine = create_async_engine(str(settings.database_url))
        async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
        
        async with async_session() as db:
            try:
                now = datetime.now(timezone.utc)
                
                # Get notifications that are due
                stmt = (
                    select(Notification)
                    .where(
                        Notification.status == NotificationStatus.PENDING,
                        Notification.scheduled_at.isnot(None),
                        Notification.scheduled_at <= now,
                    )
                    .limit(100)  # Process in batches
                )
                result = await db.execute(stmt)
                notifications = list(result.scalars().all())
                
                sent_count = 0
                failed_count = 0
                
                for notification in notifications:
                    service = NotificationService(db)
                    send_result = await service.send_notification(
                        user_id=notification.user_id,
                        title=notification.title,
                        body=notification.body,
                        channel=notification.channel,
                    )
                    
                    if send_result.success:
                        sent_count += 1
                    else:
                        failed_count += 1
                
                await db.commit()
                
                return {
                    "success": True,
                    "notifications_sent": sent_count,
                    "notifications_failed": failed_count,
                }
                
            except Exception as e:
                logger.exception(f"Error sending due scheduled notifications: {e}")
                await db.rollback()
                return {"success": False, "error": str(e)}
    
    return run_async(_send_due())
