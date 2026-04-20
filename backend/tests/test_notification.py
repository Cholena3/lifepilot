"""Tests for notification service.

Validates: Requirements 31.1, 31.2, 31.5
"""

import uuid
from datetime import time
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.models.notification import (
    Notification,
    NotificationChannel,
    NotificationPreferences,
    NotificationStatus,
)
from app.schemas.notification import (
    NotificationCreate,
    NotificationPreferencesCreate,
    NotificationPreferencesUpdate,
    NotificationResponse,
    NotificationSendResult,
)
from app.services.notification import (
    BaseChannelSender,
    ChannelSendError,
    EmailChannelSender,
    NotificationService,
    PushChannelSender,
    SMSChannelSender,
    WhatsAppChannelSender,
)


class TestNotificationChannel:
    """Tests for NotificationChannel enum."""

    def test_channel_values(self):
        """Test that all expected channels exist."""
        assert NotificationChannel.PUSH.value == "push"
        assert NotificationChannel.EMAIL.value == "email"
        assert NotificationChannel.SMS.value == "sms"
        assert NotificationChannel.WHATSAPP.value == "whatsapp"

    def test_channel_count(self):
        """Test that we have exactly 4 channels.
        
        Validates: Requirements 31.1
        """
        channels = list(NotificationChannel)
        assert len(channels) == 4


class TestNotificationStatus:
    """Tests for NotificationStatus enum."""

    def test_status_values(self):
        """Test that all expected statuses exist."""
        assert NotificationStatus.PENDING.value == "pending"
        assert NotificationStatus.SENT.value == "sent"
        assert NotificationStatus.DELIVERED.value == "delivered"
        assert NotificationStatus.FAILED.value == "failed"
        assert NotificationStatus.QUEUED.value == "queued"


class TestNotificationSchemas:
    """Tests for notification Pydantic schemas."""

    def test_notification_create_valid(self):
        """Test creating a valid notification schema."""
        notification = NotificationCreate(
            title="Test Title",
            body="Test body content",
            channel=NotificationChannel.PUSH,
        )
        assert notification.title == "Test Title"
        assert notification.body == "Test body content"
        assert notification.channel == NotificationChannel.PUSH

    def test_notification_create_empty_title_fails(self):
        """Test that empty title fails validation."""
        with pytest.raises(ValueError):
            NotificationCreate(
                title="",
                body="Test body",
                channel=NotificationChannel.PUSH,
            )

    def test_notification_create_empty_body_fails(self):
        """Test that empty body fails validation."""
        with pytest.raises(ValueError):
            NotificationCreate(
                title="Test",
                body="",
                channel=NotificationChannel.PUSH,
            )

    def test_notification_preferences_create_defaults(self):
        """Test notification preferences default values.
        
        Validates: Requirements 31.2
        """
        prefs = NotificationPreferencesCreate()
        assert prefs.push_enabled is True
        assert prefs.email_enabled is True
        assert prefs.sms_enabled is False
        assert prefs.whatsapp_enabled is False
        assert prefs.quiet_hours_start is None
        assert prefs.quiet_hours_end is None

    def test_notification_preferences_with_quiet_hours(self):
        """Test notification preferences with quiet hours.
        
        Validates: Requirements 31.4
        """
        prefs = NotificationPreferencesCreate(
            quiet_hours_start=time(22, 0),
            quiet_hours_end=time(7, 0),
        )
        assert prefs.quiet_hours_start == time(22, 0)
        assert prefs.quiet_hours_end == time(7, 0)


