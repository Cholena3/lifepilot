"""Celery tasks for budget management.

Validates: Requirements 11.2, 11.3, 11.4, 11.6
"""

import asyncio
import logging
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
    name="app.tasks.budget_tasks.archive_expired_budgets",
)
def archive_expired_budgets() -> dict:
    """Periodic task to archive expired budgets and start new periods.
    
    Validates: Requirements 11.6
    
    This task:
    1. Finds all active budgets with end_date < today
    2. Archives them with spent amount to budget_history
    3. Starts a new period for each budget
    
    Returns:
        Dict with success status and statistics
    """
    async def _archive():
        from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
        from sqlalchemy.orm import sessionmaker
        
        from app.core.config import get_settings
        from app.services.budget import BudgetService
        
        settings = get_settings()
        engine = create_async_engine(str(settings.database_url))
        async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
        
        async with async_session() as db:
            try:
                service = BudgetService(db)
                archived = await service.archive_expired_budgets()
                
                await db.commit()
                
                logger.info(f"Archived {len(archived)} expired budgets")
                
                return {
                    "success": True,
                    "budgets_archived": len(archived),
                    "archived_ids": [str(h.id) for h in archived],
                }
                
            except Exception as e:
                logger.exception(f"Error archiving expired budgets: {e}")
                await db.rollback()
                return {"success": False, "error": str(e)}
    
    return run_async(_archive())


@celery_app.task(
    name="app.tasks.budget_tasks.check_budget_thresholds",
    bind=True,
    max_retries=3,
    default_retry_delay=60,
)
def check_budget_thresholds(
    self,
    user_id: str,
    category_id: str,
) -> dict:
    """Check budget thresholds and send notifications if needed.
    
    Validates: Requirements 11.2, 11.3, 11.4
    
    This task is triggered after expense changes to check if any
    budget thresholds have been crossed.
    
    Args:
        user_id: UUID of the user
        category_id: UUID of the expense category
        
    Returns:
        Dict with success status and triggered thresholds
    """
    async def _check():
        from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
        from sqlalchemy.orm import sessionmaker
        
        from app.core.config import get_settings
        from app.services.budget import BudgetService
        
        settings = get_settings()
        engine = create_async_engine(str(settings.database_url))
        async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
        
        async with async_session() as db:
            try:
                service = BudgetService(db)
                triggered = await service.check_and_send_threshold_notifications(
                    UUID(user_id), UUID(category_id)
                )
                
                await db.commit()
                
                if triggered:
                    logger.info(
                        f"Budget thresholds triggered for user {user_id}, "
                        f"category {category_id}: {triggered}"
                    )
                
                return {
                    "success": True,
                    "user_id": user_id,
                    "category_id": category_id,
                    "thresholds_triggered": triggered,
                }
                
            except Exception as e:
                logger.exception(
                    f"Error checking budget thresholds for user {user_id}: {e}"
                )
                await db.rollback()
                raise self.retry(exc=e)
    
    return run_async(_check())


@celery_app.task(
    name="app.tasks.budget_tasks.check_all_user_budgets",
    bind=True,
    max_retries=3,
    default_retry_delay=60,
)
def check_all_user_budgets(self, user_id: str) -> dict:
    """Check all budget thresholds for a user.
    
    Validates: Requirements 11.2, 11.3, 11.4
    
    Args:
        user_id: UUID of the user
        
    Returns:
        Dict with success status and triggered thresholds per budget
    """
    async def _check():
        from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
        from sqlalchemy.orm import sessionmaker
        
        from app.core.config import get_settings
        from app.services.budget import BudgetService
        
        settings = get_settings()
        engine = create_async_engine(str(settings.database_url))
        async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
        
        async with async_session() as db:
            try:
                service = BudgetService(db)
                results = await service.check_all_budgets_thresholds(UUID(user_id))
                
                await db.commit()
                
                # Convert UUID keys to strings for JSON serialization
                results_str = {str(k): v for k, v in results.items()}
                
                logger.info(
                    f"Checked all budgets for user {user_id}: "
                    f"{len(results)} budgets triggered notifications"
                )
                
                return {
                    "success": True,
                    "user_id": user_id,
                    "budgets_with_notifications": results_str,
                }
                
            except Exception as e:
                logger.exception(
                    f"Error checking all budgets for user {user_id}: {e}"
                )
                await db.rollback()
                raise self.retry(exc=e)
    
    return run_async(_check())
