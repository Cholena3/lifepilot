"""Admin alerting service for monitoring system errors and triggering alerts.

Provides functionality to monitor error rates and trigger alerts to administrators
when errors exceed configurable thresholds.

Validates: Requirements 38.5
"""

import logging
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import List, Optional
from uuid import UUID

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.models.notification import NotificationChannel
from app.models.user import User
from app.services.notification import NotificationService

logger = logging.getLogger(__name__)


class AlertThresholds:
    """Configurable thresholds for admin alerts.
    
    Validates: Requirements 38.5
    
    Thresholds are loaded from application settings but can be
    overridden programmatically for testing or dynamic configuration.
    """
    
    _settings = None
    
    # Override values (None means use settings)
    _error_rate_override: Optional[Decimal] = None
    _min_requests_override: Optional[int] = None
    _window_minutes_override: Optional[int] = None
    _cooldown_minutes_override: Optional[int] = None
    _critical_rate_override: Optional[Decimal] = None
    
    @classmethod
    def _get_settings(cls):
        if cls._settings is None:
            cls._settings = get_settings()
        return cls._settings
    
    @classmethod
    def get_error_rate_threshold(cls) -> Decimal:
        """Error rate threshold (percentage) - trigger alert when exceeded."""
        if cls._error_rate_override is not None:
            return cls._error_rate_override
        return Decimal(str(cls._get_settings().admin_alert_error_rate_threshold))
    
    @classmethod
    def get_min_requests_for_alert(cls) -> int:
        """Minimum requests required before checking error rate."""
        if cls._min_requests_override is not None:
            return cls._min_requests_override
        return cls._get_settings().admin_alert_min_requests
    
    @classmethod
    def get_error_rate_window_minutes(cls) -> int:
        """Time window for error rate calculation (in minutes)."""
        if cls._window_minutes_override is not None:
            return cls._window_minutes_override
        return cls._get_settings().admin_alert_window_minutes
    
    @classmethod
    def get_alert_cooldown_minutes(cls) -> int:
        """Cooldown period between alerts (in minutes) to prevent alert fatigue."""
        if cls._cooldown_minutes_override is not None:
            return cls._cooldown_minutes_override
        return cls._get_settings().admin_alert_cooldown_minutes
    
    @classmethod
    def get_critical_error_rate_threshold(cls) -> Decimal:
        """Critical error rate threshold for immediate escalation."""
        if cls._critical_rate_override is not None:
            return cls._critical_rate_override
        return Decimal(str(cls._get_settings().admin_alert_critical_rate_threshold))
    
    @classmethod
    def set_overrides(
        cls,
        error_rate: Optional[Decimal] = None,
        min_requests: Optional[int] = None,
        window_minutes: Optional[int] = None,
        cooldown_minutes: Optional[int] = None,
        critical_rate: Optional[Decimal] = None,
    ) -> None:
        """Set threshold overrides (useful for testing).
        
        Args:
            error_rate: Error rate threshold percentage
            min_requests: Minimum requests before alerting
            window_minutes: Time window for error rate calculation
            cooldown_minutes: Cooldown between alerts
            critical_rate: Critical error rate threshold
        """
        cls._error_rate_override = error_rate
        cls._min_requests_override = min_requests
        cls._window_minutes_override = window_minutes
        cls._cooldown_minutes_override = cooldown_minutes
        cls._critical_rate_override = critical_rate
    
    @classmethod
    def reset_overrides(cls) -> None:
        """Reset all threshold overrides to use settings values."""
        cls._error_rate_override = None
        cls._min_requests_override = None
        cls._window_minutes_override = None
        cls._cooldown_minutes_override = None
        cls._critical_rate_override = None
        cls._settings = None  # Force reload of settings


class ErrorMetrics:
    """Container for error metrics data."""
    
    def __init__(
        self,
        total_requests: int,
        total_errors: int,
        error_rate: Decimal,
        window_start: datetime,
        window_end: datetime,
    ):
        self.total_requests = total_requests
        self.total_errors = total_errors
        self.error_rate = error_rate
        self.window_start = window_start
        self.window_end = window_end
    
    @property
    def is_critical(self) -> bool:
        """Check if error rate is at critical level."""
        return self.error_rate >= AlertThresholds.get_critical_error_rate_threshold()
    
    @property
    def exceeds_threshold(self) -> bool:
        """Check if error rate exceeds the alert threshold."""
        return self.error_rate >= AlertThresholds.get_error_rate_threshold()


