"""Pydantic schemas for health module.

Includes schemas for health record and family member management.

Validates: Requirements 14.1, 14.2, 14.5
"""

from datetime import datetime, date
from typing import Optional, List
from uuid import UUID

from pydantic import BaseModel, Field, field_validator


class HealthRecordCategory:
    """Valid health record categories.
    
    Validates: Requirements 14.1
    """
    PRESCRIPTION = "prescription"
    LAB_REPORT = "lab_report"
    SCAN = "scan"
    VACCINE = "vaccine"
    INSURANCE = "insurance"
    
    ALL = [PRESCRIPTION, LAB_REPORT, SCAN, VACCINE, INSURANCE]


# ============================================================================
# Family Member Schemas
# ============================================================================

class FamilyMemberCreate(BaseModel):
    """Schema for creating a new family member.
    
    Validates: Requirements 14.2
    """
    
    name: str = Field(..., min_length=1, max_length=255, description="Full name of the family member")
    relationship: str = Field(..., min_length=1, max_length=50, description="Relationship to the user")
    date_of_birth: Optional[date] = Field(None, description="Date of birth")
    gender: Optional[str] = Field(None, max_length=20, description="Gender")


class FamilyMemberUpdate(BaseModel):
    """Schema for updating a family member."""
    
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    relationship: Optional[str] = Field(None, min_length=1, max_length=50)
    date_of_birth: Optional[date] = None
    gender: Optional[str] = Field(None, max_length=20)


class FamilyMemberResponse(BaseModel):
    """Response schema for a family member.
    
    Validates: Requirements 14.2
    """
    
    id: UUID
    user_id: UUID
    name: str
    relationship: str
    date_of_birth: Optional[date] = None
    gender: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    
    model_config = {"from_attributes": True}


# ============================================================================
# Health Record Schemas
# ============================================================================

class HealthRecordCreate(BaseModel):
    """Schema for creating a new health record.
    
    Validates: Requirements 14.1, 14.2
    """
    
    category: str = Field(..., description="Record category")
    title: str = Field(..., min_length=1, max_length=255, description="Title of the health record")
    content_type: str = Field(..., description="MIME type of the document")
    file_size: int = Field(..., ge=0, description="File size in bytes")
    family_member_id: Optional[UUID] = Field(None, description="Family member ID (null for self)")
    record_date: Optional[date] = Field(None, description="Date of the health record")
    doctor_name: Optional[str] = Field(None, max_length=255, description="Doctor's name")
    hospital_name: Optional[str] = Field(None, max_length=255, description="Hospital/clinic name")
    notes: Optional[str] = Field(None, description="Additional notes")
    
    @field_validator("category")
    @classmethod
    def validate_category(cls, v: str) -> str:
        """Validate that category is one of the allowed values."""
        if v not in HealthRecordCategory.ALL:
            raise ValueError(f"Category must be one of: {', '.join(HealthRecordCategory.ALL)}")
        return v


class HealthRecordUpdate(BaseModel):
    """Schema for updating a health record."""
    
    category: Optional[str] = None
    title: Optional[str] = Field(None, min_length=1, max_length=255)
    family_member_id: Optional[UUID] = None
    record_date: Optional[date] = None
    doctor_name: Optional[str] = Field(None, max_length=255)
    hospital_name: Optional[str] = Field(None, max_length=255)
    notes: Optional[str] = None
    
    @field_validator("category")
    @classmethod
    def validate_category(cls, v: Optional[str]) -> Optional[str]:
        """Validate that category is one of the allowed values."""
        if v is not None and v not in HealthRecordCategory.ALL:
            raise ValueError(f"Category must be one of: {', '.join(HealthRecordCategory.ALL)}")
        return v


class HealthRecordResponse(BaseModel):
    """Response schema for a health record.
    
    Validates: Requirements 14.1, 14.2, 14.5
    """
    
    id: UUID
    user_id: UUID
    family_member_id: Optional[UUID] = None
    category: str
    title: str
    file_path: str
    content_type: str
    file_size: int
    ocr_text: Optional[str] = None
    extracted_data: Optional[dict] = None
    record_date: Optional[date] = None
    doctor_name: Optional[str] = None
    hospital_name: Optional[str] = None
    notes: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    
    model_config = {"from_attributes": True}


class HealthRecordWithFamilyMemberResponse(HealthRecordResponse):
    """Response schema for a health record with family member details."""
    
    family_member: Optional[FamilyMemberResponse] = None


# ============================================================================
# Filter and Search Schemas
# ============================================================================

