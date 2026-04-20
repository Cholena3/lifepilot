"""Pydantic schemas for weekly summary module.

Provides schemas for weekly summary generation and retrieval.

Validates: Requirements 34.1, 34.2, 34.3, 34.4, 34.5
"""

from datetime import date, datetime
from decimal import Decimal
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, Field


class WeeklySummaryMetrics(BaseModel):
    """Metrics for a weekly summary.
    
    Validates: Requirements 34.2
    """
    
    # Money module
    expenses_total: Decimal = Field(
        default=Decimal("0"),
        description="Total expenses for the week"
    )
    expenses_count: int = Field(
        default=0,
        description="Number of expenses logged"
    )
    
    # Documents module
    documents_added: int = Field(
        default=0,
        description="Number of documents added"
    )
    
    # Health module
    health_records_logged: int = Field(
        default=0,
        description="Number of health records logged"
    )
    medicine_doses_taken: int = Field(
        default=0,
        description="Number of medicine doses taken"
    )
    vitals_logged: int = Field(
        default=0,
        description="Number of vitals logged"
    )
    
    # Wardrobe module
    wardrobe_items_added: int = Field(
        default=0,
        description="Number of wardrobe items added"
    )
    outfits_worn: int = Field(
        default=0,
        description="Number of outfits worn"
    )
    
    # Career module
    skills_updated: int = Field(
        default=0,
        description="Number of skills added or updated"
    )
    courses_progress_hours: Decimal = Field(
        default=Decimal("0"),
        description="Hours of course progress"
    )
    job_applications: int = Field(
        default=0,
        description="Number of job applications submitted"
    )
    achievements_added: int = Field(
        default=0,
        description="Number of achievements added"
    )
    
    # Exams module
    exams_bookmarked: int = Field(
        default=0,
        description="Number of exams bookmarked"
    )
    exams_applied: int = Field(
        default=0,
        description="Number of exams applied to"
    )
    
    # Overall
    life_score: int = Field(
        default=0,
        description="Life score at end of week"
    )
    total_activities: int = Field(
        default=0,
        description="Total number of activities across all modules"
    )


class WeeklySummaryComparisons(BaseModel):
    """Comparison metrics with previous week.
    
    Validates: Requirements 34.3
    """
    
    # Money module
    expenses_total_change: Decimal = Field(
        default=Decimal("0"),
        description="Change in total expenses from previous week"
    )
    expenses_total_change_percent: Optional[Decimal] = Field(
        default=None,
        description="Percentage change in expenses (None if previous was 0)"
    )
    expenses_count_change: int = Field(
        default=0,
        description="Change in number of expenses"
    )
    
    # Documents module
    documents_added_change: int = Field(
        default=0,
        description="Change in documents added"
    )
    
    # Health module
    health_records_logged_change: int = Field(
        default=0,
        description="Change in health records logged"
    )
    medicine_doses_taken_change: int = Field(
        default=0,
        description="Change in medicine doses taken"
    )
    vitals_logged_change: int = Field(
        default=0,
        description="Change in vitals logged"
    )
    
    # Wardrobe module
    wardrobe_items_added_change: int = Field(
        default=0,
        description="Change in wardrobe items added"
    )
    outfits_worn_change: int = Field(
        default=0,
        description="Change in outfits worn"
    )
    
    # Career module
    skills_updated_change: int = Field(
        default=0,
        description="Change in skills updated"
    )
    courses_progress_hours_change: Decimal = Field(
        default=Decimal("0"),
        description="Change in course progress hours"
    )
    job_applications_change: int = Field(
        default=0,
        description="Change in job applications"
    )
    achievements_added_change: int = Field(
        default=0,
        description="Change in achievements added"
    )
    
    # Exams module
    exams_bookmarked_change: int = Field(
        default=0,
        description="Change in exams bookmarked"
    )
    exams_applied_change: int = Field(
        default=0,
        description="Change in exams applied"
    )
    
    # Overall
    life_score_change: int = Field(
        default=0,
        description="Change in life score"
    )
    total_activities_change: int = Field(
        default=0,
        description="Change in total activities"
    )


class WeeklySummaryResponse(BaseModel):
    """Response schema for a weekly summary.
    
    Validates: Requirements 34.1, 34.2, 34.3, 34.5
    """
    
    model_config = {"from_attributes": True}
    
    id: UUID = Field(..., description="Summary UUID")
    user_id: UUID = Field(..., description="User UUID")
    week_start: date = Field(..., description="Start date of the week (Monday)")
    week_end: date = Field(..., description="End date of the week (Sunday)")
    metrics: WeeklySummaryMetrics = Field(..., description="Activity metrics for the week")
    comparisons: WeeklySummaryComparisons = Field(..., description="Comparison with previous week")
    generated_at: datetime = Field(..., description="When the summary was generated")
    created_at: datetime = Field(..., description="Record creation timestamp")
    updated_at: datetime = Field(..., description="Record update timestamp")


class WeeklySummaryListResponse(BaseModel):
    """Response schema for listing weekly summaries.
    
    Validates: Requirements 34.5
    """
    
    summaries: List[WeeklySummaryResponse] = Field(
        default_factory=list,
        description="List of weekly summaries"
    )
    total: int = Field(..., description="Total number of summaries")
    page: int = Field(..., description="Current page number")
    page_size: int = Field(..., description="Number of items per page")
    has_more: bool = Field(..., description="Whether there are more pages")


class WeeklySummaryGenerateRequest(BaseModel):
    """Request schema for generating a weekly summary.
    
    Validates: Requirements 34.1
    """
    
    week_start: Optional[date] = Field(
        default=None,
        description="Start date of the week to generate summary for (defaults to last completed week)"
    )


class WeeklySummaryNotificationContent(BaseModel):
    """Content for weekly summary notification.
    
    Validates: Requirements 34.4
    """
    
    title: str = Field(..., description="Notification title")
    body: str = Field(..., description="Notification body")
    summary_id: UUID = Field(..., description="ID of the generated summary")
