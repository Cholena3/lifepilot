"""Account management schemas for data export and deletion.

Validates: Requirements 36.5, 36.6
"""

from datetime import datetime
from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel, Field


class DataExportResponse(BaseModel):
    """Response schema for data export endpoint.
    
    Validates: Requirements 36.5
    
    Contains all user data in a portable JSON format.
    """
    
    export_date: datetime = Field(description="Timestamp when export was generated")
    user: dict[str, Any] = Field(description="User account information")
    profile: Optional[dict[str, Any]] = Field(default=None, description="User profile data")
    student_profile: Optional[dict[str, Any]] = Field(default=None, description="Student profile data")
    career_preferences: Optional[dict[str, Any]] = Field(default=None, description="Career preferences")
    documents: list[dict[str, Any]] = Field(default_factory=list, description="User documents metadata")
    expenses: list[dict[str, Any]] = Field(default_factory=list, description="User expenses")
    expense_categories: list[dict[str, Any]] = Field(default_factory=list, description="Custom expense categories")
    budgets: list[dict[str, Any]] = Field(default_factory=list, description="User budgets")
    health_records: list[dict[str, Any]] = Field(default_factory=list, description="Health records")
    family_members: list[dict[str, Any]] = Field(default_factory=list, description="Family members")
    medicines: list[dict[str, Any]] = Field(default_factory=list, description="Medicine tracking data")
    vitals: list[dict[str, Any]] = Field(default_factory=list, description="Vital signs records")
    emergency_info: Optional[dict[str, Any]] = Field(default=None, description="Emergency health information")
    wardrobe_items: list[dict[str, Any]] = Field(default_factory=list, description="Wardrobe items")
    outfits: list[dict[str, Any]] = Field(default_factory=list, description="Saved outfits")
    outfit_plans: list[dict[str, Any]] = Field(default_factory=list, description="Outfit plans")
    packing_lists: list[dict[str, Any]] = Field(default_factory=list, description="Packing lists")
    skills: list[dict[str, Any]] = Field(default_factory=list, description="Skills inventory")
    courses: list[dict[str, Any]] = Field(default_factory=list, description="Learning courses")
    roadmaps: list[dict[str, Any]] = Field(default_factory=list, description="Career roadmaps")
    job_applications: list[dict[str, Any]] = Field(default_factory=list, description="Job applications")
    achievements: list[dict[str, Any]] = Field(default_factory=list, description="Achievements")
    resumes: list[dict[str, Any]] = Field(default_factory=list, description="Resumes")
    exam_bookmarks: list[dict[str, Any]] = Field(default_factory=list, description="Exam bookmarks")
    exam_applications: list[dict[str, Any]] = Field(default_factory=list, description="Exam applications")
    notifications: list[dict[str, Any]] = Field(default_factory=list, description="Notification history")
    notification_preferences: Optional[dict[str, Any]] = Field(default=None, description="Notification preferences")
    life_scores: list[dict[str, Any]] = Field(default_factory=list, description="Life score history")
    badges: list[dict[str, Any]] = Field(default_factory=list, description="Earned badges")
    weekly_summaries: list[dict[str, Any]] = Field(default_factory=list, description="Weekly summaries")
    
    model_config = {"from_attributes": True}


class AccountDeletionRequest(BaseModel):
    """Request schema for account deletion.
    
    Validates: Requirements 36.6
    """
    
    confirm: bool = Field(
        description="Must be True to confirm account deletion request"
    )
    password: Optional[str] = Field(
        default=None,
        description="Current password for verification (required for password-based accounts)"
    )


class AccountDeletionResponse(BaseModel):
    """Response schema for account deletion request.
    
    Validates: Requirements 36.6
    """
    
    message: str = Field(description="Status message")
    deletion_requested_at: datetime = Field(description="When deletion was requested")
    deletion_scheduled_at: datetime = Field(description="When data will be permanently deleted")
    can_cancel_until: datetime = Field(description="Deadline to cancel deletion")


class AccountDeletionCancelResponse(BaseModel):
    """Response schema for cancelling account deletion.
    
    Validates: Requirements 36.6
    """
    
    message: str = Field(description="Status message")
    cancelled_at: datetime = Field(description="When cancellation was processed")


class AccountDeletionStatusResponse(BaseModel):
    """Response schema for account deletion status.
    
    Validates: Requirements 36.6
    """
    
    deletion_pending: bool = Field(description="Whether deletion is pending")
    deletion_requested_at: Optional[datetime] = Field(
        default=None, description="When deletion was requested"
    )
    deletion_scheduled_at: Optional[datetime] = Field(
        default=None, description="When data will be permanently deleted"
    )
    can_cancel: bool = Field(description="Whether deletion can still be cancelled")