class HealthRecordFilters(BaseModel):
    """Schema for health record filter parameters.
    
    Validates: Requirements 14.1, 14.2
    """
    
    category: Optional[str] = Field(None, description="Filter by category")
    family_member_id: Optional[UUID] = Field(None, description="Filter by family member")
    start_date: Optional[date] = Field(None, description="Filter records from this date")
    end_date: Optional[date] = Field(None, description="Filter records until this date")
    page: int = Field(default=1, ge=1, description="Page number (1-indexed)")
    page_size: int = Field(default=20, ge=1, le=100, description="Number of results per page")
    
    @field_validator("category")
    @classmethod
    def validate_category(cls, v: Optional[str]) -> Optional[str]:
        """Validate that category is one of the allowed values."""
        if v is not None and v not in HealthRecordCategory.ALL:
            raise ValueError(f"Category must be one of: {', '.join(HealthRecordCategory.ALL)}")
        return v


class HealthRecordSearchQuery(BaseModel):
    """Schema for health record search query parameters."""
    
    query: str = Field(..., min_length=1, max_length=500, description="Search query string")
    category: Optional[str] = Field(None, description="Optional category filter")
    family_member_id: Optional[UUID] = Field(None, description="Optional family member filter")
    page: int = Field(default=1, ge=1, description="Page number (1-indexed)")
    page_size: int = Field(default=20, ge=1, le=100, description="Number of results per page")
    
    @field_validator("category")
    @classmethod
    def validate_category(cls, v: Optional[str]) -> Optional[str]:
        """Validate that category is one of the allowed values."""
        if v is not None and v not in HealthRecordCategory.ALL:
            raise ValueError(f"Category must be one of: {', '.join(HealthRecordCategory.ALL)}")
        return v


# ============================================================================
# Paginated Response
# ============================================================================

class PaginatedHealthRecordResponse(BaseModel):
    """Paginated response for health records."""
    
    items: List[HealthRecordResponse]
    total: int = Field(..., ge=0, description="Total number of items")
    page: int = Field(..., ge=1, description="Current page number")
    page_size: int = Field(..., ge=1, description="Number of items per page")
    total_pages: int = Field(..., ge=0, description="Total number of pages")
    
    @classmethod
    def create(
        cls,
        items: List[HealthRecordResponse],
        total: int,
        page: int,
        page_size: int,
    ) -> "PaginatedHealthRecordResponse":
        """Create a paginated response."""
        total_pages = (total + page_size - 1) // page_size if total > 0 else 0
        return cls(
            items=items,
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
        )


class PaginatedFamilyMemberResponse(BaseModel):
    """Paginated response for family members."""
    
    items: List[FamilyMemberResponse]
    total: int = Field(..., ge=0, description="Total number of items")
    page: int = Field(..., ge=1, description="Current page number")
    page_size: int = Field(..., ge=1, description="Number of items per page")
    total_pages: int = Field(..., ge=0, description="Total number of pages")
    
    @classmethod
    def create(
        cls,
        items: List[FamilyMemberResponse],
        total: int,
        page: int,
        page_size: int,
    ) -> "PaginatedFamilyMemberResponse":
        """Create a paginated response."""
        total_pages = (total + page_size - 1) // page_size if total > 0 else 0
        return cls(
            items=items,
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
        )


# ============================================================================
# Timeline Schemas
# ============================================================================

class TimelineEntryResponse(BaseModel):
    """Response schema for a health timeline entry.
    
    Validates: Requirements 14.5, 14.6
    """
    
    id: UUID
    category: str
    title: str
    record_date: Optional[date] = None
    doctor_name: Optional[str] = None
    hospital_name: Optional[str] = None
    family_member_id: Optional[UUID] = None
    family_member_name: Optional[str] = None
    created_at: datetime
    
    model_config = {"from_attributes": True}


class HealthTimelineResponse(BaseModel):
    """Response schema for health timeline.
    
    Validates: Requirements 14.5, 14.6
    """
    
    items: List[TimelineEntryResponse]
    total: int = Field(..., ge=0, description="Total number of items")
    page: int = Field(..., ge=1, description="Current page number")
    page_size: int = Field(..., ge=1, description="Number of items per page")
    total_pages: int = Field(..., ge=0, description="Total number of pages")
    
    @classmethod
    def create(
        cls,
        items: List[TimelineEntryResponse],
        total: int,
        page: int,
        page_size: int,
    ) -> "HealthTimelineResponse":
        """Create a timeline response."""
        total_pages = (total + page_size - 1) // page_size if total > 0 else 0
        return cls(
            items=items,
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
        )