class AdminAlertingService:
    """Service for monitoring system errors and alerting administrators.
    
    Validates: Requirements 38.5
    """
    
    # In-memory tracking of last alert time to prevent alert fatigue
    # In production, this would be stored in Redis for distributed systems
    _last_alert_time: Optional[datetime] = None
    
    def __init__(self, db: AsyncSession) -> None:
        """Initialize the admin alerting service.
        
        Args:
            db: Async database session
        """
        self.db = db
        self.notification_service = NotificationService(db)
    
    async def get_admin_users(self) -> List[User]:
        """Get all admin users who should receive alerts.
        
        Returns:
            List of admin User objects
        """
        stmt = select(User).where(User.is_admin == True)
        result = await self.db.execute(stmt)
        return list(result.scalars().all())
    
    async def get_error_metrics(
        self,
        window_minutes: Optional[int] = None,
    ) -> ErrorMetrics:
        """Get error metrics for the specified time window.
        
        In a production system, these metrics would come from a monitoring
        system like Prometheus, DataDog, or CloudWatch. This implementation
        provides a simulated approach that can be replaced with actual
        metrics collection.
        
        Args:
            window_minutes: Time window in minutes (defaults to configured value)
            
        Returns:
            ErrorMetrics object with current error statistics
        """
        if window_minutes is None:
            window_minutes = AlertThresholds.get_error_rate_window_minutes()
        
        now = datetime.now(timezone.utc)
        window_start = now - timedelta(minutes=window_minutes)
        
        # In production, this would query actual metrics from a monitoring system
        # For now, we simulate by checking notification failures as a proxy
        # This can be replaced with actual metrics integration
        
        # Simulated metrics - in production, replace with actual metrics source
        total_requests = await self._get_request_count(window_start, now)
        total_errors = await self._get_error_count(window_start, now)
        
        if total_requests > 0:
            error_rate = Decimal(total_errors) / Decimal(total_requests) * Decimal("100")
        else:
            error_rate = Decimal("0.0")
        
        return ErrorMetrics(
            total_requests=total_requests,
            total_errors=total_errors,
            error_rate=error_rate.quantize(Decimal("0.01")),
            window_start=window_start,
            window_end=now,
        )
    
    async def _get_request_count(
        self,
        start_time: datetime,
        end_time: datetime,
    ) -> int:
        """Get total request count for the time window.
        
        In production, this would query actual request metrics.
        This is a placeholder that returns simulated data.
        
        Args:
            start_time: Start of time window
            end_time: End of time window
            
        Returns:
            Total request count
        """
        # Placeholder - in production, integrate with metrics system
        # For now, return a simulated value based on time window
        # This allows the alerting logic to be tested
        return 0
    
    async def _get_error_count(
        self,
        start_time: datetime,
        end_time: datetime,
    ) -> int:
        """Get total error count for the time window.
        
        In production, this would query actual error metrics.
        This is a placeholder that returns simulated data.
        
        Args:
            start_time: Start of time window
            end_time: End of time window
            
        Returns:
            Total error count
        """
        # Placeholder - in production, integrate with metrics system
        return 0
    
    def _can_send_alert(self) -> bool:
        """Check if enough time has passed since the last alert.
        
        Prevents alert fatigue by enforcing a cooldown period.
        
        Returns:
            True if alert can be sent, False if in cooldown
        """
        if self._last_alert_time is None:
            return True
        
        cooldown = timedelta(minutes=AlertThresholds.get_alert_cooldown_minutes())
        return datetime.now(timezone.utc) - self._last_alert_time >= cooldown
    
    def _update_last_alert_time(self) -> None:
        """Update the last alert time to now."""
        AdminAlertingService._last_alert_time = datetime.now(timezone.utc)
    
    async def check_and_alert(
        self,
        metrics: Optional[ErrorMetrics] = None,
    ) -> dict:
        """Check error metrics and send alerts if thresholds are exceeded.
        
        Validates: Requirements 38.5
        
        Args:
            metrics: Optional pre-computed metrics (will be fetched if not provided)
            
        Returns:
            Dict with check results and alert status
        """
        if metrics is None:
            metrics = await self.get_error_metrics()
        
        result = {
            "checked_at": datetime.now(timezone.utc).isoformat(),
            "total_requests": metrics.total_requests,
            "total_errors": metrics.total_errors,
            "error_rate": str(metrics.error_rate),
            "threshold": str(AlertThresholds.get_error_rate_threshold()),
            "exceeds_threshold": metrics.exceeds_threshold,
            "is_critical": metrics.is_critical,
            "alert_sent": False,
            "alert_skipped_reason": None,
        }
        
        # Check if we have enough requests to make a meaningful assessment
        min_requests = AlertThresholds.get_min_requests_for_alert()
        if metrics.total_requests < min_requests:
            result["alert_skipped_reason"] = (
                f"Insufficient requests ({metrics.total_requests} < "
                f"{min_requests})"
            )
            logger.debug(
                f"Skipping alert check: insufficient requests "
                f"({metrics.total_requests} < {min_requests})"
            )
            return result
        
        # Check if error rate exceeds threshold
        threshold = AlertThresholds.get_error_rate_threshold()
        if not metrics.exceeds_threshold:
            result["alert_skipped_reason"] = "Error rate within acceptable limits"
            logger.debug(
                f"Error rate {metrics.error_rate}% is within threshold "
                f"({threshold}%)"
            )
            return result
        
        # Check cooldown period
        if not self._can_send_alert():
            result["alert_skipped_reason"] = "Alert cooldown period active"
            logger.info(
                f"Alert suppressed due to cooldown. Error rate: {metrics.error_rate}%"
            )
            return result
        
        # Send alert to all admin users
        alert_sent = await self._send_error_rate_alert(metrics)
        result["alert_sent"] = alert_sent
        
        if alert_sent:
            self._update_last_alert_time()
            logger.warning(
                f"Admin alert sent: Error rate {metrics.error_rate}% exceeds "
                f"threshold {threshold}%"
            )
        
        return result
    
    async def _send_error_rate_alert(self, metrics: ErrorMetrics) -> bool:
        """Send error rate alert to all admin users.
        
        Args:
            metrics: Current error metrics
            
        Returns:
            True if at least one alert was sent successfully
        """
        admin_users = await self.get_admin_users()
        
        if not admin_users:
            logger.warning("No admin users found to receive error rate alert")
            return False
        
        # Determine alert severity
        if metrics.is_critical:
            severity = "CRITICAL"
            title = "🚨 CRITICAL: System Error Rate Alert"
        else:
            severity = "WARNING"
            title = "⚠️ WARNING: Elevated System Error Rate"
        
        body = (
            f"System error rate has exceeded the configured threshold.\n\n"
            f"Severity: {severity}\n"
            f"Error Rate: {metrics.error_rate}%\n"
            f"Threshold: {AlertThresholds.get_error_rate_threshold()}%\n"
            f"Total Requests: {metrics.total_requests}\n"
            f"Total Errors: {metrics.total_errors}\n"
            f"Time Window: {metrics.window_start.strftime('%Y-%m-%d %H:%M:%S')} - "
            f"{metrics.window_end.strftime('%Y-%m-%d %H:%M:%S')} UTC\n\n"
            f"Please investigate immediately."
        )
        
        success_count = 0
        
        for admin in admin_users:
            try:
                # Send via email as primary channel for admin alerts
                # with fallback to other channels
                result = await self.notification_service.send_with_fallback(
                    user_id=admin.id,
                    title=title,
                    body=body,
                    channels=[
                        NotificationChannel.EMAIL,
                        NotificationChannel.PUSH,
                        NotificationChannel.SMS,
                    ],
                )
                
                if result.success:
                    success_count += 1
                    logger.info(f"Alert sent to admin {admin.email}")
                else:
                    logger.error(
                        f"Failed to send alert to admin {admin.email}: {result.error}"
                    )
                    
            except Exception as e:
                logger.exception(f"Error sending alert to admin {admin.email}: {e}")
        
        return success_count > 0
    
    async def trigger_manual_alert(
        self,
        title: str,
        message: str,
        severity: str = "INFO",
    ) -> dict:
        """Manually trigger an alert to all admin users.
        
        Useful for custom alerts from other parts of the system.
        
        Args:
            title: Alert title
            message: Alert message body
            severity: Alert severity (INFO, WARNING, CRITICAL)
            
        Returns:
            Dict with alert results
        """
        admin_users = await self.get_admin_users()
        
        if not admin_users:
            return {
                "success": False,
                "error": "No admin users found",
                "admins_notified": 0,
            }
        
        # Add severity prefix to title
        severity_icons = {
            "INFO": "ℹ️",
            "WARNING": "⚠️",
            "CRITICAL": "🚨",
        }
        icon = severity_icons.get(severity.upper(), "ℹ️")
        full_title = f"{icon} {severity.upper()}: {title}"
        
        success_count = 0
        
        for admin in admin_users:
            try:
                result = await self.notification_service.send_with_fallback(
                    user_id=admin.id,
                    title=full_title,
                    body=message,
                    channels=[
                        NotificationChannel.EMAIL,
                        NotificationChannel.PUSH,
                    ],
                )
                
                if result.success:
                    success_count += 1
                    
            except Exception as e:
                logger.exception(f"Error sending manual alert to admin {admin.email}: {e}")
        
        return {
            "success": success_count > 0,
            "admins_notified": success_count,
            "total_admins": len(admin_users),
        }
    
    @classmethod
    def reset_alert_cooldown(cls) -> None:
        """Reset the alert cooldown (useful for testing)."""
        cls._last_alert_time = None