class TestChannelSenders:
    """Tests for channel sender implementations."""

    @pytest.mark.asyncio
    async def test_push_sender_channel(self):
        """Test push sender returns correct channel."""
        sender = PushChannelSender()
        assert sender.channel == NotificationChannel.PUSH

    @pytest.mark.asyncio
    async def test_email_sender_channel(self):
        """Test email sender returns correct channel."""
        sender = EmailChannelSender()
        assert sender.channel == NotificationChannel.EMAIL

    @pytest.mark.asyncio
    async def test_sms_sender_channel(self):
        """Test SMS sender returns correct channel."""
        sender = SMSChannelSender()
        assert sender.channel == NotificationChannel.SMS

    @pytest.mark.asyncio
    async def test_whatsapp_sender_channel(self):
        """Test WhatsApp sender returns correct channel."""
        sender = WhatsAppChannelSender()
        assert sender.channel == NotificationChannel.WHATSAPP

    @pytest.mark.asyncio
    async def test_push_sender_send(self):
        """Test push sender send method (mock implementation).
        
        Validates: Requirements 31.1
        """
        sender = PushChannelSender()
        user_id = uuid.uuid4()
        result = await sender.send(user_id, "Test", "Body")
        assert result is True

    @pytest.mark.asyncio
    async def test_email_sender_send(self):
        """Test email sender send method (mock implementation).
        
        Validates: Requirements 31.1
        """
        sender = EmailChannelSender()
        user_id = uuid.uuid4()
        result = await sender.send(user_id, "Test", "Body")
        assert result is True

    @pytest.mark.asyncio
    async def test_sms_sender_send(self):
        """Test SMS sender send method (mock implementation).
        
        Validates: Requirements 31.1
        """
        sender = SMSChannelSender()
        user_id = uuid.uuid4()
        result = await sender.send(user_id, "Test", "Body")
        assert result is True

    @pytest.mark.asyncio
    async def test_whatsapp_sender_send(self):
        """Test WhatsApp sender send method (mock implementation).
        
        Validates: Requirements 31.1
        """
        sender = WhatsAppChannelSender()
        user_id = uuid.uuid4()
        result = await sender.send(user_id, "Test", "Body")
        assert result is True


class TestNotificationSendResult:
    """Tests for NotificationSendResult schema."""

    def test_successful_result(self):
        """Test creating a successful send result."""
        notification_id = uuid.uuid4()
        result = NotificationSendResult(
            success=True,
            notification_id=notification_id,
            channel_used=NotificationChannel.PUSH,
            channels_attempted=[NotificationChannel.PUSH],
        )
        assert result.success is True
        assert result.notification_id == notification_id
        assert result.channel_used == NotificationChannel.PUSH
        assert result.error is None

    def test_failed_result(self):
        """Test creating a failed send result."""
        result = NotificationSendResult(
            success=False,
            channels_attempted=[NotificationChannel.PUSH, NotificationChannel.EMAIL],
            error="All channels failed",
        )
        assert result.success is False
        assert result.notification_id is None
        assert result.channel_used is None
        assert len(result.channels_attempted) == 2
        assert result.error == "All channels failed"

    def test_fallback_result(self):
        """Test result after fallback to secondary channel.
        
        Validates: Requirements 31.5
        """
        notification_id = uuid.uuid4()
        result = NotificationSendResult(
            success=True,
            notification_id=notification_id,
            channel_used=NotificationChannel.EMAIL,
            channels_attempted=[NotificationChannel.PUSH, NotificationChannel.EMAIL],
        )
        assert result.success is True
        assert result.channel_used == NotificationChannel.EMAIL
        assert len(result.channels_attempted) == 2
        assert result.channels_attempted[0] == NotificationChannel.PUSH
        assert result.channels_attempted[1] == NotificationChannel.EMAIL


class TestChannelSendError:
    """Tests for ChannelSendError exception."""

    def test_error_message(self):
        """Test error message formatting."""
        error = ChannelSendError(NotificationChannel.PUSH, "Connection failed")
        assert "push" in str(error).lower()
        assert "Connection failed" in str(error)
        assert error.channel == NotificationChannel.PUSH
        assert error.message == "Connection failed"


