"""Notification service for multi-channel notification delivery.

Validates: Requirements 31.1, 31.2, 31.3, 31.4, 31.5, 31.6, 32.1, 32.2, 32.3, 32.4
"""

import logging
from abc import ABC, abstractmethod
from datetime import datetime, time, timezone
from typing import Optional
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.notification import (
    Notification,
    NotificationChannel,
    NotificationPreferences,
    NotificationStatus,
)
from app.repositories.notification import (
    NotificationPreferencesRepository,
    NotificationRepository,
)
from app.schemas.notification import NotificationSendResult

logger = logging.getLogger(__name__)


class ChannelSendError(Exception):
    """Exception raised when a channel fails to send a notification."""
    
    def __init__(self, channel: NotificationChannel, message: str):
        self.channel = channel
        self.message = message
        super().__init__(f"Failed to send via {channel.value}: {message}")


class BaseChannelSender(ABC):
    """Abstract base class for channel-specific notification senders."""
    
    @property
    @abstractmethod
    def channel(self) -> NotificationChannel:
        """Return the channel this sender handles."""
        pass
    
    @abstractmethod
    async def send(
        self,
        user_id: UUID,
        title: str,
        body: str,
        **kwargs,
    ) -> bool:
        """Send a notification via this channel.
        
        Args:
            user_id: Target user's UUID
            title: Notification title
            body: Notification body content
            **kwargs: Additional channel-specific parameters
            
        Returns:
            True if sent successfully, False otherwise
            
        Raises:
            ChannelSendError: If sending fails
        """
        pass


class PushChannelSender(BaseChannelSender):
    """Push notification sender (mock implementation).
    
    Validates: Requirements 31.1
    """
    
    @property
    def channel(self) -> NotificationChannel:
        return NotificationChannel.PUSH
    
    async def send(
        self,
        user_id: UUID,
        title: str,
        body: str,
        **kwargs,
    ) -> bool:
        """Send a push notification.
        
        This is a mock implementation. In production, this would integrate
        with Firebase Cloud Messaging, Apple Push Notification Service, etc.
        
        Args:
            user_id: Target user's UUID
            title: Notification title
            body: Notification body content
            **kwargs: Additional parameters (e.g., device_token)
            
        Returns:
            True if sent successfully
            
        Raises:
            ChannelSendError: If sending fails
        """
        logger.info(f"[MOCK] Sending push notification to user {user_id}: {title}")
        # Mock implementation - always succeeds
        # In production: integrate with FCM/APNS
        return True


class EmailChannelSender(BaseChannelSender):
    """Email notification sender (mock implementation).
    
    Validates: Requirements 31.1
    """
    
    @property
    def channel(self) -> NotificationChannel:
        return NotificationChannel.EMAIL
    
    async def send(
        self,
        user_id: UUID,
        title: str,
        body: str,
        **kwargs,
    ) -> bool:
        """Send an email notification.
        
        This is a mock implementation. In production, this would integrate
        with SendGrid, AWS SES, or similar email service.
        
        Args:
            user_id: Target user's UUID
            title: Notification title (used as subject)
            body: Notification body content
            **kwargs: Additional parameters (e.g., email_address)
            
        Returns:
            True if sent successfully
            
        Raises:
            ChannelSendError: If sending fails
        """
        logger.info(f"[MOCK] Sending email to user {user_id}: {title}")
        # Mock implementation - always succeeds
        # In production: integrate with email service
        return True


class SMSChannelSender(BaseChannelSender):
    """SMS notification sender (mock implementation).
    
    Validates: Requirements 31.1
    """
    
    @property
    def channel(self) -> NotificationChannel:
        return NotificationChannel.SMS
    
    async def send(
        self,
        user_id: UUID,
        title: str,
        body: str,
        **kwargs,
    ) -> bool:
        """Send an SMS notification.
        
        This is a mock implementation. In production, this would integrate
        with Twilio, AWS SNS, or similar SMS service.
        
        Args:
            user_id: Target user's UUID
            title: Notification title (prepended to body)
            body: Notification body content
            **kwargs: Additional parameters (e.g., phone_number)
            
        Returns:
            True if sent successfully
            
        Raises:
            ChannelSendError: If sending fails
        """
        logger.info(f"[MOCK] Sending SMS to user {user_id}: {title}")
        # Mock implementation - always succeeds
        # In production: integrate with SMS gateway
        return True


