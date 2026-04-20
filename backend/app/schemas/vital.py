"""Pydantic schemas for vitals tracking module.

Includes schemas for vital CRUD operations, target ranges,
trends, and PDF export.

Validates: Requirements 16.1, 16.2, 16.3, 16.4, 16.5
"""

from datetime import datetime, date
from typing import Optional, List
from uuid import UUID

from pydantic import BaseModel, Field, field_validator


class VitalTypeEnum:
    """Valid vital type options.
    
    Validates: Requirements 16.1
    """
    BLOOD_PRESSURE_SYSTOLIC = "blood_pressure_systolic"
    BLOOD_PRESSURE_DIASTOLIC = "blood_pressure_diastolic"
    HEART_RATE = "heart_rate"
    WEIGHT = "weight"
    TEMPERATURE = "temperature"
    BLOOD_SUGAR = "blood_sugar"
    OXYGEN_SATURATION = "oxygen_saturation"
    RESPIRATORY_RATE = "respiratory_rate"
    
    ALL = [
        BLOOD_PRESSURE_SYSTOLIC, BLOOD_PRESSURE_DIASTOLIC, HEART_RATE,
        WEIGHT, TEMPERATURE, BLOOD_SUGAR, OXYGEN_SATURATION, RESPIRATORY_RATE
    ]


class WarningLevel(str):
    """Warning levels for out-of-range readings.
    
    Validates: Requirements 16.3
    """
    NORMAL = "normal"
    LOW = "low"
    HIGH = "high"
    CRITICAL_LOW = "critical_low"
    CRITICAL_HIGH = "critical_high"


# ============================================================================
# Vital Schemas
# ============================================================================

class VitalCreate(BaseModel):
    """Schema for creating a new vital reading.
    
    Validates: Requirements 16.1
    """
    
    vital_type: str = Field(..., description="Type of vital reading")
    value: float = Field(..., description="Numeric value of the reading")
    unit: str = Field(..., max_length=20, description="Unit of measurement")
    family_member_id: Optional[UUID] = Field(None, description="Family member ID (null for self)")
    notes: Optional[str] = Field(None, description="Optional notes about the reading")
    recorded_at: Optional[datetime] = Field(None, description="When the vital was recorded (defaults to now)")
    
    @field_validator("vital_type")
    @classmethod
    def validate_vital_type(cls, v: str) -> str:
        """Validate that vital_type is one of the allowed values."""
        if v not in VitalTypeEnum.ALL:
            raise ValueError(f"Vital type must be one of: {', '.join(VitalTypeEnum.ALL)}")
        return v


class VitalUpdate(BaseModel):
    """Schema for updating a vital reading."""
    
    value: Optional[float] = Field(None, description="Numeric value of the reading")
    unit: Optional[str] = Field(None, max_length=20, description="Unit of measurement")
    notes: Optional[str] = Field(None, description="Optional notes about the reading")
    recorded_at: Optional[datetime] = Field(None, description="When the vital was recorded")


class VitalResponse(BaseModel):
    """Response schema for a vital reading.
    
    Validates: Requirements 16.1, 16.3
    """
    
    id: UUID
    user_id: UUID
    family_member_id: Optional[UUID] = None
    vital_type: str
    value: float
    unit: str
    notes: Optional[str] = None
    recorded_at: datetime
    warning_level: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    
    model_config = {"from_attributes": True}


class VitalWithFamilyMemberResponse(VitalResponse):
    """Response schema for a vital with family member name."""
    
    family_member_name: Optional[str] = None


# ============================================================================
# Target Range Schemas
# ============================================================================

class VitalTargetRangeCreate(BaseModel):
    """Schema for creating a custom target range.
    
    Validates: Requirements 16.4
    """
    
    vital_type: str = Field(..., description="Type of vital this range applies to")
    min_value: Optional[float] = Field(None, description="Minimum acceptable value")
    max_value: Optional[float] = Field(None, description="Maximum acceptable value")
    family_member_id: Optional[UUID] = Field(None, description="Family member ID (null for self)")
    
    @field_validator("vital_type")
    @classmethod
    def validate_vital_type(cls, v: str) -> str:
        """Validate that vital_type is one of the allowed values."""
        if v not in VitalTypeEnum.ALL:
            raise ValueError(f"Vital type must be one of: {', '.join(VitalTypeEnum.ALL)}")
        return v


class VitalTargetRangeUpdate(BaseModel):
    """Schema for updating a custom target range."""
    
    min_value: Optional[float] = Field(None, description="Minimum acceptable value")
    max_value: Optional[float] = Field(None, description="Maximum acceptable value")


