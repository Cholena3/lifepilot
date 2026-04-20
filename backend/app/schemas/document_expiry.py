"""Pydantic schemas for document expiry alerts.

Validates: Requirements 8.1, 8.2, 8.3, 8.4
"""

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field

from app.models.document_expiry import ExpiryAlertType
from app.schemas.document import DocumentCategory


class DocumentExpiryAlertPreferencesCreate(BaseModel):
    """Schema for creating document expiry alert preferences.
    
    Validates: Requirements 8.4
    """
    category: str = Field(..., description="Document category")
    alerts_enabled: bool = Field(default=True, description="Enable expiry alerts for this category")
    alert_30_days: bool = Field(default=True, description="Send alert 30 days before expiry")
    alert_14_days: bool = Field(default=True, description="Send alert 14 days before expiry")
    alert_7_days: bool = Field(default=True, description="Send alert 7 days before expiry")


class DocumentExpiryAlertPreferencesUpdate(BaseModel):
    """Schema for updating document expiry alert preferences.
    
    Validates: Requirements 8.4
    """
    alerts_enabled: Optional[bool] = Field(default=None, description="Enable expiry alerts for this category")
    alert_30_days: Optional[bool] = Field(default=None, description="Send alert 30 days before expiry")
    alert_14_days: Optional[bool] = Field(default=None, description="Send alert 14 days before expiry")
    alert_7_days: Optional[bool] = Field(default=None, description="Send alert 7 days before expiry")


class DocumentExpiryAlertPreferencesResponse(BaseModel):
    """Response schema for document expiry alert preferences.
    
    Validates: Requirements 8.4
    """
    id: UUID
    user_id: UUID
    category: str
    alerts_enabled: bool
    alert_30_days: bool
    alert_14_days: bool
    alert_7_days: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class DocumentExpiryAlertResponse(BaseModel):
    """Response schema for document expiry alert record.
    
    Validates: Requirements 8.1
    """
    id: UUID
    document_id: UUID
    user_id: UUID
    alert_type: ExpiryAlertType
    sent_at: datetime
    notification_id: Optional[UUID] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ExpiringDocumentInfo(BaseModel):
    """Information about an expiring document.
    
    Validates: Requirements 8.1, 8.2
    """
    document_id: UUID
    user_id: UUID
    title: str
    category: str
    expiry_date: datetime
    days_until_expiry: int
    is_expired: bool


class DocumentExpiryCheckResult(BaseModel):
    """Result of checking documents for expiry.
    
    Validates: Requirements 8.1, 8.2
    """
    documents_checked: int
    alerts_sent: int
    documents_marked_expired: int
    errors: list[str] = Field(default_factory=list)
