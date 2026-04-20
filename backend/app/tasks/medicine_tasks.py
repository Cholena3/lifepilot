"""Celery tasks for medicine reminders and refill alerts.

Validates: Requirements 15.2, 15.4, 15.5
"""

import asyncio
import logging
from datetime import datetime, timedelta, timezone
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
    name="app.tasks.medicine_tasks.send_dose_reminder",
    bind=True,
    max_retries=3,
    default_retry_delay=60,
)
def send_dose_reminder(
    self,
    dose_id: str,
    user_id: str,
    medicine_name: str,
    dosage: Optional[str],
    instructions: Optional[str],
) -> dict:
    """Send a dose reminder notification.
    
    Validates: Requirements 15.2
    
    Args:
        dose_id: UUID of the dose
        user_id: UUID of the user
        medicine_name: Name of the medicine
        dosage: Dosage information
        instructions: Additional instructions
        
    Returns:
        Dict with success status and details
    """
    async def _send():
        from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
        from sqlalchemy.orm import sessionmaker
        
        from app.core.config import get_settings
        from app.models.notification import NotificationChannel
        from app.repositories.medicine import MedicineRepository
        from app.services.notification import NotificationService
        
        settings = get_settings()
        engine = create_async_engine(str(settings.database_url))
        async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
        
        async with async_session() as db:
            try:
                # Build notification message
                title = f"Time to take {medicine_name}"
                body_parts = [f"It's time for your {medicine_name}"]
                if dosage:
                    body_parts.append(f"Dosage: {dosage}")
                if instructions:
                    body_parts.append(f"Instructions: {instructions}")
                body = "\n".join(body_parts)
                
                # Send notification
                notification_service = NotificationService(db)
                result = await notification_service.send_notification_with_quiet_hours(
                    user_id=UUID(user_id),
                    title=title,
                    body=body,
                    channel=NotificationChannel.PUSH,
                    is_urgent=False,
                )
                
                # Mark reminder as sent
                medicine_repo = MedicineRepository(db)
                dose = await medicine_repo.get_dose_by_id(UUID(dose_id))
                if dose:
                    await medicine_repo.mark_dose_reminder_sent(dose, is_followup=False)
                
                await db.commit()
                
                return {
                    "success": result.success,
                    "dose_id": dose_id,
                    "notification_id": str(result.notification_id) if result.notification_id else None,
                    "error": result.error,
                }
                
            except Exception as e:
                logger.exception(f"Error sending dose reminder for dose {dose_id}: {e}")
                await db.rollback()
                raise self.retry(exc=e)
    
    return run_async(_send())


@celery_app.task(
    name="app.tasks.medicine_tasks.send_missed_dose_followup",
    bind=True,
    max_retries=3,
    default_retry_delay=60,
)
def send_missed_dose_followup(
    self,
    dose_id: str,
    user_id: str,
    medicine_name: str,
    scheduled_time: str,
) -> dict:
    """Send a follow-up reminder for a missed dose.
    
    Validates: Requirements 15.4
    
    Args:
        dose_id: UUID of the dose
        user_id: UUID of the user
        medicine_name: Name of the medicine
        scheduled_time: When the dose was scheduled (ISO format)
        
    Returns:
        Dict with success status and details
    """
    async def _send():
        from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
        from sqlalchemy.orm import sessionmaker
        
        from app.core.config import get_settings
        from app.models.medicine import DoseStatus
        from app.models.notification import NotificationChannel
        from app.repositories.medicine import MedicineRepository
        from app.services.notification import NotificationService
        
        settings = get_settings()
        engine = create_async_engine(str(settings.database_url))
        async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
        
        async with async_session() as db:
            try:
                # Build notification message
                title = f"Missed dose: {medicine_name}"
                body = (
                    f"You missed your scheduled dose of {medicine_name}. "
                    f"Please take it as soon as possible or skip if advised by your doctor."
                )
                
                # Send notification
                notification_service = NotificationService(db)
                result = await notification_service.send_notification_with_quiet_hours(
                    user_id=UUID(user_id),
                    title=title,
                    body=body,
                    channel=NotificationChannel.PUSH,
                    is_urgent=True,  # Missed dose is urgent
                )
                
                # Mark follow-up reminder as sent and update status to missed
                medicine_repo = MedicineRepository(db)
                dose = await medicine_repo.get_dose_by_id(UUID(dose_id))
                if dose:
                    await medicine_repo.mark_dose_reminder_sent(dose, is_followup=True)
                    await medicine_repo.update_dose_status(dose, DoseStatus.MISSED.value)
                
                await db.commit()
                
                return {
                    "success": result.success,
                    "dose_id": dose_id,
                    "notification_id": str(result.notification_id) if result.notification_id else None,
                    "error": result.error,
                }
                
            except Exception as e:
                logger.exception(f"Error sending missed dose follow-up for dose {dose_id}: {e}")
                await db.rollback()
                raise self.retry(exc=e)
    
    return run_async(_send())


