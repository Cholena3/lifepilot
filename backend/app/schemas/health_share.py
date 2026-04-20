"""Pydantic schemas for health record sharing module.

Includes schemas for creating share links, accessing shared records,
and viewing access logs.

Validates: Requirements 18.1, 18.2, 18.3, 18.4, 18.5
"""

from datetime import datetime
from typing import Optional, List
from uuid import UUID

from pydantic import BaseModel, Field, field_validator


# ============================================================================
# Health Record Share Schemas
# ============================================================================

class HealthRecordShareCreate(BaseModel):
    """Schema for creating a health record share link.
    
    Validates: Requirements 18.1, 18.2
    """
    
    record_ids: List[UUID] = Field(..., min_length=1, description="List of health record IDs to share")
    doctor_name: Optional[str] = Field(None, max_length=255, description="Name of the doctor")
    doctor_email: Optional[str] = Field(None, max_length=255, description="Email of the doctor")
    purpose: Optional[str] = Field(None, max_length=255, description="Purpose of sharing")
    expires_in_hours: int = Field(default=72, ge=1, le=720, description="Hours until link expires (1-720)")
    notes: Optional[str] = Field(None, description="Notes for the doctor")


class HealthRecordShareUpdate(BaseModel):
    """Schema for updating a health record share."""
    
    doctor_name: Optional[str] = Field(None, max_length=255)
    doctor_email: Optional[str] = Field(None, max_length=255)
    purpose: Optional[str] = Field(None, max_length=255)
    notes: Optional[str] = None


class HealthRecordShareResponse(BaseModel):
    """Response schema for a health record share.
    
    Validates: Requirements 18.1, 18.2, 18.5
    """
    
    id: UUID
    user_id: UUID
    public_token: str
    doctor_name: Optional[str] = None
    doctor_email: Optional[str] = None
    purpose: Optional[str] = None
    record_ids: List[UUID]
    expires_at: datetime
    is_revoked: bool
    is_expired: bool
    is_valid: bool
    access_count: int
    last_accessed_at: Optional[datetime] = None
    notes: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    
    model_config = {"from_attributes": True}


# ============================================================================
# Public Access Schemas
# ============================================================================

class SharedHealthRecordInfo(BaseModel):
    """Information about a shared health record (read-only view).
    
    Validates: Requirements 18.3
    """
    
    id: UUID
    category: str
    title: str
    record_date: Optional[datetime] = None
    doctor_name: Optional[str] = None
    hospital_name: Optional[str] = None
    notes: Optional[str] = None
    family_member_name: Optional[str] = None


class PublicHealthShareResponse(BaseModel):
    """Response schema for public access to shared health records.
    
    Validates: Requirements 18.3, 18.4
    """
    
    share_id: UUID
    doctor_name: Optional[str] = None
    purpose: Optional[str] = None
    notes: Optional[str] = None
    records: List[SharedHealthRecordInfo]
    expires_at: datetime
    shared_by_notes: Optional[str] = None


# ============================================================================
# Access Log Schemas
# ============================================================================

class HealthShareAccessLogResponse(BaseModel):
    """Response schema for a share access log entry.
    
    Validates: Requirements 18.5
    """
    
    id: UUID
    share_id: UUID
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    accessed_at: datetime
    
    model_config = {"from_attributes": True}


class HealthRecordShareDetailResponse(HealthRecordShareResponse):
    """Detailed response including access logs.
    
    Validates: Requirements 18.5
    """
    
    access_logs: List[HealthShareAccessLogResponse] = []


# ============================================================================
# Paginated Responses
# ============================================================================

class PaginatedHealthRecordShareResponse(BaseModel):
    """Paginated response for health record shares."""
    
    items: List[HealthRecordShareResponse]
    total: int = Field(..., ge=0, description="Total number of items")
    page: int = Field(..., ge=1, description="Current page number")
    page_size: int = Field(..., ge=1, description="Number of items per page")
    total_pages: int = Field(..., ge=0, description="Total number of pages")
    
    @classmethod
    def create(
        cls,
        items: List[HealthRecordShareResponse],
        total: int,
        page: int,
        page_size: int,
    ) -> "PaginatedHealthRecordShareResponse":
        """Create a paginated response."""
        total_pages = (total + page_size - 1) // page_size if total > 0 else 0
        return cls(
            items=items,
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
        )
