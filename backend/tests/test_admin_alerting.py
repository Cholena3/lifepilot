"""Tests for admin alerting service.

Validates: Requirements 38.5
"""

from datetime import datetime, timedelta, timezone
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.notification import NotificationChannel
from app.models.user import User
from app.schemas.notification import NotificationSendResult
from app.services.admin_alerting import (
    AdminAlertingService,
    AlertThresholds,
    ErrorMetrics,
)


@pytest.fixture
def mock_db():
    """Create a mock database session."""
    return AsyncMock(spec=AsyncSession)


@pytest.fixture
def mock_notification_service():
    """Create a mock notification service."""
    service = AsyncMock()
    service.send_with_fallback = AsyncMock(
        return_value=NotificationSendResult(
            success=True,
            notification_id=uuid4(),
            channel_used=NotificationChannel.EMAIL,
            channels_attempted=[NotificationChannel.EMAIL],
        )
    )
    return service


@pytest.fixture(autouse=True)
def reset_thresholds():
    """Reset thresholds before and after each test."""
    AlertThresholds.reset_overrides()
    AdminAlertingService.reset_alert_cooldown()
    yield
    AlertThresholds.reset_overrides()
    AdminAlertingService.reset_alert_cooldown()


class TestAlertThresholds:
    """Tests for AlertThresholds configuration."""
    
    def test_default_thresholds_from_settings(self):
        """Test that default thresholds are loaded from settings."""
        # Default values from config.py
        assert AlertThresholds.get_error_rate_threshold() == Decimal("5.0")
        assert AlertThresholds.get_min_requests_for_alert() == 100
        assert AlertThresholds.get_error_rate_window_minutes() == 15
        assert AlertThresholds.get_alert_cooldown_minutes() == 30
        assert AlertThresholds.get_critical_error_rate_threshold() == Decimal("10.0")
    
    def test_set_overrides(self):
        """Test that overrides can be set."""
        AlertThresholds.set_overrides(
            error_rate=Decimal("3.0"),
            min_requests=50,
            window_minutes=10,
            cooldown_minutes=15,
            critical_rate=Decimal("8.0"),
        )
        
        assert AlertThresholds.get_error_rate_threshold() == Decimal("3.0")
        assert AlertThresholds.get_min_requests_for_alert() == 50
        assert AlertThresholds.get_error_rate_window_minutes() == 10
        assert AlertThresholds.get_alert_cooldown_minutes() == 15
        assert AlertThresholds.get_critical_error_rate_threshold() == Decimal("8.0")
    
    def test_reset_overrides(self):
        """Test that overrides can be reset."""
        AlertThresholds.set_overrides(error_rate=Decimal("3.0"))
        AlertThresholds.reset_overrides()
        
        # Should return to default
        assert AlertThresholds.get_error_rate_threshold() == Decimal("5.0")


class TestErrorMetrics:
    """Tests for ErrorMetrics class."""
    
    def test_exceeds_threshold_true(self):
        """Test exceeds_threshold returns True when rate is above threshold."""
        AlertThresholds.set_overrides(error_rate=Decimal("5.0"))
        
        metrics = ErrorMetrics(
            total_requests=100,
            total_errors=10,
            error_rate=Decimal("10.0"),  # 10% > 5%
            window_start=datetime.now(timezone.utc) - timedelta(minutes=15),
            window_end=datetime.now(timezone.utc),
        )
        
        assert metrics.exceeds_threshold is True
    
    def test_exceeds_threshold_false(self):
        """Test exceeds_threshold returns False when rate is below threshold."""
        AlertThresholds.set_overrides(error_rate=Decimal("5.0"))
        
        metrics = ErrorMetrics(
            total_requests=100,
            total_errors=2,
            error_rate=Decimal("2.0"),  # 2% < 5%
            window_start=datetime.now(timezone.utc) - timedelta(minutes=15),
            window_end=datetime.now(timezone.utc),
        )
        
        assert metrics.exceeds_threshold is False
    
    def test_is_critical_true(self):
        """Test is_critical returns True when rate is above critical threshold."""
        AlertThresholds.set_overrides(critical_rate=Decimal("10.0"))
        
        metrics = ErrorMetrics(
            total_requests=100,
            total_errors=15,
            error_rate=Decimal("15.0"),  # 15% > 10%
            window_start=datetime.now(timezone.utc) - timedelta(minutes=15),
            window_end=datetime.now(timezone.utc),
        )
        
        assert metrics.is_critical is True
    
    def test_is_critical_false(self):
        """Test is_critical returns False when rate is below critical threshold."""
        AlertThresholds.set_overrides(critical_rate=Decimal("10.0"))
        
        metrics = ErrorMetrics(
            total_requests=100,
            total_errors=5,
            error_rate=Decimal("5.0"),  # 5% < 10%
            window_start=datetime.now(timezone.utc) - timedelta(minutes=15),
            window_end=datetime.now(timezone.utc),
        )
        
        assert metrics.is_critical is False


