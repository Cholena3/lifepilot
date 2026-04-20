"""Celery tasks for account management.

Validates: Requirements 36.6
"""

import asyncio
import logging
from datetime import datetime, timezone
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
    name="app.tasks.account_tasks.process_scheduled_deletions",
)
def process_scheduled_deletions() -> dict:
    """Process all accounts scheduled for deletion.
    
    Validates: Requirements 36.6
    
    This task runs daily to find and permanently delete accounts
    whose 30-day grace period has expired.
    
    Returns:
        Dict with success status and count of deleted accounts
    """
    async def _process():
        from sqlalchemy import select
        from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
        from sqlalchemy.orm import sessionmaker
        
        from app.core.config import get_settings
        from app.models.user import User
        from app.services.account import AccountService
        
        settings = get_settings()
        engine = create_async_engine(str(settings.database_url))
        async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
        
        async with async_session() as db:
            try:
                now = datetime.now(timezone.utc)
                
                # Find users whose deletion grace period has expired
                stmt = (
                    select(User)
                    .where(
                        User.deletion_scheduled_at.isnot(None),
                        User.deletion_scheduled_at <= now,
                    )
                )
                result = await db.execute(stmt)
                users_to_delete = list(result.scalars().all())
                
                deleted_count = 0
                failed_count = 0
                
                for user in users_to_delete:
                    try:
                        service = AccountService(db)
                        success = await service.permanently_delete_user(user.id)
                        if success:
                            deleted_count += 1
                            logger.info(f"Successfully deleted user {user.id}")
                        else:
                            failed_count += 1
                            logger.warning(f"Failed to delete user {user.id}")
                    except Exception as e:
                        failed_count += 1
                        logger.exception(f"Error deleting user {user.id}: {e}")
                        await db.rollback()
                
                return {
                    "success": True,
                    "users_processed": len(users_to_delete),
                    "deleted_count": deleted_count,
                    "failed_count": failed_count,
                }
                
            except Exception as e:
                logger.exception(f"Error processing scheduled deletions: {e}")
                await db.rollback()
                return {"success": False, "error": str(e)}
    
    return run_async(_process())


@celery_app.task(
    name="app.tasks.account_tasks.delete_user_account",
    bind=True,
    max_retries=3,
    default_retry_delay=3600,  # Retry after 1 hour
)
def delete_user_account(self, user_id: str) -> dict:
    """Delete a specific user account.
    
    Validates: Requirements 36.6
    
    This task is scheduled to run 30 days after a deletion request.
    
    Args:
        user_id: UUID of the user to delete
        
    Returns:
        Dict with success status
    """
    async def _delete():
        from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
        from sqlalchemy.orm import sessionmaker
        
        from app.core.config import get_settings
        from app.services.account import AccountService
        
        settings = get_settings()
        engine = create_async_engine(str(settings.database_url))
        async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
        
        async with async_session() as db:
            try:
                service = AccountService(db)
                success = await service.permanently_delete_user(UUID(user_id))
                
                if success:
                    logger.info(f"Successfully deleted user {user_id}")
                    return {"success": True, "user_id": user_id}
                else:
                    logger.warning(f"Deletion not executed for user {user_id} (may have been cancelled)")
                    return {"success": False, "user_id": user_id, "reason": "Deletion cancelled or not due"}
                    
            except Exception as e:
                logger.exception(f"Error deleting user {user_id}: {e}")
                await db.rollback()
                raise self.retry(exc=e)
    
    return run_async(_delete())


@celery_app.task(
    name="app.tasks.account_tasks.send_deletion_reminder",
    bind=True,
    max_retries=3,
    default_retry_delay=60,
)
def send_deletion_reminder(self, user_id: str, days_remaining: int) -> dict:
    """Send a reminder about pending account deletion.
    
    Validates: Requirements 36.6
    
    Args:
        user_id: UUID of the user
        days_remaining: Number of days until deletion
        
    Returns:
        Dict with success status
    """
    async def _send_reminder():
        from sqlalchemy import select
        from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
        from sqlalchemy.orm import sessionmaker
        
        from app.core.config import get_settings
        from app.models.notification import NotificationChannel
        from app.models.user import User
        from app.services.notification import NotificationService
        
        settings = get_settings()
        engine = create_async_engine(str(settings.database_url))
        async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
        
        async with async_session() as db:
            try:
                # Verify user still has pending deletion
                stmt = select(User).where(User.id == user_id)
                result = await db.execute(stmt)
                user = result.scalar_one_or_none()
                
                if not user or not user.deletion_requested_at:
                    logger.info(f"User {user_id} no longer has pending deletion, skipping reminder")
                    return {"success": True, "skipped": True}
                
                # Send notification
                service = NotificationService(db)
                await service.send_notification(
                    user_id=UUID(user_id),
                    title="Account Deletion Reminder",
                    body=f"Your account is scheduled for deletion in {days_remaining} days. "
                         f"Log in to cancel if you've changed your mind.",
                    channel=NotificationChannel.EMAIL,
                )
                
                await db.commit()
                
                logger.info(f"Sent deletion reminder to user {user_id} ({days_remaining} days remaining)")
                return {"success": True, "user_id": user_id, "days_remaining": days_remaining}
                
            except Exception as e:
                logger.exception(f"Error sending deletion reminder to user {user_id}: {e}")
                await db.rollback()
                raise self.retry(exc=e)
    
    return run_async(_send_reminder())