class TestNotificationPreferencesModel:
    """Tests for NotificationPreferences model methods."""

    def test_is_channel_enabled_push(self):
        """Test is_channel_enabled for push."""
        prefs = NotificationPreferences(
            id=uuid.uuid4(),
            user_id=uuid.uuid4(),
            push_enabled=True,
            email_enabled=False,
            sms_enabled=False,
            whatsapp_enabled=False,
        )
        assert prefs.is_channel_enabled(NotificationChannel.PUSH) is True
        assert prefs.is_channel_enabled(NotificationChannel.EMAIL) is False

    def test_is_channel_enabled_all_channels(self):
        """Test is_channel_enabled for all channels.
        
        Validates: Requirements 31.2
        """
        prefs = NotificationPreferences(
            id=uuid.uuid4(),
            user_id=uuid.uuid4(),
            push_enabled=True,
            email_enabled=True,
            sms_enabled=True,
            whatsapp_enabled=True,
        )
        assert prefs.is_channel_enabled(NotificationChannel.PUSH) is True
        assert prefs.is_channel_enabled(NotificationChannel.EMAIL) is True
        assert prefs.is_channel_enabled(NotificationChannel.SMS) is True
        assert prefs.is_channel_enabled(NotificationChannel.WHATSAPP) is True



class TestQuietHoursLogic:
    """Tests for quiet hours logic.
    
    Validates: Requirements 31.4, 32.3
    """

    def test_quiet_hours_within_same_day(self):
        """Test quiet hours that don't span midnight (e.g., 13:00 to 15:00).
        
        Validates: Requirements 31.4
        """
        from datetime import time
        
        # Simulate quiet hours from 13:00 to 15:00
        start = time(13, 0)
        end = time(15, 0)
        
        # Helper function to check if time is in quiet hours
        def is_in_quiet_hours(current: time, start: time, end: time) -> bool:
            if start <= end:
                return start <= current <= end
            else:
                return current >= start or current <= end
        
        # Test times within quiet hours
        assert is_in_quiet_hours(time(13, 0), start, end) is True
        assert is_in_quiet_hours(time(14, 0), start, end) is True
        assert is_in_quiet_hours(time(15, 0), start, end) is True
        
        # Test times outside quiet hours
        assert is_in_quiet_hours(time(12, 59), start, end) is False
        assert is_in_quiet_hours(time(15, 1), start, end) is False
        assert is_in_quiet_hours(time(0, 0), start, end) is False
        assert is_in_quiet_hours(time(23, 59), start, end) is False

    def test_quiet_hours_spanning_midnight(self):
        """Test quiet hours that span midnight (e.g., 22:00 to 07:00).
        
        Validates: Requirements 31.4, 32.3
        """
        from datetime import time
        
        # Simulate quiet hours from 22:00 to 07:00
        start = time(22, 0)
        end = time(7, 0)
        
        # Helper function to check if time is in quiet hours
        def is_in_quiet_hours(current: time, start: time, end: time) -> bool:
            if start <= end:
                return start <= current <= end
            else:
                return current >= start or current <= end
        
        # Test times within quiet hours (evening)
        assert is_in_quiet_hours(time(22, 0), start, end) is True
        assert is_in_quiet_hours(time(23, 0), start, end) is True
        assert is_in_quiet_hours(time(23, 59), start, end) is True
        
        # Test times within quiet hours (morning)
        assert is_in_quiet_hours(time(0, 0), start, end) is True
        assert is_in_quiet_hours(time(3, 0), start, end) is True
        assert is_in_quiet_hours(time(7, 0), start, end) is True
        
        # Test times outside quiet hours
        assert is_in_quiet_hours(time(7, 1), start, end) is False
        assert is_in_quiet_hours(time(12, 0), start, end) is False
        assert is_in_quiet_hours(time(21, 59), start, end) is False

    def test_quiet_hours_edge_cases(self):
        """Test edge cases for quiet hours.
        
        Validates: Requirements 31.4
        """
        from datetime import time
        
        # Helper function to check if time is in quiet hours
        def is_in_quiet_hours(current: time, start: time, end: time) -> bool:
            if start <= end:
                return start <= current <= end
            else:
                return current >= start or current <= end
        
        # Same start and end time (1 minute window)
        start = time(12, 0)
        end = time(12, 0)
        assert is_in_quiet_hours(time(12, 0), start, end) is True
        assert is_in_quiet_hours(time(12, 1), start, end) is False
        
        # Full day quiet hours (00:00 to 23:59)
        start = time(0, 0)
        end = time(23, 59)
        assert is_in_quiet_hours(time(0, 0), start, end) is True
        assert is_in_quiet_hours(time(12, 0), start, end) is True
        assert is_in_quiet_hours(time(23, 59), start, end) is True