@celery_app.task(
    name="app.tasks.medicine_tasks.send_refill_reminder",
    bind=True,
    max_retries=3,
    default_retry_delay=60,
)
def send_refill_reminder(
    self,
    medicine_id: str,
    user_id: str,
    medicine_name: str,
    remaining_quantity: int,
    days_until_empty: Optional[int],
) -> dict:
    """Send a refill reminder notification.
    
    Validates: Requirements 15.5
    
    Args:
        medicine_id: UUID of the medicine
        user_id: UUID of the user
        medicine_name: Name of the medicine
        remaining_quantity: Remaining quantity
        days_until_empty: Estimated days until medicine runs out
        
    Returns:
        Dict with success status and details
    """
    async def _send():
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
                # Build notification message
                title = f"Refill needed: {medicine_name}"
                body_parts = [
                    f"Your supply of {medicine_name} is running low.",
                    f"Remaining: {remaining_quantity} doses",
                ]
                if days_until_empty is not None:
                    body_parts.append(f"Estimated to run out in {days_until_empty} days")
                body_parts.append("Please refill your prescription soon.")
                body = "\n".join(body_parts)
                
                # Send notification
                notification_service = NotificationService(db)
                result = await notification_service.send_notification_with_quiet_hours(
                    user_id=UUID(user_id),
                    title=title,
                    body=body,
                    channel=NotificationChannel.PUSH,
                    is_urgent=False,
                )
                
                await db.commit()
                
                return {
                    "success": result.success,
                    "medicine_id": medicine_id,
                    "notification_id": str(result.notification_id) if result.notification_id else None,
                    "error": result.error,
                }
                
            except Exception as e:
                logger.exception(f"Error sending refill reminder for medicine {medicine_id}: {e}")
                await db.rollback()
                raise self.retry(exc=e)
    
    return run_async(_send())


@celery_app.task(
    name="app.tasks.medicine_tasks.process_pending_dose_reminders",
)
def process_pending_dose_reminders() -> dict:
    """Periodic task to process and send pending dose reminders.
    
    Validates: Requirements 15.2
    
    Returns:
        Dict with success status and count of reminders sent
    """
    async def _process():
        from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
        from sqlalchemy.orm import sessionmaker
        
        from app.core.config import get_settings
        from app.repositories.medicine import MedicineRepository
        
        settings = get_settings()
        engine = create_async_engine(str(settings.database_url))
        async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
        
        async with async_session() as db:
            try:
                medicine_repo = MedicineRepository(db)
                
                # Get doses that need reminders (scheduled within next 5 minutes)
                reminder_time = datetime.now(timezone.utc) + timedelta(minutes=5)
                pending_doses = await medicine_repo.get_pending_dose_reminders(reminder_time)
                
                reminders_queued = 0
                for dose in pending_doses:
                    # Queue individual reminder task
                    send_dose_reminder.delay(
                        dose_id=str(dose.id),
                        user_id=str(dose.medicine.user_id),
                        medicine_name=dose.medicine.name,
                        dosage=dose.medicine.dosage,
                        instructions=dose.medicine.instructions,
                    )
                    reminders_queued += 1
                
                return {
                    "success": True,
                    "reminders_queued": reminders_queued,
                }
                
            except Exception as e:
                logger.exception(f"Error processing pending dose reminders: {e}")
                return {"success": False, "error": str(e)}
    
    return run_async(_process())


@celery_app.task(
    name="app.tasks.medicine_tasks.process_missed_doses",
)
def process_missed_doses() -> dict:
    """Periodic task to process missed doses and send follow-up reminders.
    
    Validates: Requirements 15.4
    
    Returns:
        Dict with success status and count of follow-ups sent
    """
    async def _process():
        from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
        from sqlalchemy.orm import sessionmaker
        
        from app.core.config import get_settings
        from app.repositories.medicine import MedicineRepository
        
        settings = get_settings()
        engine = create_async_engine(str(settings.database_url))
        async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
        
        async with async_session() as db:
            try:
                medicine_repo = MedicineRepository(db)
                
                # Get doses that are missed (30 minutes past scheduled time)
                missed_doses = await medicine_repo.get_missed_doses_needing_followup(
                    grace_period_minutes=30
                )
                
                followups_queued = 0
                for dose in missed_doses:
                    # Queue follow-up reminder task
                    send_missed_dose_followup.delay(
                        dose_id=str(dose.id),
                        user_id=str(dose.medicine.user_id),
                        medicine_name=dose.medicine.name,
                        scheduled_time=dose.scheduled_time.isoformat(),
                    )
                    followups_queued += 1
                
                return {
                    "success": True,
                    "followups_queued": followups_queued,
                }
                
            except Exception as e:
                logger.exception(f"Error processing missed doses: {e}")
                return {"success": False, "error": str(e)}
    
    return run_async(_process())


