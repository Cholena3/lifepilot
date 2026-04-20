"""Pydantic schemas for notification service.

Validates: Requirements 31.1, 31.2, 31.5
"""

from datetime import datetime, time
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field

from app.models.notification import NotificationChannel, NotificationStatus


# Notification Schemas

class NotificationCreate(BaseModel):
    """Schema for creating a notification.
    
    Validates: Requirements 31.1, 31.2
    """
    title: str = Field(..., min_length=1, max_length=255, description="Notification title")
    body: str = Field(..., min_length=1, description="Notification body content")
    channel: NotificationChannel = Field(..., description="Delivery channel")


class NotificationResponse(BaseModel):
    """Schema for notification response.
    
    Validates: Requirements 31.1, 32.5
    """
    id: UUID
    user_id: UUID
    title: str
    body: str
    channel: NotificationChannel
    status: NotificationStatus
    sent_at: Optional[datetime] = None
    delivered_at: Optional[datetime] = None
    failed_at: Optional[datetime] = None
    failure_reason: Optional[str] = None
    scheduled_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class NotificationSendRequest(BaseModel):
    """Schema for sending a notification to a user.
    
    Validates: Requirements 31.1, 31.2
    """
    user_id: UUID = Field(..., description="Target user ID")
    title: str = Field(..., min_length=1, max_length=255, description="Notification title")
    body: str = Field(..., min_length=1, description="Notification body content")
    channel: NotificationChannel = Field(..., description="Delivery channel")


class NotificationSendWithFallbackRequest(BaseModel):
    """Schema for sending a notification with channel fallback.
    
    Validates: Requirements 31.1, 31.5
    """
    user_id: UUID = Field(..., description="Target user ID")
    title: str = Field(..., min_length=1, max_length=255, description="Notification title")
    body: str = Field(..., min_length=1, description="Notification body content")
    channels: list[NotificationChannel] = Field(
        ..., 
        min_length=1,
        description="Ordered list of channels to try (first is primary, rest are fallbacks)"
    )


class NotificationSendResult(BaseModel):
    """Result of a notification send operation.
    
    Validates: Requirements 31.1, 31.5
    """
    success: bool
    notification_id: Optional[UUID] = None
    channel_used: Optional[NotificationChannel] = None
    channels_attempted: list[NotificationChannel] = Field(default_factory=list)
    error: Optional[str] = None


# Notification Preferences Schemas

class NotificationPreferencesCreate(BaseModel):
    """Schema for creating notification preferences.
    
    Validates: Requirements 31.2, 31.3, 31.4
    """
    push_enabled: bool = Field(default=True, description="Enable push notifications")
    email_enabled: bool = Field(default=True, description="Enable email notifications")
    sms_enabled: bool = Field(default=False, description="Enable SMS notifications")
    whatsapp_enabled: bool = Field(default=False, description="Enable WhatsApp notifications")
    quiet_hours_start: Optional[time] = Field(
        default=None, 
        description="Start time for quiet hours (HH:MM)"
    )
    quiet_hours_end: Optional[time] = Field(
        default=None, 
        description="End time for quiet hours (HH:MM)"
    )


class NotificationPreferencesUpdate(BaseModel):
    """Schema for updating notification preferences.
    
    Validates: Requirements 31.2, 31.3, 31.4
    """
    push_enabled: Optional[bool] = Field(default=None, description="Enable push notifications")
    email_enabled: Optional[bool] = Field(default=None, description="Enable email notifications")
    sms_enabled: Optional[bool] = Field(default=None, description="Enable SMS notifications")
    whatsapp_enabled: Optional[bool] = Field(default=None, description="Enable WhatsApp notifications")
    quiet_hours_start: Optional[time] = Field(
        default=None, 
        description="Start time for quiet hours (HH:MM)"
    )
    quiet_hours_end: Optional[time] = Field(
        default=None, 
        description="End time for quiet hours (HH:MM)"
    )


class NotificationPreferencesResponse(BaseModel):
    """Schema for notification preferences response.
    
    Validates: Requirements 31.2, 31.3, 31.4
    """
    id: UUID
    user_id: UUID
    push_enabled: bool
    email_enabled: bool
    sms_enabled: bool
    whatsapp_enabled: bool
    quiet_hours_start: Optional[time] = None
    quiet_hours_end: Optional[time] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