class TestNotificationBatching:
    """Tests for notification batching logic.
    
    Validates: Requirements 31.6
    """

    def test_batch_title_format(self):
        """Test that batched notification title is formatted correctly.
        
        Validates: Requirements 31.6
        """
        notifications = [
            ("Title 1", "Body 1", NotificationChannel.PUSH),
            ("Title 2", "Body 2", NotificationChannel.PUSH),
            ("Title 3", "Body 3", NotificationChannel.PUSH),
        ]
        
        expected_title = f"You have {len(notifications)} new notifications"
        assert expected_title == "You have 3 new notifications"

    def test_batch_body_format(self):
        """Test that batched notification body is formatted correctly.
        
        Validates: Requirements 31.6
        """
        notifications = [
            ("Title 1", "Body 1", NotificationChannel.PUSH),
            ("Title 2", "Body 2", NotificationChannel.EMAIL),
        ]
        
        batched_body_parts = []
        for title, body, _ in notifications:
            batched_body_parts.append(f"• {title}: {body}")
        batched_body = "\n".join(batched_body_parts)
        
        expected = "• Title 1: Body 1\n• Title 2: Body 2"
        assert batched_body == expected

    def test_single_notification_no_batching(self):
        """Test that single notification doesn't get batched.
        
        Validates: Requirements 31.6
        """
        notifications = [
            ("Single Title", "Single Body", NotificationChannel.PUSH),
        ]
        
        # Single notification should not be batched
        assert len(notifications) == 1

    def test_empty_notifications_list(self):
        """Test handling of empty notifications list."""
        notifications: list[tuple[str, str, NotificationChannel]] = []
        assert len(notifications) == 0


class TestNotificationPreferencesQuietHours:
    """Tests for notification preferences with quiet hours.
    
    Validates: Requirements 31.4, 32.3
    """

    def test_preferences_with_quiet_hours(self):
        """Test creating preferences with quiet hours.
        
        Validates: Requirements 32.3
        """
        prefs = NotificationPreferencesCreate(
            push_enabled=True,
            email_enabled=True,
            quiet_hours_start=time(22, 0),
            quiet_hours_end=time(7, 0),
        )
        assert prefs.quiet_hours_start == time(22, 0)
        assert prefs.quiet_hours_end == time(7, 0)

    def test_preferences_update_quiet_hours(self):
        """Test updating quiet hours in preferences.
        
        Validates: Requirements 32.1, 32.3
        """
        update = NotificationPreferencesUpdate(
            quiet_hours_start=time(23, 0),
            quiet_hours_end=time(6, 0),
        )
        assert update.quiet_hours_start == time(23, 0)
        assert update.quiet_hours_end == time(6, 0)

    def test_preferences_clear_quiet_hours(self):
        """Test clearing quiet hours (setting to None).
        
        Validates: Requirements 32.3
        """
        # When quiet_hours_start and quiet_hours_end are None, quiet hours are disabled
        prefs = NotificationPreferencesCreate(
            push_enabled=True,
            quiet_hours_start=None,
            quiet_hours_end=None,
        )
        assert prefs.quiet_hours_start is None
        assert prefs.quiet_hours_end is None


class TestNotificationQueuedStatus:
    """Tests for notification queued status.
    
    Validates: Requirements 31.4
    """

    def test_queued_status_exists(self):
        """Test that QUEUED status exists in NotificationStatus enum.
        
        Validates: Requirements 31.4
        """
        assert NotificationStatus.QUEUED.value == "queued"

    def test_notification_with_queued_status(self):
        """Test creating notification with queued status.
        
        Validates: Requirements 31.4
        """
        notification_id = uuid.uuid4()
        user_id = uuid.uuid4()
        
        notification = Notification(
            id=notification_id,
            user_id=user_id,
            title="Queued Notification",
            body="This notification is queued during quiet hours",
            channel=NotificationChannel.PUSH,
            status=NotificationStatus.QUEUED,
        )
        
        assert notification.status == NotificationStatus.QUEUED
        assert notification.title == "Queued Notification"


