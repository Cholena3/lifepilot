"""Celery tasks for exam deadline reminders and data scraping.

Validates: Requirements 3.7, 5.1, 5.2, 5.3, 5.4, 5.5
"""

import asyncio
import logging
from datetime import date, timedelta
from typing import Optional
from uuid import UUID

from app.tasks import celery_app

logger = logging.getLogger(__name__)

# Scraper retry configuration
SCRAPER_MAX_RETRIES = 3
SCRAPER_RETRY_DELAY = 300  # 5 minutes


def run_async(coro):
    """Helper to run async code in sync context."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


@celery_app.task(
    name="app.tasks.exam_tasks.check_exam_deadline_reminders",
)
def check_exam_deadline_reminders() -> dict:
    """Periodic task to check for exam deadlines and send reminders.
    
    Validates: Requirements 3.7
    
    This task:
    1. Finds exams with registration_end date exactly 7 days from now
    2. Sends notifications to all users who have bookmarked those exams
    
    Returns:
        Dict with success status and statistics
    """
    async def _check():
        from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
        from sqlalchemy.orm import sessionmaker
        
        from app.core.config import get_settings
        from app.models.notification import NotificationChannel
        from app.repositories.exam import ExamBookmarkRepository, ExamRepository
        from app.services.notification import NotificationService
        
        settings = get_settings()
        engine = create_async_engine(str(settings.database_url))
        async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
        
        async with async_session() as db:
            try:
                # Calculate the target date (7 days from now)
                target_date = date.today() + timedelta(days=7)
                
                # Get exams with deadline in 7 days
                exam_repo = ExamRepository(db)
                exams_with_deadline = await exam_repo.get_exams_with_deadline_on_date(target_date)
                
                if not exams_with_deadline:
                    logger.info("No exams with deadline in 7 days found")
                    return {
                        "success": True,
                        "exams_checked": 0,
                        "notifications_sent": 0,
                        "errors": [],
                    }
                
                bookmark_repo = ExamBookmarkRepository(db)
                notification_service = NotificationService(db)
                
                notifications_sent = 0
                errors = []
                
                for exam in exams_with_deadline:
                    # Get all users who bookmarked this exam
                    bookmarked_users = await bookmark_repo.get_users_who_bookmarked_exam(exam.id)
                    
                    for user_id in bookmarked_users:
                        try:
                            # Send notification to user
                            title = f"Exam Deadline Reminder: {exam.name}"
                            body = (
                                f"The registration deadline for {exam.name} "
                                f"({exam.organization}) is in 7 days "
                                f"({exam.registration_end.strftime('%B %d, %Y')}). "
                                f"Don't miss the deadline!"
                            )
                            
                            result = await notification_service.send_notification(
                                user_id=user_id,
                                title=title,
                                body=body,
                                channel=NotificationChannel.PUSH,
                            )
                            
                            if result.success:
                                notifications_sent += 1
                                logger.info(
                                    f"Sent deadline reminder for exam {exam.id} to user {user_id}"
                                )
                            else:
                                errors.append(
                                    f"Failed to send notification for exam {exam.id} "
                                    f"to user {user_id}: {result.error}"
                                )
                                
                        except Exception as e:
                            error_msg = (
                                f"Error sending notification for exam {exam.id} "
                                f"to user {user_id}: {str(e)}"
                            )
                            errors.append(error_msg)
                            logger.exception(error_msg)
                
                await db.commit()
                
                logger.info(
                    f"Exam deadline reminder check completed: "
                    f"exams_checked={len(exams_with_deadline)}, "
                    f"notifications_sent={notifications_sent}"
                )
                
                return {
                    "success": True,
                    "exams_checked": len(exams_with_deadline),
                    "notifications_sent": notifications_sent,
                    "errors": errors,
                }
                
            except Exception as e:
                logger.exception(f"Error checking exam deadline reminders: {e}")
                await db.rollback()
                return {"success": False, "error": str(e)}
    
    return run_async(_check())


@celery_app.task(
    name="app.tasks.exam_tasks.send_exam_deadline_reminder",
    bind=True,
    max_retries=3,
    default_retry_delay=60,
)
def send_exam_deadline_reminder(
    self,
    exam_id: str,
    user_id: str,
) -> dict:
    """Send a deadline reminder for a specific exam to a specific user.
    
    Validates: Requirements 3.7
    
    Args:
        exam_id: UUID of the exam
        user_id: UUID of the user to notify
        
    Returns:
        Dict with success status and details
    """
    async def _send():
        from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
        from sqlalchemy.orm import sessionmaker
        
        from app.core.config import get_settings
        from app.models.notification import NotificationChannel
        from app.repositories.exam import ExamRepository
        from app.services.notification import NotificationService
        
        settings = get_settings()
        engine = create_async_engine(str(settings.database_url))
        async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
        
        async with async_session() as db:
            try:
                exam_repo = ExamRepository(db)
                exam = await exam_repo.get_exam_by_id(UUID(exam_id))
                
                if exam is None:
                    logger.error(f"Exam {exam_id} not found")
                    return {"success": False, "error": "Exam not found"}
                
                if exam.registration_end is None:
                    logger.error(f"Exam {exam_id} has no registration deadline")
                    return {"success": False, "error": "Exam has no deadline"}
                
                # Calculate days until deadline
                days_until = (exam.registration_end - date.today()).days
                
                notification_service = NotificationService(db)
                
                title = f"Exam Deadline Reminder: {exam.name}"
                body = (
                    f"The registration deadline for {exam.name} "
                    f"({exam.organization}) is in {days_until} days "
                    f"({exam.registration_end.strftime('%B %d, %Y')}). "
                    f"Don't miss the deadline!"
                )
                
                result = await notification_service.send_notification(
                    user_id=UUID(user_id),
                    title=title,
                    body=body,
                    channel=NotificationChannel.PUSH,
                )
                
                await db.commit()
                
                return {
                    "success": result.success,
                    "notification_id": str(result.notification_id) if result.notification_id else None,
                    "exam_id": exam_id,
                    "user_id": user_id,
                    "error": result.error,
                }
                
            except Exception as e:
                logger.exception(
                    f"Error sending deadline reminder for exam {exam_id} to user {user_id}: {e}"
                )
                await db.rollback()
                raise self.retry(exc=e)
    
    return run_async(_send())


# ============================================================================
# Exam Data Scraping Tasks
# ============================================================================

@celery_app.task(
    name="app.tasks.exam_tasks.run_exam_scraper",
    bind=True,
    max_retries=SCRAPER_MAX_RETRIES,
    default_retry_delay=SCRAPER_RETRY_DELAY,
)
def run_exam_scraper(self, source: str) -> dict:
    """Run a specific exam scraper.
    
    Validates: Requirements 5.1, 5.4
    
    Args:
        source: The scraper source (tcs, infosys, gate, upsc, naukri, linkedin)
        
    Returns:
        Dict with scraper result statistics
    """
    async def _run():
        from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
        from sqlalchemy.orm import sessionmaker
        
        from app.core.config import get_settings
        from app.services.scraper import ScraperSource, get_scraper
        
        settings = get_settings()
        engine = create_async_engine(str(settings.database_url))
        async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
        
        async with async_session() as db:
            try:
                # Get the scraper source enum
                try:
                    scraper_source = ScraperSource(source.lower())
                except ValueError:
                    logger.error(f"Invalid scraper source: {source}")
                    return {
                        "success": False,
                        "source": source,
                        "error": f"Invalid scraper source: {source}",
                    }
                
                # Run the scraper
                scraper = get_scraper(scraper_source, db)
                result = await scraper.run()
                
                await db.commit()
                
                return {
                    "success": result.success,
                    "source": result.source.value,
                    "exams_found": result.exams_found,
                    "exams_created": result.exams_created,
                    "exams_updated": result.exams_updated,
                    "exams_skipped": result.exams_skipped,
                    "errors": result.errors,
                    "started_at": result.started_at.isoformat() if result.started_at else None,
                    "completed_at": result.completed_at.isoformat() if result.completed_at else None,
                }
                
            except Exception as e:
                logger.exception(f"Error running scraper for {source}: {e}")
                await db.rollback()
                raise self.retry(exc=e)
    
    return run_async(_run())


@celery_app.task(
    name="app.tasks.exam_tasks.run_all_exam_scrapers",
)
def run_all_exam_scrapers() -> dict:
    """Run all configured exam scrapers.
    
    Validates: Requirements 5.1
    
    This is the main scheduled task that runs all scrapers.
    
    Returns:
        Dict with results from all scrapers
    """
    async def _run():
        from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
        from sqlalchemy.orm import sessionmaker
        
        from app.core.config import get_settings
        from app.services.scraper import run_all_scrapers
        
        settings = get_settings()
        engine = create_async_engine(str(settings.database_url))
        async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
        
        async with async_session() as db:
            try:
                results = await run_all_scrapers(db)
                await db.commit()
                
                return {
                    "success": True,
                    "total_sources": len(results),
                    "successful_sources": sum(1 for r in results if r.success),
                    "results": [
                        {
                            "source": r.source.value,
                            "success": r.success,
                            "exams_found": r.exams_found,
                            "exams_created": r.exams_created,
                            "exams_updated": r.exams_updated,
                            "exams_skipped": r.exams_skipped,
                            "errors": r.errors[:5],  # Limit errors to first 5
                        }
                        for r in results
                    ],
                }
                
            except Exception as e:
                logger.exception(f"Error running all scrapers: {e}")
                await db.rollback()
                return {"success": False, "error": str(e)}
    
    return run_async(_run())


@celery_app.task(
    name="app.tasks.exam_tasks.scrape_tcs_exams",
    bind=True,
    max_retries=SCRAPER_MAX_RETRIES,
    default_retry_delay=SCRAPER_RETRY_DELAY,
)
def scrape_tcs_exams(self) -> dict:
    """Scrape TCS exam data.
    
    Validates: Requirements 5.1, 5.4, 5.5
    """
    return run_exam_scraper.apply(args=["tcs"]).get()


@celery_app.task(
    name="app.tasks.exam_tasks.scrape_infosys_exams",
    bind=True,
    max_retries=SCRAPER_MAX_RETRIES,
    default_retry_delay=SCRAPER_RETRY_DELAY,
)
def scrape_infosys_exams(self) -> dict:
    """Scrape Infosys exam data.
    
    Validates: Requirements 5.1, 5.4, 5.5
    """
    return run_exam_scraper.apply(args=["infosys"]).get()


@celery_app.task(
    name="app.tasks.exam_tasks.scrape_gate_exams",
    bind=True,
    max_retries=SCRAPER_MAX_RETRIES,
    default_retry_delay=SCRAPER_RETRY_DELAY,
)
def scrape_gate_exams(self) -> dict:
    """Scrape GATE exam data.
    
    Validates: Requirements 5.1, 5.4, 5.5
    """
    return run_exam_scraper.apply(args=["gate"]).get()


@celery_app.task(
    name="app.tasks.exam_tasks.scrape_upsc_exams",
    bind=True,
    max_retries=SCRAPER_MAX_RETRIES,
    default_retry_delay=SCRAPER_RETRY_DELAY,
)
def scrape_upsc_exams(self) -> dict:
    """Scrape UPSC exam data.
    
    Validates: Requirements 5.1, 5.4, 5.5
    """
    return run_exam_scraper.apply(args=["upsc"]).get()


@celery_app.task(
    name="app.tasks.exam_tasks.scrape_naukri_exams",
    bind=True,
    max_retries=SCRAPER_MAX_RETRIES,
    default_retry_delay=SCRAPER_RETRY_DELAY,
)
def scrape_naukri_exams(self) -> dict:
    """Scrape Naukri exam data.
    
    Validates: Requirements 5.1, 5.4, 5.5
    """
    return run_exam_scraper.apply(args=["naukri"]).get()


@celery_app.task(
    name="app.tasks.exam_tasks.scrape_linkedin_exams",
    bind=True,
    max_retries=SCRAPER_MAX_RETRIES,
    default_retry_delay=SCRAPER_RETRY_DELAY,
)
def scrape_linkedin_exams(self) -> dict:
    """Scrape LinkedIn exam/job data.
    
    Validates: Requirements 5.1, 5.4, 5.5
    """
    return run_exam_scraper.apply(args=["linkedin"]).get()