class WhatsAppChannelSender(BaseChannelSender):
    """WhatsApp notification sender (mock implementation).
    
    Validates: Requirements 31.1
    """
    
    @property
    def channel(self) -> NotificationChannel:
        return NotificationChannel.WHATSAPP
    
    async def send(
        self,
        user_id: UUID,
        title: str,
        body: str,
        **kwargs,
    ) -> bool:
        """Send a WhatsApp notification.
        
        This is a mock implementation. In production, this would integrate
        with WhatsApp Business API.
        
        Args:
            user_id: Target user's UUID
            title: Notification title
            body: Notification body content
            **kwargs: Additional parameters (e.g., phone_number)
            
        Returns:
            True if sent successfully
            
        Raises:
            ChannelSendError: If sending fails
        """
        logger.info(f"[MOCK] Sending WhatsApp message to user {user_id}: {title}")
        # Mock implementation - always succeeds
        # In production: integrate with WhatsApp Business API
        return True


class NotificationService:
    """Service for sending notifications via multiple channels.
    
    Validates: Requirements 31.1, 31.2, 31.3, 31.4, 31.5, 31.6, 32.1, 32.2, 32.3, 32.4
    """
    
    def __init__(self, db: AsyncSession) -> None:
        """Initialize notification service.
        
        Args:
            db: Async database session
        """
        self.db = db
        self.notification_repo = NotificationRepository(db)
        self.preferences_repo = NotificationPreferencesRepository(db)
        
        # Initialize channel senders
        self._senders: dict[NotificationChannel, BaseChannelSender] = {
            NotificationChannel.PUSH: PushChannelSender(),
            NotificationChannel.EMAIL: EmailChannelSender(),
            NotificationChannel.SMS: SMSChannelSender(),
            NotificationChannel.WHATSAPP: WhatsAppChannelSender(),
        }
    
    def _get_sender(self, channel: NotificationChannel) -> BaseChannelSender:
        """Get the sender for a specific channel.
        
        Args:
            channel: The notification channel
            
        Returns:
            The channel sender
            
        Raises:
            ValueError: If channel is not supported
        """
        sender = self._senders.get(channel)
        if sender is None:
            raise ValueError(f"Unsupported channel: {channel}")
        return sender
    
    async def send_notification(
        self,
        user_id: UUID,
        title: str,
        body: str,
        channel: NotificationChannel,
    ) -> NotificationSendResult:
        """Send a notification via a specific channel.
        
        Validates: Requirements 31.1, 31.2
        
        Args:
            user_id: Target user's UUID
            title: Notification title
            body: Notification body content
            channel: Delivery channel
            
        Returns:
            NotificationSendResult with success status and details
        """
        # Create notification record
        notification = await self.notification_repo.create_notification(
            user_id=user_id,
            title=title,
            body=body,
            channel=channel,
            status=NotificationStatus.PENDING,
        )
        
        try:
            # Get sender and send
            sender = self._get_sender(channel)
            success = await sender.send(user_id, title, body)
            
            if success:
                # Update status to sent
                now = datetime.now(timezone.utc)
                await self.notification_repo.update_notification_status(
                    notification_id=notification.id,
                    status=NotificationStatus.SENT,
                    sent_at=now,
                )
                
                return NotificationSendResult(
                    success=True,
                    notification_id=notification.id,
                    channel_used=channel,
                    channels_attempted=[channel],
                )
            else:
                # Update status to failed
                now = datetime.now(timezone.utc)
                await self.notification_repo.update_notification_status(
                    notification_id=notification.id,
                    status=NotificationStatus.FAILED,
                    failed_at=now,
                    failure_reason="Send returned False",
                )
                
                return NotificationSendResult(
                    success=False,
                    notification_id=notification.id,
                    channels_attempted=[channel],
                    error="Failed to send notification",
                )
                
        except ChannelSendError as e:
            # Update status to failed
            now = datetime.now(timezone.utc)
            await self.notification_repo.update_notification_status(
                notification_id=notification.id,
                status=NotificationStatus.FAILED,
                failed_at=now,
                failure_reason=str(e),
            )
            
            return NotificationSendResult(
                success=False,
                notification_id=notification.id,
                channels_attempted=[channel],
                error=str(e),
            )
        except Exception as e:
            logger.exception(f"Unexpected error sending notification: {e}")
            
            # Update status to failed
            now = datetime.now(timezone.utc)
            await self.notification_repo.update_notification_status(
                notification_id=notification.id,
                status=NotificationStatus.FAILED,
                failed_at=now,
                failure_reason=f"Unexpected error: {str(e)}",
            )
            
            return NotificationSendResult(
                success=False,
                notification_id=notification.id,
                channels_attempted=[channel],
                error=f"Unexpected error: {str(e)}",
            )
    
    async def send_with_fallback(
        self,
        user_id: UUID,
        title: str,
        body: str,
        channels: list[NotificationChannel],
    ) -> NotificationSendResult:
        """Send a notification with channel fallback on failure.
        
        Validates: Requirements 31.1, 31.5
        
        Tries each channel in order. If a channel fails, falls back to the next
        channel in the list until one succeeds or all channels are exhausted.
        
        Args:
            user_id: Target user's UUID
            title: Notification title
            body: Notification body content
            channels: Ordered list of channels to try
            
        Returns:
            NotificationSendResult with success status and details
        """
        if not channels:
            return NotificationSendResult(
                success=False,
                channels_attempted=[],
                error="No channels provided",
            )
        
        channels_attempted: list[NotificationChannel] = []
        last_error: Optional[str] = None
        
        for channel in channels:
            channels_attempted.append(channel)
            
            # Create notification record for this attempt
            notification = await self.notification_repo.create_notification(
                user_id=user_id,
                title=title,
                body=body,
                channel=channel,
                status=NotificationStatus.PENDING,
            )
            
            try:
                sender = self._get_sender(channel)
                success = await sender.send(user_id, title, body)
                
                if success:
                    # Update status to sent
                    now = datetime.now(timezone.utc)
                    await self.notification_repo.update_notification_status(
                        notification_id=notification.id,
                        status=NotificationStatus.SENT,
                        sent_at=now,
                    )
                    
                    logger.info(
                        f"Notification sent successfully via {channel.value} "
                        f"after trying {len(channels_attempted)} channel(s)"
                    )
                    
                    return NotificationSendResult(
                        success=True,
                        notification_id=notification.id,
                        channel_used=channel,
                        channels_attempted=channels_attempted,
                    )
                else:
                    last_error = f"Channel {channel.value} returned False"
                    
            except ChannelSendError as e:
                last_error = str(e)
                logger.warning(f"Channel {channel.value} failed: {e}")
                
            except Exception as e:
                last_error = f"Unexpected error on {channel.value}: {str(e)}"
                logger.exception(f"Unexpected error on channel {channel.value}: {e}")
            
            # Update notification status to failed for this attempt
            now = datetime.now(timezone.utc)
            await self.notification_repo.update_notification_status(
                notification_id=notification.id,
                status=NotificationStatus.FAILED,
                failed_at=now,
                failure_reason=last_error,
            )
        
        # All channels failed
        logger.error(
            f"All {len(channels_attempted)} channels failed for user {user_id}"
        )
        
        return NotificationSendResult(
            success=False,
            channels_attempted=channels_attempted,
            error=f"All channels failed. Last error: {last_error}",
        )
    
    async def get_preferences(self, user_id: UUID) -> NotificationPreferences:
        """Get notification preferences for a user.
        
        Validates: Requirements 31.2
        
        Args:
            user_id: User's UUID
            
        Returns:
            NotificationPreferences model instance
        """
        return await self.preferences_repo.get_or_create_preferences(user_id)
    
    async def update_preferences(
        self,
        user_id: UUID,
        **kwargs,
    ) -> NotificationPreferences:
        """Update notification preferences for a user.
        
        Validates: Requirements 31.2
        
        Args:
            user_id: User's UUID
            **kwargs: Fields to update
            
        Returns:
            Updated NotificationPreferences model instance
        """
        # Ensure preferences exist
        await self.preferences_repo.get_or_create_preferences(user_id)
        
        # Update preferences
        preferences = await self.preferences_repo.update_preferences(user_id, **kwargs)
        if preferences is None:
            # This shouldn't happen since we just created them
            return await self.preferences_repo.get_or_create_preferences(user_id)
        return preferences
    
    async def get_notification_history(
        self,
        user_id: UUID,
        limit: int = 50,
        offset: int = 0,
    ) -> list[Notification]:
        """Get notification history for a user.
        
        Validates: Requirements 32.5
        
        Args:
            user_id: User's UUID
            limit: Maximum number of notifications to return
            offset: Number of notifications to skip
            
        Returns:
            List of Notification model instances
        """
        return await self.notification_repo.get_notifications_by_user(
            user_id, limit, offset
        )

    async def get_notification_history_paginated(
        self,
        user_id: UUID,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[Notification], int]:
        """Get paginated notification history for a user.
        
        Validates: Requirements 32.5, 37.5
        
        Args:
            user_id: User's UUID
            page: Page number (1-indexed)
            page_size: Number of notifications per page
            
        Returns:
            Tuple of (list of Notification model instances, total count)
        """
        offset = (page - 1) * page_size
        notifications = await self.notification_repo.get_notifications_by_user(
            user_id, page_size, offset
        )
        total = await self.notification_repo.count_notifications_by_user(user_id)
        return notifications, total

    async def is_in_quiet_hours(
        self,
        user_id: UUID,
        current_time: Optional[time] = None,
    ) -> bool:
        """Check if current time is within user's quiet hours.
        
        Validates: Requirements 31.4, 32.3
        
        Quiet hours can span midnight (e.g., 22:00 to 07:00).
        
        Args:
            user_id: User's UUID
            current_time: Time to check (defaults to current UTC time)
            
        Returns:
            True if within quiet hours, False otherwise
        """
        preferences = await self.preferences_repo.get_preferences_by_user(user_id)
        
        if preferences is None:
            return False
        
        if preferences.quiet_hours_start is None or preferences.quiet_hours_end is None:
            return False
        
        if current_time is None:
            current_time = datetime.now(timezone.utc).time()
        
        start = preferences.quiet_hours_start
        end = preferences.quiet_hours_end
        
        # Handle quiet hours that span midnight (e.g., 22:00 to 07:00)
        if start <= end:
            # Normal case: quiet hours within same day (e.g., 13:00 to 15:00)
            return start <= current_time <= end
        else:
            # Spans midnight: quiet hours cross day boundary (e.g., 22:00 to 07:00)
            return current_time >= start or current_time <= end

    async def send_notification_with_quiet_hours(
        self,
        user_id: UUID,
        title: str,
        body: str,
        channel: NotificationChannel,
        is_urgent: bool = False,
    ) -> NotificationSendResult:
        """Send a notification respecting quiet hours.
        
        Validates: Requirements 31.4, 32.3
        
        Non-urgent notifications are queued during quiet hours.
        Urgent notifications are sent immediately regardless of quiet hours.
        
        Args:
            user_id: Target user's UUID
            title: Notification title
            body: Notification body content
            channel: Delivery channel
            is_urgent: If True, send immediately regardless of quiet hours
            
        Returns:
            NotificationSendResult with success status and details
        """
        # Check quiet hours for non-urgent notifications
        if not is_urgent and await self.is_in_quiet_hours(user_id):
            # Queue the notification for later delivery
            notification = await self.notification_repo.create_notification(
                user_id=user_id,
                title=title,
                body=body,
                channel=channel,
                status=NotificationStatus.QUEUED,
            )
            
            logger.info(
                f"Notification queued for user {user_id} during quiet hours"
            )
            
            return NotificationSendResult(
                success=True,
                notification_id=notification.id,
                channel_used=None,
                channels_attempted=[],
                error=None,
            )
        
        # Send immediately
        return await self.send_notification(user_id, title, body, channel)

    async def send_with_fallback_and_quiet_hours(
        self,
        user_id: UUID,
        title: str,
        body: str,
        channels: list[NotificationChannel],
        is_urgent: bool = False,
    ) -> NotificationSendResult:
        """Send a notification with fallback, respecting quiet hours.
        
        Validates: Requirements 31.4, 31.5, 32.3
        
        Non-urgent notifications are queued during quiet hours.
        Urgent notifications are sent immediately with fallback.
        
        Args:
            user_id: Target user's UUID
            title: Notification title
            body: Notification body content
            channels: Ordered list of channels to try
            is_urgent: If True, send immediately regardless of quiet hours
            
        Returns:
            NotificationSendResult with success status and details
        """
        if not channels:
            return NotificationSendResult(
                success=False,
                channels_attempted=[],
                error="No channels provided",
            )
        
        # Check quiet hours for non-urgent notifications
        if not is_urgent and await self.is_in_quiet_hours(user_id):
            # Queue the notification for later delivery (use first channel)
            notification = await self.notification_repo.create_notification(
                user_id=user_id,
                title=title,
                body=body,
                channel=channels[0],
                status=NotificationStatus.QUEUED,
            )
            
            logger.info(
                f"Notification queued for user {user_id} during quiet hours"
            )
            
            return NotificationSendResult(
                success=True,
                notification_id=notification.id,
                channel_used=None,
                channels_attempted=[],
                error=None,
            )
        
        # Send with fallback
        return await self.send_with_fallback(user_id, title, body, channels)

    async def batch_notifications(
        self,
        user_id: UUID,
        notifications: list[tuple[str, str, NotificationChannel]],
    ) -> NotificationSendResult:
        """Batch multiple notifications into a single notification.
        
        Validates: Requirements 31.6
        
        Combines multiple notifications into a single batched notification
        to prevent notification fatigue.
        
        Args:
            user_id: Target user's UUID
            notifications: List of (title, body, channel) tuples to batch
            
        Returns:
            NotificationSendResult with success status and details
        """
        if not notifications:
            return NotificationSendResult(
                success=False,
                channels_attempted=[],
                error="No notifications to batch",
            )
        
        if len(notifications) == 1:
            # Single notification, no batching needed
            title, body, channel = notifications[0]
            return await self.send_notification(user_id, title, body, channel)
        
        # Batch multiple notifications
        # Use the channel from the first notification
        _, _, primary_channel = notifications[0]
        
        # Create batched title and body
        batched_title = f"You have {len(notifications)} new notifications"
        batched_body_parts = []
        for title, body, _ in notifications:
            batched_body_parts.append(f"• {title}: {body}")
        batched_body = "\n".join(batched_body_parts)
        
        logger.info(
            f"Batching {len(notifications)} notifications for user {user_id}"
        )
        
        return await self.send_notification(
            user_id, batched_title, batched_body, primary_channel
        )

    async def get_queued_notifications(
        self,
        user_id: UUID,
    ) -> list[Notification]:
        """Get queued notifications for a user (notifications held during quiet hours).
        
        Validates: Requirements 31.4
        
        Args:
            user_id: User's UUID
            
        Returns:
            List of queued Notification model instances
        """
        return await self.notification_repo.get_queued_notifications(user_id)

    async def process_queued_notifications(
        self,
        user_id: UUID,
    ) -> list[NotificationSendResult]:
        """Process and send queued notifications after quiet hours end.
        
        Validates: Requirements 31.4
        
        Args:
            user_id: User's UUID
            
        Returns:
            List of NotificationSendResult for each processed notification
        """
        # Check if still in quiet hours
        if await self.is_in_quiet_hours(user_id):
            logger.info(
                f"Still in quiet hours for user {user_id}, not processing queue"
            )
            return []
        
        queued = await self.get_queued_notifications(user_id)
        results = []
        
        for notification in queued:
            # Send the queued notification
            try:
                sender = self._get_sender(notification.channel)
                success = await sender.send(
                    user_id, notification.title, notification.body
                )
                
                now = datetime.now(timezone.utc)
                if success:
                    await self.notification_repo.update_notification_status(
                        notification_id=notification.id,
                        status=NotificationStatus.SENT,
                        sent_at=now,
                    )
                    results.append(NotificationSendResult(
                        success=True,
                        notification_id=notification.id,
                        channel_used=notification.channel,
                        channels_attempted=[notification.channel],
                    ))
                else:
                    await self.notification_repo.update_notification_status(
                        notification_id=notification.id,
                        status=NotificationStatus.FAILED,
                        failed_at=now,
                        failure_reason="Send returned False",
                    )
                    results.append(NotificationSendResult(
                        success=False,
                        notification_id=notification.id,
                        channels_attempted=[notification.channel],
                        error="Failed to send notification",
                    ))
            except Exception as e:
                logger.exception(f"Error processing queued notification: {e}")
                now = datetime.now(timezone.utc)
                await self.notification_repo.update_notification_status(
                    notification_id=notification.id,
                    status=NotificationStatus.FAILED,
                    failed_at=now,
                    failure_reason=str(e),
                )
                results.append(NotificationSendResult(
                    success=False,
                    notification_id=notification.id,
                    channels_attempted=[notification.channel],
                    error=str(e),
                ))
        
        logger.info(
            f"Processed {len(results)} queued notifications for user {user_id}"
        )
        return results

    async def schedule_notification(
        self,
        user_id: UUID,
        title: str,
        body: str,
        channel: NotificationChannel,
        send_at: datetime,
    ) -> Notification:
        """Schedule a notification for future delivery.
        
        Validates: Requirements 32.5
        
        Args:
            user_id: Target user's UUID
            title: Notification title
            body: Notification body content
            channel: Delivery channel
            send_at: When to send the notification (must be timezone-aware)
            
        Returns:
            Created Notification model instance with scheduled_at set
        """
        # Ensure send_at is timezone-aware
        if send_at.tzinfo is None:
            send_at = send_at.replace(tzinfo=timezone.utc)
        
        notification = await self.notification_repo.create_scheduled_notification(
            user_id=user_id,
            title=title,
            body=body,
            channel=channel,
            scheduled_at=send_at,
        )
        
        logger.info(
            f"Scheduled notification {notification.id} for user {user_id} at {send_at}"
        )
        
        return notification

    async def get_scheduled_notifications(
        self,
        user_id: UUID,
    ) -> list[Notification]:
        """Get pending scheduled notifications for a user.
        
        Validates: Requirements 32.5
        
        Args:
            user_id: User's UUID
            
        Returns:
            List of scheduled Notification model instances
        """
        return await self.notification_repo.get_scheduled_notifications(user_id)


