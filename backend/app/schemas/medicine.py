"""Pydantic schemas for medicine tracking module.

Includes schemas for medicine CRUD operations, dose tracking,
and adherence statistics.

Validates: Requirements 15.1, 15.2, 15.3, 15.4, 15.5, 15.6
"""

from datetime import datetime, date, time
from typing import Optional, List
from uuid import UUID

from pydantic import BaseModel, Field, field_validator


class MedicineFrequencyEnum:
    """Valid medicine frequency options.
    
    Validates: Requirements 15.1
    """
    ONCE_DAILY = "once_daily"
    TWICE_DAILY = "twice_daily"
    THREE_TIMES_DAILY = "three_times_daily"
    FOUR_TIMES_DAILY = "four_times_daily"
    EVERY_OTHER_DAY = "every_other_day"
    WEEKLY = "weekly"
    AS_NEEDED = "as_needed"
    CUSTOM = "custom"
    
    ALL = [
        ONCE_DAILY, TWICE_DAILY, THREE_TIMES_DAILY, FOUR_TIMES_DAILY,
        EVERY_OTHER_DAY, WEEKLY, AS_NEEDED, CUSTOM
    ]


class DoseStatusEnum:
    """Status of a scheduled dose.
    
    Validates: Requirements 15.3, 15.4
    """
    SCHEDULED = "scheduled"
    TAKEN = "taken"
    MISSED = "missed"
    SKIPPED = "skipped"
    
    ALL = [SCHEDULED, TAKEN, MISSED, SKIPPED]


# ============================================================================
# Medicine Schemas
# ============================================================================

class MedicineCreate(BaseModel):
    """Schema for creating a new medicine.
    
    Validates: Requirements 15.1
    """
    
    name: str = Field(..., min_length=1, max_length=255, description="Name of the medicine")
    dosage: Optional[str] = Field(None, max_length=100, description="Dosage amount and unit")
    frequency: str = Field(
        default=MedicineFrequencyEnum.ONCE_DAILY,
        description="How often the medicine should be taken"
    )
    instructions: Optional[str] = Field(None, description="Additional instructions")
    reminder_times: Optional[List[str]] = Field(
        None,
        description="List of reminder times in HH:MM format"
    )
    start_date: date = Field(default_factory=date.today, description="Start date of medicine course")
    end_date: Optional[date] = Field(None, description="End date of medicine course")
    total_quantity: Optional[int] = Field(None, ge=0, description="Total quantity for refill tracking")
    remaining_quantity: Optional[int] = Field(None, ge=0, description="Remaining quantity")
    refill_threshold: int = Field(default=5, ge=0, description="Quantity at which to send refill reminder")
    health_record_id: Optional[UUID] = Field(None, description="Source prescription health record ID")
    
    @field_validator("frequency")
    @classmethod
    def validate_frequency(cls, v: str) -> str:
        """Validate that frequency is one of the allowed values."""
        if v not in MedicineFrequencyEnum.ALL:
            raise ValueError(f"Frequency must be one of: {', '.join(MedicineFrequencyEnum.ALL)}")
        return v
    
    @field_validator("reminder_times")
    @classmethod
    def validate_reminder_times(cls, v: Optional[List[str]]) -> Optional[List[str]]:
        """Validate reminder times are in HH:MM format."""
        if v is None:
            return v
        import re
        time_pattern = re.compile(r'^([01]?[0-9]|2[0-3]):([0-5][0-9])$')
        for t in v:
            if not time_pattern.match(t):
                raise ValueError(f"Invalid time format: {t}. Use HH:MM format.")
        return v


class MedicineUpdate(BaseModel):
    """Schema for updating a medicine."""
    
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    dosage: Optional[str] = Field(None, max_length=100)
    frequency: Optional[str] = None
    instructions: Optional[str] = None
    reminder_times: Optional[List[str]] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    total_quantity: Optional[int] = Field(None, ge=0)
    remaining_quantity: Optional[int] = Field(None, ge=0)
    refill_threshold: Optional[int] = Field(None, ge=0)
    is_active: Optional[bool] = None
    
    @field_validator("frequency")
    @classmethod
    def validate_frequency(cls, v: Optional[str]) -> Optional[str]:
        """Validate that frequency is one of the allowed values."""
        if v is not None and v not in MedicineFrequencyEnum.ALL:
            raise ValueError(f"Frequency must be one of: {', '.join(MedicineFrequencyEnum.ALL)}")
        return v
    
    @field_validator("reminder_times")
    @classmethod
    def validate_reminder_times(cls, v: Optional[List[str]]) -> Optional[List[str]]:
        """Validate reminder times are in HH:MM format."""
        if v is None:
            return v
        import re
        time_pattern = re.compile(r'^([01]?[0-9]|2[0-3]):([0-5][0-9])$')
        for t in v:
            if not time_pattern.match(t):
                raise ValueError(f"Invalid time format: {t}. Use HH:MM format.")
        return v