class TestAdminAlertingService:
    """Tests for AdminAlertingService."""
    
    @pytest.mark.asyncio
    async def test_get_admin_users(self, mock_db):
        """Test getting admin users."""
        # Setup mock
        admin_user = MagicMock(spec=User)
        admin_user.id = uuid4()
        admin_user.email = "admin@example.com"
        admin_user.is_admin = True
        
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [admin_user]
        mock_db.execute = AsyncMock(return_value=mock_result)
        
        service = AdminAlertingService(mock_db)
        admins = await service.get_admin_users()
        
        assert len(admins) == 1
        assert admins[0].email == "admin@example.com"
    
    @pytest.mark.asyncio
    async def test_check_and_alert_insufficient_requests(self, mock_db):
        """Test that alerts are skipped when requests are below minimum."""
        AlertThresholds.set_overrides(min_requests=100)
        
        service = AdminAlertingService(mock_db)
        
        # Create metrics with insufficient requests
        metrics = ErrorMetrics(
            total_requests=50,  # Below minimum of 100
            total_errors=10,
            error_rate=Decimal("20.0"),
            window_start=datetime.now(timezone.utc) - timedelta(minutes=15),
            window_end=datetime.now(timezone.utc),
        )
        
        result = await service.check_and_alert(metrics=metrics)
        
        assert result["alert_sent"] is False
        assert "Insufficient requests" in result["alert_skipped_reason"]
    
    @pytest.mark.asyncio
    async def test_check_and_alert_within_threshold(self, mock_db):
        """Test that alerts are skipped when error rate is within threshold."""
        AlertThresholds.set_overrides(
            error_rate=Decimal("5.0"),
            min_requests=10,
        )
        
        service = AdminAlertingService(mock_db)
        
        # Create metrics within threshold
        metrics = ErrorMetrics(
            total_requests=100,
            total_errors=2,
            error_rate=Decimal("2.0"),  # Below 5% threshold
            window_start=datetime.now(timezone.utc) - timedelta(minutes=15),
            window_end=datetime.now(timezone.utc),
        )
        
        result = await service.check_and_alert(metrics=metrics)
        
        assert result["alert_sent"] is False
        assert "within acceptable limits" in result["alert_skipped_reason"]
    
    @pytest.mark.asyncio
    async def test_check_and_alert_sends_alert(self, mock_db, mock_notification_service):
        """Test that alerts are sent when error rate exceeds threshold."""
        AlertThresholds.set_overrides(
            error_rate=Decimal("5.0"),
            min_requests=10,
            cooldown_minutes=0,  # No cooldown for test
        )
        
        # Setup admin user
        admin_user = MagicMock(spec=User)
        admin_user.id = uuid4()
        admin_user.email = "admin@example.com"
        
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [admin_user]
        mock_db.execute = AsyncMock(return_value=mock_result)
        
        service = AdminAlertingService(mock_db)
        service.notification_service = mock_notification_service
        
        # Create metrics exceeding threshold
        metrics = ErrorMetrics(
            total_requests=100,
            total_errors=10,
            error_rate=Decimal("10.0"),  # Above 5% threshold
            window_start=datetime.now(timezone.utc) - timedelta(minutes=15),
            window_end=datetime.now(timezone.utc),
        )
        
        result = await service.check_and_alert(metrics=metrics)
        
        assert result["alert_sent"] is True
        assert result["exceeds_threshold"] is True
        mock_notification_service.send_with_fallback.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_check_and_alert_cooldown(self, mock_db, mock_notification_service):
        """Test that alerts are suppressed during cooldown period."""
        AlertThresholds.set_overrides(
            error_rate=Decimal("5.0"),
            min_requests=10,
            cooldown_minutes=30,
        )
        
        # Setup admin user
        admin_user = MagicMock(spec=User)
        admin_user.id = uuid4()
        admin_user.email = "admin@example.com"
        
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [admin_user]
        mock_db.execute = AsyncMock(return_value=mock_result)
        
        service = AdminAlertingService(mock_db)
        service.notification_service = mock_notification_service
        
        # Create metrics exceeding threshold
        metrics = ErrorMetrics(
            total_requests=100,
            total_errors=10,
            error_rate=Decimal("10.0"),
            window_start=datetime.now(timezone.utc) - timedelta(minutes=15),
            window_end=datetime.now(timezone.utc),
        )
        
        # First alert should be sent
        result1 = await service.check_and_alert(metrics=metrics)
        assert result1["alert_sent"] is True
        
        # Second alert should be suppressed due to cooldown
        result2 = await service.check_and_alert(metrics=metrics)
        assert result2["alert_sent"] is False
        assert "cooldown" in result2["alert_skipped_reason"]
    
    @pytest.mark.asyncio
    async def test_check_and_alert_critical_severity(self, mock_db, mock_notification_service):
        """Test that critical alerts are identified correctly."""
        AlertThresholds.set_overrides(
            error_rate=Decimal("5.0"),
            critical_rate=Decimal("10.0"),
            min_requests=10,
            cooldown_minutes=0,
        )
        
        # Setup admin user
        admin_user = MagicMock(spec=User)
        admin_user.id = uuid4()
        admin_user.email = "admin@example.com"
        
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [admin_user]
        mock_db.execute = AsyncMock(return_value=mock_result)
        
        service = AdminAlertingService(mock_db)
        service.notification_service = mock_notification_service
        
        # Create metrics at critical level
        metrics = ErrorMetrics(
            total_requests=100,
            total_errors=15,
            error_rate=Decimal("15.0"),  # Above 10% critical threshold
            window_start=datetime.now(timezone.utc) - timedelta(minutes=15),
            window_end=datetime.now(timezone.utc),
        )
        
        result = await service.check_and_alert(metrics=metrics)
        
        assert result["is_critical"] is True
        assert result["alert_sent"] is True
    
    @pytest.mark.asyncio
    async def test_trigger_manual_alert(self, mock_db, mock_notification_service):
        """Test manual alert triggering."""
        # Setup admin user
        admin_user = MagicMock(spec=User)
        admin_user.id = uuid4()
        admin_user.email = "admin@example.com"
        
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [admin_user]
        mock_db.execute = AsyncMock(return_value=mock_result)
        
        service = AdminAlertingService(mock_db)
        service.notification_service = mock_notification_service
        
        result = await service.trigger_manual_alert(
            title="Test Alert",
            message="This is a test alert message",
            severity="WARNING",
        )
        
        assert result["success"] is True
        assert result["admins_notified"] == 1
        mock_notification_service.send_with_fallback.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_trigger_manual_alert_no_admins(self, mock_db):
        """Test manual alert when no admin users exist."""
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_db.execute = AsyncMock(return_value=mock_result)
        
        service = AdminAlertingService(mock_db)
        
        result = await service.trigger_manual_alert(
            title="Test Alert",
            message="This is a test alert message",
        )
        
        assert result["success"] is False
        assert "No admin users found" in result["error"]
    
    def test_reset_alert_cooldown(self):
        """Test resetting the alert cooldown."""
        # Set a last alert time
        AdminAlertingService._last_alert_time = datetime.now(timezone.utc)
        
        # Reset it
        AdminAlertingService.reset_alert_cooldown()
        
        assert AdminAlertingService._last_alert_time is None
    
    @pytest.mark.asyncio
    async def test_get_error_metrics(self, mock_db):
        """Test getting error metrics."""
        service = AdminAlertingService(mock_db)
        
        metrics = await service.get_error_metrics(window_minutes=15)
        
        assert metrics.total_requests == 0  # Placeholder returns 0
        assert metrics.total_errors == 0
        assert metrics.error_rate == Decimal("0.00")
        assert metrics.window_start < metrics.window_end


