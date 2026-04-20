"""Celery tasks for admin alerting and error rate monitoring.

Validates: Requirements 38.5
"""

import asyncio
import logging
from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional

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
    name="app.tasks.admin_alerting_tasks.check_error_rates",
    bind=True,
    max_retries=3,
    default_retry_delay=60,
)
def check_error_rates(self) -> dict:
    """Periodic task to check error rates and trigger alerts if thresholds are exceeded.
    
    Validates: Requirements 38.5
    
    This task runs periodically to monitor system error rates and sends
    alerts to administrators when errors exceed the configured threshold.
    
    Returns:
        Dict with check results and alert status
    """
    async def _check():
        from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
        from sqlalchemy.orm import sessionmaker
        
        from app.core.config import get_settings
        from app.services.admin_alerting import AdminAlertingService
        
        settings = get_settings()
        engine = create_async_engine(str(settings.database_url))
        async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
        
        async with async_session() as db:
            try:
                service = AdminAlertingService(db)
                result = await service.check_and_alert()
                
                await db.commit()
                
                logger.info(
                    f"Error rate check completed: "
                    f"rate={result['error_rate']}%, "
                    f"threshold={result['threshold']}%, "
                    f"alert_sent={result['alert_sent']}"
                )
                
                return result
                
            except Exception as e:
                logger.exception(f"Error checking error rates: {e}")
                await db.rollback()
                raise self.retry(exc=e)
    
    return run_async(_check())


@celery_app.task(
    name="app.tasks.admin_alerting_tasks.send_admin_alert",
    bind=True,
    max_retries=3,
    default_retry_delay=60,
)
def send_admin_alert(
    self,
    title: str,
    message: str,
    severity: str = "INFO",
) -> dict:
    """Send a manual alert to all admin users.
    
    Validates: Requirements 38.5
    
    This task can be called from other parts of the system to send
    custom alerts to administrators.
    
    Args:
        title: Alert title
        message: Alert message body
        severity: Alert severity (INFO, WARNING, CRITICAL)
        
    Returns:
        Dict with alert results
    """
    async def _send():
        from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
        from sqlalchemy.orm import sessionmaker
        
        from app.core.config import get_settings
        from app.services.admin_alerting import AdminAlertingService
        
        settings = get_settings()
        engine = create_async_engine(str(settings.database_url))
        async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
        
        async with async_session() as db:
            try:
                service = AdminAlertingService(db)
                result = await service.trigger_manual_alert(
                    title=title,
                    message=message,
                    severity=severity,
                )
                
                await db.commit()
                
                logger.info(
                    f"Admin alert sent: title='{title}', "
                    f"severity={severity}, "
                    f"admins_notified={result['admins_notified']}"
                )
                
                return result
                
            except Exception as e:
                logger.exception(f"Error sending admin alert: {e}")
                await db.rollback()
                raise self.retry(exc=e)
    
    return run_async(_send())


@celery_app.task(
    name="app.tasks.admin_alerting_tasks.check_error_rates_with_metrics",
    bind=True,
    max_retries=3,
    default_retry_delay=60,
)
def check_error_rates_with_metrics(
    self,
    total_requests: int,
    total_errors: int,
) -> dict:
    """Check error rates with provided metrics and trigger alerts if needed.
    
    Validates: Requirements 38.5
    
    This task allows external systems to provide metrics directly,
    useful when integrating with monitoring systems like Prometheus
    or CloudWatch.
    
    Args:
        total_requests: Total number of requests in the time window
        total_errors: Total number of errors in the time window
        
    Returns:
        Dict with check results and alert status
    """
    async def _check():
        from datetime import timedelta
        
        from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
        from sqlalchemy.orm import sessionmaker
        
        from app.core.config import get_settings
        from app.services.admin_alerting import (
            AdminAlertingService,
            AlertThresholds,
            ErrorMetrics,
        )
        
        settings = get_settings()
        engine = create_async_engine(str(settings.database_url))
        async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
        
        async with async_session() as db:
            try:
                # Calculate error rate
                if total_requests > 0:
                    error_rate = Decimal(total_errors) / Decimal(total_requests) * Decimal("100")
                else:
                    error_rate = Decimal("0.0")
                
                # Create metrics object
                now = datetime.now(timezone.utc)
                window_start = now - timedelta(
                    minutes=AlertThresholds.get_error_rate_window_minutes()
                )
                
                metrics = ErrorMetrics(
                    total_requests=total_requests,
                    total_errors=total_errors,
                    error_rate=error_rate.quantize(Decimal("0.01")),
                    window_start=window_start,
                    window_end=now,
                )
                
                # Check and alert
                service = AdminAlertingService(db)
                result = await service.check_and_alert(metrics=metrics)
                
                await db.commit()
                
                logger.info(
                    f"Error rate check with metrics completed: "
                    f"requests={total_requests}, "
                    f"errors={total_errors}, "
                    f"rate={result['error_rate']}%, "
                    f"alert_sent={result['alert_sent']}"
                )
                
                return result
                
            except Exception as e:
                logger.exception(f"Error checking error rates with metrics: {e}")
                await db.rollback()
                raise self.retry(exc=e)
    
    return run_async(_check())