class MedicineResponse(BaseModel):
    """Response schema for a medicine.
    
    Validates: Requirements 15.1, 15.6
    """
    
    id: UUID
    user_id: UUID
    health_record_id: Optional[UUID] = None
    name: str
    dosage: Optional[str] = None
    frequency: str
    instructions: Optional[str] = None
    reminder_times: Optional[List[str]] = None
    start_date: date
    end_date: Optional[date] = None
    total_quantity: Optional[int] = None
    remaining_quantity: Optional[int] = None
    refill_threshold: int
    is_active: bool
    created_at: datetime
    updated_at: datetime
    
    model_config = {"from_attributes": True}


# ============================================================================
# Dose Schemas
# ============================================================================

class DoseLogCreate(BaseModel):
    """Schema for logging a dose.
    
    Validates: Requirements 15.3, 15.4
    """
    
    taken: bool = Field(..., description="Whether the dose was taken")
    taken_time: Optional[datetime] = Field(None, description="When the dose was taken")
    notes: Optional[str] = Field(None, description="Optional notes about this dose")


class DoseResponse(BaseModel):
    """Response schema for a dose record.
    
    Validates: Requirements 15.3, 15.4
    """
    
    id: UUID
    medicine_id: UUID
    scheduled_time: datetime
    taken_time: Optional[datetime] = None
    status: str
    notes: Optional[str] = None
    reminder_sent: bool
    followup_reminder_sent: bool
    created_at: datetime
    updated_at: datetime
    
    model_config = {"from_attributes": True}


class DoseWithMedicineResponse(DoseResponse):
    """Response schema for a dose with medicine details."""
    
    medicine_name: str
    medicine_dosage: Optional[str] = None


# ============================================================================
# Adherence Statistics Schemas
# ============================================================================

class AdherenceStats(BaseModel):
    """Schema for medicine adherence statistics.
    
    Validates: Requirements 15.6
    """
    
    medicine_id: UUID
    medicine_name: str
    total_scheduled: int = Field(..., ge=0, description="Total scheduled doses")
    total_taken: int = Field(..., ge=0, description="Total doses taken")
    total_missed: int = Field(..., ge=0, description="Total doses missed")
    total_skipped: int = Field(..., ge=0, description="Total doses skipped")
    adherence_percentage: float = Field(
        ...,
        ge=0.0,
        le=100.0,
        description="Adherence percentage (taken/scheduled * 100)"
    )
    streak_current: int = Field(default=0, ge=0, description="Current consecutive doses taken")
    streak_longest: int = Field(default=0, ge=0, description="Longest consecutive doses taken")
    period_start: Optional[date] = Field(None, description="Start of statistics period")
    period_end: Optional[date] = Field(None, description="End of statistics period")


class OverallAdherenceStats(BaseModel):
    """Schema for overall adherence statistics across all medicines."""
    
    total_medicines: int = Field(..., ge=0)
    active_medicines: int = Field(..., ge=0)
    overall_adherence_percentage: float = Field(..., ge=0.0, le=100.0)
    medicines_needing_refill: int = Field(default=0, ge=0)
    medicines: List[AdherenceStats] = Field(default_factory=list)


# ============================================================================
# Reminder Schemas
# ============================================================================

class MedicineReminderResponse(BaseModel):
    """Response schema for upcoming medicine reminders."""
    
    dose_id: UUID
    medicine_id: UUID
    medicine_name: str
    dosage: Optional[str] = None
    scheduled_time: datetime
    instructions: Optional[str] = None


class RefillAlertResponse(BaseModel):
    """Response schema for refill alerts.
    
    Validates: Requirements 15.5
    """
    
    medicine_id: UUID
    medicine_name: str
    remaining_quantity: int
    refill_threshold: int
    days_until_empty: Optional[int] = None


# ============================================================================
# Paginated Responses
# ============================================================================

class PaginatedMedicineResponse(BaseModel):
    """Paginated response for medicines."""
    
    items: List[MedicineResponse]
    total: int = Field(..., ge=0, description="Total number of items")
    page: int = Field(..., ge=1, description="Current page number")
    page_size: int = Field(..., ge=1, description="Number of items per page")
    total_pages: int = Field(..., ge=0, description="Total number of pages")
    
    @classmethod
    def create(
        cls,
        items: List[MedicineResponse],
        total: int,
        page: int,
        page_size: int,
    ) -> "PaginatedMedicineResponse":
        """Create a paginated response."""
        total_pages = (total + page_size - 1) // page_size if total > 0 else 0
        return cls(
            items=items,
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
        )


class PaginatedDoseResponse(BaseModel):
    """Paginated response for doses."""
    
    items: List[DoseResponse]
    total: int = Field(..., ge=0, description="Total number of items")
    page: int = Field(..., ge=1, description="Current page number")
    page_size: int = Field(..., ge=1, description="Number of items per page")
    total_pages: int = Field(..., ge=0, description="Total number of pages")
    
    @classmethod
    def create(
        cls,
        items: List[DoseResponse],
        total: int,
        page: int,
        page_size: int,
    ) -> "PaginatedDoseResponse":
        """Create a paginated response."""
        total_pages = (total + page_size - 1) // page_size if total > 0 else 0
        return cls(
            items=items,
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
        )
