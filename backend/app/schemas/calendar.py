"""Schemas for Google Calendar integration.

Implements Requirements 4.1-4.5 for exam calendar integration.
"""

import uuid
from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel, Field


class GoogleCalendarAuthURL(BaseModel):
    """Response containing Google Calendar OAuth authorization URL."""
    
    auth_url: str = Field(..., description="Google OAuth authorization URL")
    state: str = Field(..., description="State parameter for CSRF protection")


class GoogleCalendarCallback(BaseModel):
    """Request body for Google Calendar OAuth callback."""
    
    code: str = Field(..., description="Authorization code from Google")
    state: str = Field(..., description="State parameter for CSRF verification")


class GoogleCalendarTokenResponse(BaseModel):
    """Response after successful Google Calendar OAuth."""
    
    connected: bool = Field(True, description="Whether calendar is connected")
    message: str = Field(..., description="Success message")


class GoogleCalendarStatus(BaseModel):
    """Response for Google Calendar connection status."""
    
    connected: bool = Field(..., description="Whether calendar is connected")
    token_expiry: Optional[datetime] = Field(None, description="When the token expires")


class CalendarEventCreate(BaseModel):
    """Request to create a calendar event for an exam."""
    
    exam_id: uuid.UUID = Field(..., description="ID of the exam to sync")


class CalendarEventResponse(BaseModel):
    """Response after creating/updating a calendar event."""
    
    id: uuid.UUID = Field(..., description="Calendar sync record ID")
    exam_id: uuid.UUID = Field(..., description="Exam ID")
    google_event_id: str = Field(..., description="Google Calendar event ID")
    synced_at: datetime = Field(..., description="When the event was synced")
    
    model_config = {"from_attributes": True}


class CalendarSyncResponse(BaseModel):
    """Response for calendar sync status of an exam."""
    
    exam_id: uuid.UUID = Field(..., description="Exam ID")
    is_synced: bool = Field(..., description="Whether exam is synced to calendar")
    google_event_id: Optional[str] = Field(None, description="Google Calendar event ID if synced")
    synced_at: Optional[datetime] = Field(None, description="When the event was last synced")


class CalendarEventDetails(BaseModel):
    """Details for creating a Google Calendar event."""
    
    summary: str = Field(..., description="Event title")
    description: Optional[str] = Field(None, description="Event description")
    start_date: date = Field(..., description="Event start date")
    end_date: Optional[date] = Field(None, description="Event end date")
    location: Optional[str] = Field(None, description="Event location")