# Convenience functions for direct channel sending

async def send_push(
    db: AsyncSession,
    user_id: UUID,
    title: str,
    body: str,
) -> NotificationSendResult:
    """Send a push notification.
    
    Validates: Requirements 31.1
    
    Args:
        db: Database session
        user_id: Target user's UUID
        title: Notification title
        body: Notification body content
        
    Returns:
        NotificationSendResult with success status
    """
    service = NotificationService(db)
    return await service.send_notification(user_id, title, body, NotificationChannel.PUSH)


async def send_email(
    db: AsyncSession,
    user_id: UUID,
    title: str,
    body: str,
) -> NotificationSendResult:
    """Send an email notification.
    
    Validates: Requirements 31.1
    
    Args:
        db: Database session
        user_id: Target user's UUID
        title: Notification title (used as subject)
        body: Notification body content
        
    Returns:
        NotificationSendResult with success status
    """
    service = NotificationService(db)
    return await service.send_notification(user_id, title, body, NotificationChannel.EMAIL)


async def send_sms(
    db: AsyncSession,
    user_id: UUID,
    title: str,
    body: str,
) -> NotificationSendResult:
    """Send an SMS notification.
    
    Validates: Requirements 31.1
    
    Args:
        db: Database session
        user_id: Target user's UUID
        title: Notification title
        body: Notification body content
        
    Returns:
        NotificationSendResult with success status
    """
    service = NotificationService(db)
    return await service.send_notification(user_id, title, body, NotificationChannel.SMS)


async def send_whatsapp(
    db: AsyncSession,
    user_id: UUID,
    title: str,
    body: str,
) -> NotificationSendResult:
    """Send a WhatsApp notification.
    
    Validates: Requirements 31.1
    
    Args:
        db: Database session
        user_id: Target user's UUID
        title: Notification title
        body: Notification body content
        
    Returns:
        NotificationSendResult with success status
    """
    service = NotificationService(db)
    return await service.send_notification(user_id, title, body, NotificationChannel.WHATSAPP)
