"""Pydantic schemas for emergency health information module.

Includes schemas for emergency info CRUD operations, visibility configuration,
and public access responses.

Validates: Requirements 17.1, 17.2, 17.3, 17.4, 17.5
"""

from datetime import datetime
from typing import Optional, List
from uuid import UUID

from pydantic import BaseModel, Field, field_validator

from app.models.emergency_info import EmergencyInfoField, BloodType


# ============================================================================
# Emergency Contact Schema
# ============================================================================

class EmergencyContact(BaseModel):
    """Schema for an emergency contact.
    
    Validates: Requirements 17.1
    """
    
    name: str = Field(..., min_length=1, max_length=255, description="Contact's name")
    phone: str = Field(..., min_length=1, max_length=50, description="Contact's phone number")
    relationship: Optional[str] = Field(None, max_length=50, description="Relationship to user")


# ============================================================================
# Emergency Info Create/Update Schemas
# ============================================================================

class EmergencyInfoCreate(BaseModel):
    """Schema for creating emergency health information.
    
    Validates: Requirements 17.1
    """
    
    blood_type: Optional[str] = Field(None, description="Blood type")
    allergies: Optional[List[str]] = Field(None, description="List of allergies")
    medical_conditions: Optional[List[str]] = Field(None, description="List of medical conditions")
    emergency_contacts: Optional[List[EmergencyContact]] = Field(None, description="Emergency contacts")
    current_medications: Optional[List[str]] = Field(None, description="Current medications")
    visible_fields: Optional[List[str]] = Field(
        None, 
        description="Fields visible on public emergency page"
    )
    
    @field_validator("blood_type")
    @classmethod
    def validate_blood_type(cls, v: Optional[str]) -> Optional[str]:
        """Validate that blood_type is one of the allowed values."""
        if v is not None and v not in BloodType.ALL:
            raise ValueError(f"Blood type must be one of: {', '.join(BloodType.ALL)}")
        return v
    
    @field_validator("visible_fields")
    @classmethod
    def validate_visible_fields(cls, v: Optional[List[str]]) -> Optional[List[str]]:
        """Validate that all visible_fields are valid field names."""
        if v is not None:
            for field in v:
                if field not in EmergencyInfoField.ALL:
                    raise ValueError(
                        f"Visible field must be one of: {', '.join(EmergencyInfoField.ALL)}"
                    )
        return v


class EmergencyInfoUpdate(BaseModel):
    """Schema for updating emergency health information.
    
    Validates: Requirements 17.1, 17.5
    """
    
    blood_type: Optional[str] = Field(None, description="Blood type")
    allergies: Optional[List[str]] = Field(None, description="List of allergies")
    medical_conditions: Optional[List[str]] = Field(None, description="List of medical conditions")
    emergency_contacts: Optional[List[EmergencyContact]] = Field(None, description="Emergency contacts")
    current_medications: Optional[List[str]] = Field(None, description="Current medications")
    
    @field_validator("blood_type")
    @classmethod
    def validate_blood_type(cls, v: Optional[str]) -> Optional[str]:
        """Validate that blood_type is one of the allowed values."""
        if v is not None and v not in BloodType.ALL:
            raise ValueError(f"Blood type must be one of: {', '.join(BloodType.ALL)}")
        return v


class VisibilityUpdate(BaseModel):
    """Schema for updating visible fields configuration.
    
    Validates: Requirements 17.5
    """
    
    visible_fields: List[str] = Field(..., description="Fields visible on public emergency page")
    
    @field_validator("visible_fields")
    @classmethod
    def validate_visible_fields(cls, v: List[str]) -> List[str]:
        """Validate that all visible_fields are valid field names."""
        for field in v:
            if field not in EmergencyInfoField.ALL:
                raise ValueError(
                    f"Visible field must be one of: {', '.join(EmergencyInfoField.ALL)}"
                )
        return v


# ============================================================================
# Response Schemas
# ============================================================================

class EmergencyInfoResponse(BaseModel):
    """Response schema for emergency health information.
    
    Validates: Requirements 17.1, 17.5
    """
    
    id: UUID
    user_id: UUID
    public_token: str
    blood_type: Optional[str] = None
    allergies: Optional[List[str]] = None
    medical_conditions: Optional[List[str]] = None
    emergency_contacts: Optional[List[EmergencyContact]] = None
    current_medications: Optional[List[str]] = None
    visible_fields: Optional[List[str]] = None
    qr_code_path: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    
    model_config = {"from_attributes": True}


class PublicEmergencyInfoResponse(BaseModel):
    """Response schema for public emergency page (filtered by visible_fields).
    
    Validates: Requirements 17.3, 17.4
    
    This schema only includes fields that the user has configured as visible.
    """
    
    blood_type: Optional[str] = None
    allergies: Optional[List[str]] = None
    medical_conditions: Optional[List[str]] = None
    emergency_contacts: Optional[List[EmergencyContact]] = None
    current_medications: Optional[List[str]] = None
    
    model_config = {"from_attributes": True}


class QRCodeResponse(BaseModel):
    """Response schema for QR code generation.
    
    Validates: Requirements 17.2
    """
    
    qr_code_url: str = Field(..., description="URL to the QR code image")
    public_url: str = Field(..., description="Public URL that the QR code links to")
    public_token: str = Field(..., description="Public access token")


# ============================================================================
# Field Info Schemas
# ============================================================================

class EmergencyFieldInfo(BaseModel):
    """Information about an emergency info field."""
    
    name: str
    display_name: str
    description: str


class AvailableFieldsResponse(BaseModel):
    """Response schema for available emergency info fields."""
    
    fields: List[EmergencyFieldInfo]
    blood_types: List[str]