class TestAlertSeverityIcons:
    """Tests for alert severity icons in manual alerts."""
    
    @pytest.mark.asyncio
    async def test_info_severity_icon(self, mock_db, mock_notification_service):
        """Test INFO severity uses correct icon."""
        admin_user = MagicMock(spec=User)
        admin_user.id = uuid4()
        admin_user.email = "admin@example.com"
        
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [admin_user]
        mock_db.execute = AsyncMock(return_value=mock_result)
        
        service = AdminAlertingService(mock_db)
        service.notification_service = mock_notification_service
        
        await service.trigger_manual_alert(
            title="Test",
            message="Test message",
            severity="INFO",
        )
        
        call_args = mock_notification_service.send_with_fallback.call_args
        assert "ℹ️" in call_args.kwargs["title"]
    
    @pytest.mark.asyncio
    async def test_warning_severity_icon(self, mock_db, mock_notification_service):
        """Test WARNING severity uses correct icon."""
        admin_user = MagicMock(spec=User)
        admin_user.id = uuid4()
        admin_user.email = "admin@example.com"
        
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [admin_user]
        mock_db.execute = AsyncMock(return_value=mock_result)
        
        service = AdminAlertingService(mock_db)
        service.notification_service = mock_notification_service
        
        await service.trigger_manual_alert(
            title="Test",
            message="Test message",
            severity="WARNING",
        )
        
        call_args = mock_notification_service.send_with_fallback.call_args
        assert "⚠️" in call_args.kwargs["title"]
    
    @pytest.mark.asyncio
    async def test_critical_severity_icon(self, mock_db, mock_notification_service):
        """Test CRITICAL severity uses correct icon."""
        admin_user = MagicMock(spec=User)
        admin_user.id = uuid4()
        admin_user.email = "admin@example.com"
        
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [admin_user]
        mock_db.execute = AsyncMock(return_value=mock_result)
        
        service = AdminAlertingService(mock_db)
        service.notification_service = mock_notification_service
        
        await service.trigger_manual_alert(
            title="Test",
            message="Test message",
            severity="CRITICAL",
        )
        
        call_args = mock_notification_service.send_with_fallback.call_args
        assert "🚨" in call_args.kwargs["title"]