@celery_app.task(
    name="app.tasks.medicine_tasks.process_refill_alerts",
)
def process_refill_alerts() -> dict:
    """Periodic task to check for medicines needing refill and send alerts.
    
    Validates: Requirements 15.5
    
    Returns:
        Dict with success status and count of alerts sent
    """
    async def _process():
        from sqlalchemy import select
        from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
        from sqlalchemy.orm import sessionmaker
        
        from app.core.config import get_settings
        from app.models.medicine import Medicine
        from app.models.medicine import MedicineFrequency
        
        settings = get_settings()
        engine = create_async_engine(str(settings.database_url))
        async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
        
        async with async_session() as db:
            try:
                # Get all medicines needing refill
                stmt = (
                    select(Medicine)
                    .where(
                        Medicine.is_active == True,
                        Medicine.remaining_quantity.isnot(None),
                        Medicine.remaining_quantity <= Medicine.refill_threshold,
                    )
                )
                result = await db.execute(stmt)
                medicines = list(result.scalars().all())
                
                alerts_queued = 0
                for medicine in medicines:
                    # Calculate days until empty
                    days_until_empty = None
                    if medicine.remaining_quantity is not None:
                        doses_per_day = _get_doses_per_day(medicine.frequency)
                        if doses_per_day > 0:
                            days_until_empty = int(medicine.remaining_quantity / doses_per_day)
                    
                    # Queue refill reminder task
                    send_refill_reminder.delay(
                        medicine_id=str(medicine.id),
                        user_id=str(medicine.user_id),
                        medicine_name=medicine.name,
                        remaining_quantity=medicine.remaining_quantity or 0,
                        days_until_empty=days_until_empty,
                    )
                    alerts_queued += 1
                
                return {
                    "success": True,
                    "alerts_queued": alerts_queued,
                }
                
            except Exception as e:
                logger.exception(f"Error processing refill alerts: {e}")
                return {"success": False, "error": str(e)}
    
    return run_async(_process())


@celery_app.task(
    name="app.tasks.medicine_tasks.schedule_daily_doses",
)
def schedule_daily_doses() -> dict:
    """Periodic task to schedule doses for all active medicines.
    
    This task runs daily to ensure doses are scheduled for the upcoming week.
    
    Returns:
        Dict with success status and count of doses scheduled
    """
    async def _schedule():
        from sqlalchemy import select
        from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
        from sqlalchemy.orm import sessionmaker
        
        from app.core.config import get_settings
        from app.models.medicine import Medicine
        from app.services.medicine import MedicineService
        
        settings = get_settings()
        engine = create_async_engine(str(settings.database_url))
        async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
        
        async with async_session() as db:
            try:
                # Get all active medicines with reminder times
                stmt = (
                    select(Medicine)
                    .where(
                        Medicine.is_active == True,
                        Medicine.reminder_times.isnot(None),
                    )
                )
                result = await db.execute(stmt)
                medicines = list(result.scalars().all())
                
                total_scheduled = 0
                service = MedicineService(db)
                
                for medicine in medicines:
                    count = await service.schedule_doses(
                        medicine.user_id,
                        medicine.id,
                        days_ahead=7,
                    )
                    if count:
                        total_scheduled += count
                
                await db.commit()
                
                return {
                    "success": True,
                    "medicines_processed": len(medicines),
                    "doses_scheduled": total_scheduled,
                }
                
            except Exception as e:
                logger.exception(f"Error scheduling daily doses: {e}")
                await db.rollback()
                return {"success": False, "error": str(e)}
    
    return run_async(_schedule())


def _get_doses_per_day(frequency: str) -> float:
    """Get number of doses per day based on frequency.
    
    Args:
        frequency: Medicine frequency
        
    Returns:
        Number of doses per day
    """
    from app.models.medicine import MedicineFrequency
    
    frequency_map = {
        MedicineFrequency.ONCE_DAILY.value: 1.0,
        MedicineFrequency.TWICE_DAILY.value: 2.0,
        MedicineFrequency.THREE_TIMES_DAILY.value: 3.0,
        MedicineFrequency.FOUR_TIMES_DAILY.value: 4.0,
        MedicineFrequency.EVERY_OTHER_DAY.value: 0.5,
        MedicineFrequency.WEEKLY.value: 1/7,
        MedicineFrequency.AS_NEEDED.value: 0,
        MedicineFrequency.CUSTOM.value: 1.0,
    }
    return frequency_map.get(frequency, 1.0)
