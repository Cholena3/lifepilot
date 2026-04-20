"""Notification repository for database operations.

Validates: Requirements 31.1, 31.2, 31.4, 32.5
"""

from datetime import datetime
from typing import Optional
from uuid import UUID

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.notification import (
    Notification,
    NotificationChannel,
    NotificationPreferences,
    NotificationStatus,
)


class NotificationRepository:
    """Repository for Notification database operations.
    
    Validates: Requirements 31.1
    """

    def __init__(self, db: AsyncSession) -> None:
        """Initialize repository with database session.
        
        Args:
            db: Async database session
        """
        self.db = db

    async def create_notification(
        self,
        user_id: UUID,
        title: str,
        body: str,
        channel: NotificationChannel,
        status: NotificationStatus = NotificationStatus.PENDING,
    ) -> Notification:
        """Create a new notification record.
        
        Validates: Requirements 31.1
        
        Args:
            user_id: Target user's UUID
            title: Notification title
            body: Notification body content
            channel: Delivery channel
            status: Initial status (default: PENDING)
            
        Returns:
            Created Notification model instance
        """
        notification = Notification(
            user_id=user_id,
            title=title,
            body=body,
            channel=channel,
            status=status,
        )
        self.db.add(notification)
        await self.db.flush()
        await self.db.refresh(notification)
        return notification

    async def get_notification_by_id(
        self, notification_id: UUID
    ) -> Optional[Notification]:
        """Get a notification by ID.
        
        Args:
            notification_id: Notification UUID
            
        Returns:
            Notification if found, None otherwise
        """
        stmt = select(Notification).where(Notification.id == notification_id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_notifications_by_user(
        self,
        user_id: UUID,
        limit: int = 50,
        offset: int = 0,
    ) -> list[Notification]:
        """Get notifications for a user.
        
        Args:
            user_id: User's UUID
            limit: Maximum number of notifications to return
            offset: Number of notifications to skip
            
        Returns:
            List of Notification model instances
        """
        stmt = (
            select(Notification)
            .where(Notification.user_id == user_id)
            .order_by(Notification.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def count_notifications_by_user(
        self,
        user_id: UUID,
    ) -> int:
        """Count total notifications for a user.
        
        Validates: Requirements 37.5
        
        Args:
            user_id: User's UUID
            
        Returns:
            Total count of notifications
        """
        stmt = (
            select(func.count())
            .select_from(Notification)
            .where(Notification.user_id == user_id)
        )
        result = await self.db.execute(stmt)
        return result.scalar_one()

    async def update_notification_status(
        self,
        notification_id: UUID,
        status: NotificationStatus,
        sent_at: Optional[datetime] = None,
        delivered_at: Optional[datetime] = None,
        failed_at: Optional[datetime] = None,
        failure_reason: Optional[str] = None,
    ) -> Optional[Notification]:
        """Update notification status and timestamps.
        
        Validates: Requirements 31.1, 31.5
        
        Args:
            notification_id: Notification UUID
            status: New status
            sent_at: When notification was sent
            delivered_at: When notification was delivered
            failed_at: When notification failed
            failure_reason: Reason for failure
            
        Returns:
            Updated Notification if found, None otherwise
        """
        update_data = {"status": status}
        if sent_at is not None:
            update_data["sent_at"] = sent_at
        if delivered_at is not None:
            update_data["delivered_at"] = delivered_at
        if failed_at is not None:
            update_data["failed_at"] = failed_at
        if failure_reason is not None:
            update_data["failure_reason"] = failure_reason

        stmt = (
            update(Notification)
            .where(Notification.id == notification_id)
            .values(**update_data)
            .returning(Notification)
        )
        result = await self.db.execute(stmt)
        await self.db.flush()
        return result.scalar_one_or_none()

    async def get_queued_notifications(
        self,
        user_id: UUID,
    ) -> list[Notification]:
        """Get queued notifications for a user.
        
        Validates: Requirements 31.4
        
        Args:
            user_id: User's UUID
            
        Returns:
            List of queued Notification model instances
        """
        stmt = (
            select(Notification)
            .where(
                Notification.user_id == user_id,
                Notification.status == NotificationStatus.QUEUED,
            )
            .order_by(Notification.created_at.asc())
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def create_scheduled_notification(
        self,
        user_id: UUID,
        title: str,
        body: str,
        channel: NotificationChannel,
        scheduled_at: datetime,
    ) -> Notification:
        """Create a scheduled notification record.
        
        Validates: Requirements 32.5
        
        Args:
            user_id: Target user's UUID
            title: Notification title
            body: Notification body content
            channel: Delivery channel
            scheduled_at: When to send the notification
            
        Returns:
            Created Notification model instance
        """
        notification = Notification(
            user_id=user_id,
            title=title,
            body=body,
            channel=channel,
            status=NotificationStatus.PENDING,
            scheduled_at=scheduled_at,
        )
        self.db.add(notification)
        await self.db.flush()
        await self.db.refresh(notification)
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
            List of scheduled Notification model instances (not yet sent)
        """
        from datetime import datetime, timezone
        
        now = datetime.now(timezone.utc)
        stmt = (
            select(Notification)
            .where(
                Notification.user_id == user_id,
                Notification.status == NotificationStatus.PENDING,
                Notification.scheduled_at.isnot(None),
                Notification.scheduled_at > now,
            )
            .order_by(Notification.scheduled_at.asc())
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())


class NotificationPreferencesRepository:
    """Repository for NotificationPreferences database operations.
    
    Validates: Requirements 31.2
    """

    def __init__(self, db: AsyncSession) -> None:
        """Initialize repository with database session.
        
        Args:
            db: Async database session
        """
        self.db = db

    async def create_preferences(
        self,
        user_id: UUID,
        push_enabled: bool = True,
        email_enabled: bool = True,
        sms_enabled: bool = False,
        whatsapp_enabled: bool = False,
        quiet_hours_start: Optional[datetime] = None,
        quiet_hours_end: Optional[datetime] = None,
    ) -> NotificationPreferences:
        """Create notification preferences for a user.
        
        Validates: Requirements 31.2
        
        Args:
            user_id: User's UUID
            push_enabled: Enable push notifications
            email_enabled: Enable email notifications
            sms_enabled: Enable SMS notifications
            whatsapp_enabled: Enable WhatsApp notifications
            quiet_hours_start: Start time for quiet hours
            quiet_hours_end: End time for quiet hours
            
        Returns:
            Created NotificationPreferences model instance
        """
        preferences = NotificationPreferences(
            user_id=user_id,
            push_enabled=push_enabled,
            email_enabled=email_enabled,
            sms_enabled=sms_enabled,
            whatsapp_enabled=whatsapp_enabled,
            quiet_hours_start=quiet_hours_start,
            quiet_hours_end=quiet_hours_end,
        )
        self.db.add(preferences)
        await self.db.flush()
        await self.db.refresh(preferences)
        return preferences

    async def get_preferences_by_user(
        self, user_id: UUID
    ) -> Optional[NotificationPreferences]:
        """Get notification preferences for a user.
        
        Args:
            user_id: User's UUID
            
        Returns:
            NotificationPreferences if found, None otherwise
        """
        stmt = select(NotificationPreferences).where(
            NotificationPreferences.user_id == user_id
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def update_preferences(
        self,
        user_id: UUID,
        **kwargs,
    ) -> Optional[NotificationPreferences]:
        """Update notification preferences for a user.
        
        Validates: Requirements 31.2
        
        Args:
            user_id: User's UUID
            **kwargs: Fields to update
            
        Returns:
            Updated NotificationPreferences if found, None otherwise
        """
        # Filter out None values
        update_data = {k: v for k, v in kwargs.items() if v is not None}
        
        if not update_data:
            return await self.get_preferences_by_user(user_id)

        stmt = (
            update(NotificationPreferences)
            .where(NotificationPreferences.user_id == user_id)
            .values(**update_data)
            .returning(NotificationPreferences)
        )
        result = await self.db.execute(stmt)
        await self.db.flush()
        return result.scalar_one_or_none()

    async def get_or_create_preferences(
        self, user_id: UUID
    ) -> NotificationPreferences:
        """Get or create notification preferences for a user.
        
        Args:
            user_id: User's UUID
            
        Returns:
            NotificationPreferences model instance
        """
        preferences = await self.get_preferences_by_user(user_id)
        if preferences is None:
            preferences = await self.create_preferences(user_id)
        return preferences