class VitalTargetRangeResponse(BaseModel):
    """Response schema for a target range.
    
    Validates: Requirements 16.4
    """
    
    id: UUID
    user_id: UUID
    family_member_id: Optional[UUID] = None
    vital_type: str
    min_value: Optional[float] = None
    max_value: Optional[float] = None
    created_at: datetime
    updated_at: datetime
    
    model_config = {"from_attributes": True}


# ============================================================================
# Trend Schemas
# ============================================================================

class VitalTrendDataPoint(BaseModel):
    """A single data point in a vital trend.
    
    Validates: Requirements 16.2
    """
    
    recorded_at: datetime
    value: float
    warning_level: str = WarningLevel.NORMAL


class VitalTrendResponse(BaseModel):
    """Response schema for vital trends.
    
    Validates: Requirements 16.2, 16.3
    """
    
    vital_type: str
    unit: str
    data_points: List[VitalTrendDataPoint]
    min_value: Optional[float] = None
    max_value: Optional[float] = None
    avg_value: Optional[float] = None
    target_min: Optional[float] = None
    target_max: Optional[float] = None
    period_start: date
    period_end: date
    total_readings: int


class VitalSummary(BaseModel):
    """Summary statistics for a vital type."""
    
    vital_type: str
    unit: str
    latest_value: Optional[float] = None
    latest_recorded_at: Optional[datetime] = None
    latest_warning_level: Optional[str] = None
    avg_value: Optional[float] = None
    min_value: Optional[float] = None
    max_value: Optional[float] = None
    reading_count: int = 0
    target_min: Optional[float] = None
    target_max: Optional[float] = None


class VitalsDashboardResponse(BaseModel):
    """Response schema for vitals dashboard overview."""
    
    summaries: List[VitalSummary]
    recent_readings: List[VitalWithFamilyMemberResponse]
    out_of_range_count: int = 0


# ============================================================================
# PDF Export Schemas
# ============================================================================

class VitalExportRequest(BaseModel):
    """Request schema for exporting vitals report.
    
    Validates: Requirements 16.5
    """
    
    start_date: date = Field(..., description="Start date for the report")
    end_date: date = Field(..., description="End date for the report")
    vital_types: Optional[List[str]] = Field(None, description="Specific vital types to include (null for all)")
    family_member_id: Optional[UUID] = Field(None, description="Family member ID (null for self)")
    include_charts: bool = Field(default=True, description="Whether to include trend charts")
    
    @field_validator("vital_types")
    @classmethod
    def validate_vital_types(cls, v: Optional[List[str]]) -> Optional[List[str]]:
        """Validate that all vital_types are valid."""
        if v is not None:
            for vt in v:
                if vt not in VitalTypeEnum.ALL:
                    raise ValueError(f"Vital type must be one of: {', '.join(VitalTypeEnum.ALL)}")
        return v


# ============================================================================
# Paginated Responses
# ============================================================================

class PaginatedVitalResponse(BaseModel):
    """Paginated response for vitals."""
    
    items: List[VitalResponse]
    total: int = Field(..., ge=0, description="Total number of items")
    page: int = Field(..., ge=1, description="Current page number")
    page_size: int = Field(..., ge=1, description="Number of items per page")
    total_pages: int = Field(..., ge=0, description="Total number of pages")
    
    @classmethod
    def create(
        cls,
        items: List[VitalResponse],
        total: int,
        page: int,
        page_size: int,
    ) -> "PaginatedVitalResponse":
        """Create a paginated response."""
        total_pages = (total + page_size - 1) // page_size if total > 0 else 0
        return cls(
            items=items,
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
        )


class PaginatedVitalTargetRangeResponse(BaseModel):
    """Paginated response for target ranges."""
    
    items: List[VitalTargetRangeResponse]
    total: int = Field(..., ge=0, description="Total number of items")
    page: int = Field(..., ge=1, description="Current page number")
    page_size: int = Field(..., ge=1, description="Number of items per page")
    total_pages: int = Field(..., ge=0, description="Total number of pages")
    
    @classmethod
    def create(
        cls,
        items: List[VitalTargetRangeResponse],
        total: int,
        page: int,
        page_size: int,
    ) -> "PaginatedVitalTargetRangeResponse":
        """Create a paginated response."""
        total_pages = (total + page_size - 1) // page_size if total > 0 else 0
        return cls(
            items=items,
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
        )