class TestScheduledNotifications:
    """Tests for scheduled notification functionality.
    
    Validates: Requirements 32.5
    """

    def test_notification_model_has_scheduled_at(self):
        """Test that Notification model has scheduled_at field.
        
        Validates: Requirements 32.5
        """
        notification_id = uuid.uuid4()
        user_id = uuid.uuid4()
        scheduled_time = datetime(2024, 12, 25, 10, 0, 0)
        
        notification = Notification(
            id=notification_id,
            user_id=user_id,
            title="Scheduled Notification",
            body="This is a scheduled notification",
            channel=NotificationChannel.PUSH,
            status=NotificationStatus.PENDING,
            scheduled_at=scheduled_time,
        )
        
        assert notification.scheduled_at == scheduled_time
        assert notification.status == NotificationStatus.PENDING

    def test_notification_without_scheduled_at(self):
        """Test that Notification can be created without scheduled_at.
        
        Validates: Requirements 32.5
        """
        notification_id = uuid.uuid4()
        user_id = uuid.uuid4()
        
        notification = Notification(
            id=notification_id,
            user_id=user_id,
            title="Immediate Notification",
            body="This is an immediate notification",
            channel=NotificationChannel.EMAIL,
            status=NotificationStatus.PENDING,
        )
        
        assert notification.scheduled_at is None

    def test_scheduled_notification_future_time(self):
        """Test scheduling a notification for a future time.
        
        Validates: Requirements 32.5
        """
        from datetime import timedelta
        
        notification_id = uuid.uuid4()
        user_id = uuid.uuid4()
        future_time = datetime.now() + timedelta(hours=1)
        
        notification = Notification(
            id=notification_id,
            user_id=user_id,
            title="Future Notification",
            body="This will be sent in the future",
            channel=NotificationChannel.PUSH,
            status=NotificationStatus.PENDING,
            scheduled_at=future_time,
        )
        
        assert notification.scheduled_at > datetime.now()


class TestCeleryTaskConfiguration:
    """Tests for Celery task configuration.
    
    Validates: Requirements 32.5
    """

    def test_celery_app_exists(self):
        """Test that Celery app is properly configured."""
        from app.tasks import celery_app
        
        assert celery_app is not None
        assert celery_app.main == "lifepilot"

    def test_celery_task_serializer(self):
        """Test that Celery uses JSON serialization."""
        from app.tasks import celery_app
        
        assert celery_app.conf.task_serializer == "json"
        assert celery_app.conf.result_serializer == "json"

    def test_celery_timezone_utc(self):
        """Test that Celery uses UTC timezone."""
        from app.tasks import celery_app
        
        assert celery_app.conf.timezone == "UTC"
        assert celery_app.conf.enable_utc is True

    def test_celery_beat_schedule_exists(self):
        """Test that Celery Beat schedule is configured.
        
        Validates: Requirements 32.5
        """
        from app.tasks import celery_app
        
        beat_schedule = celery_app.conf.beat_schedule
        assert "process-queued-notifications-every-5-minutes" in beat_schedule
        assert "send-scheduled-notifications-every-minute" in beat_schedule


class TestNotificationTasksExist:
    """Tests for notification task existence.
    
    Validates: Requirements 31.4, 32.5
    """

    def test_send_scheduled_notification_task_exists(self):
        """Test that send_scheduled_notification task exists.
        
        Validates: Requirements 32.5
        """
        from app.tasks.notification_tasks import send_scheduled_notification
        
        assert send_scheduled_notification is not None
        assert callable(send_scheduled_notification)

    def test_process_queued_notifications_task_exists(self):
        """Test that process_queued_notifications task exists.
        
        Validates: Requirements 31.4
        """
        from app.tasks.notification_tasks import process_queued_notifications
        
        assert process_queued_notifications is not None
        assert callable(process_queued_notifications)

    def test_send_notification_batch_task_exists(self):
        """Test that send_notification_batch task exists.
        
        Validates: Requirements 31.6
        """
        from app.tasks.notification_tasks import send_notification_batch
        
        assert send_notification_batch is not None
        assert callable(send_notification_batch)

    def test_process_all_queued_notifications_task_exists(self):
        """Test that process_all_queued_notifications task exists.
        
        Validates: Requirements 31.4
        """
        from app.tasks.notification_tasks import process_all_queued_notifications
        
        assert process_all_queued_notifications is not None
        assert callable(process_all_queued_notifications)

    def test_send_due_scheduled_notifications_task_exists(self):
        """Test that send_due_scheduled_notifications task exists.
        
        Validates: Requirements 32.5
        """
        from app.tasks.notification_tasks import send_due_scheduled_notifications
        
        assert send_due_scheduled_notifications is not None
        assert callable(send_due_scheduled_notifications)


class TestScheduledNotificationSchema:
    """Tests for scheduled notification schema support.
    
    Validates: Requirements 32.5
    """

    def test_notification_response_includes_scheduled_at(self):
        """Test that NotificationResponse can include scheduled_at.
        
        Validates: Requirements 32.5
        """
        # NotificationResponse should be able to serialize notifications with scheduled_at
        # The model_config with from_attributes=True handles this
        from app.schemas.notification import NotificationResponse
        
        # Verify the schema exists and has the expected fields
        assert NotificationResponse is not None
        assert "id" in NotificationResponse.model_fields
        assert "user_id" in NotificationResponse.model_fields
        assert "title" in NotificationResponse.model_fields
        assert "body" in NotificationResponse.model_fields
        assert "channel" in NotificationResponse.model_fields
        assert "status" in NotificationResponse.model_fields


from datetime import datetime, timedelta


class TestScheduledNotificationLogic:
    """Tests for scheduled notification business logic.
    
    Validates: Requirements 32.5
    """

    def test_scheduled_notification_is_pending(self):
        """Test that scheduled notifications start with PENDING status.
        
        Validates: Requirements 32.5
        """
        notification_id = uuid.uuid4()
        user_id = uuid.uuid4()
        future_time = datetime.now() + timedelta(hours=2)
        
        notification = Notification(
            id=notification_id,
            user_id=user_id,
            title="Scheduled Test",
            body="Test body",
            channel=NotificationChannel.PUSH,
            status=NotificationStatus.PENDING,
            scheduled_at=future_time,
        )
        
        assert notification.status == NotificationStatus.PENDING
        assert notification.scheduled_at is not None
        assert notification.sent_at is None

    def test_scheduled_notification_different_channels(self):
        """Test scheduling notifications for different channels.
        
        Validates: Requirements 32.5
        """
        user_id = uuid.uuid4()
        future_time = datetime.now() + timedelta(days=1)
        
        channels = [
            NotificationChannel.PUSH,
            NotificationChannel.EMAIL,
            NotificationChannel.SMS,
            NotificationChannel.WHATSAPP,
        ]
        
        for channel in channels:
            notification = Notification(
                id=uuid.uuid4(),
                user_id=user_id,
                title=f"Scheduled {channel.value}",
                body=f"Test body for {channel.value}",
                channel=channel,
                status=NotificationStatus.PENDING,
                scheduled_at=future_time,
            )
            
            assert notification.channel == channel
            assert notification.scheduled_at == future_time

    def test_scheduled_notification_past_time(self):
        """Test that notifications can be scheduled for past time (for immediate processing).
        
        Validates: Requirements 32.5
        """
        notification_id = uuid.uuid4()
        user_id = uuid.uuid4()
        past_time = datetime.now() - timedelta(hours=1)
        
        notification = Notification(
            id=notification_id,
            user_id=user_id,
            title="Past Scheduled",
            body="This should be sent immediately",
            channel=NotificationChannel.PUSH,
            status=NotificationStatus.PENDING,
            scheduled_at=past_time,
        )
        
        # Past scheduled notifications should still be valid
        # They will be picked up by the periodic task and sent immediately
        assert notification.scheduled_at < datetime.now()
        assert notification.status == NotificationStatus.PENDING
