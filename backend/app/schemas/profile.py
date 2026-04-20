"""Profile schemas for user profile management.

Validates: Requirements 2.1, 2.4, 2.5
"""

from datetime import date
from decimal import Decimal
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field, field_validator


class ProfileBase(BaseModel):
    """Base schema for profile data."""
    
    first_name: Optional[str] = Field(
        None,
        max_length=100,
        description="User's first name",
        examples=["John"],
    )
    last_name: Optional[str] = Field(
        None,
        max_length=100,
        description="User's last name",
        examples=["Doe"],
    )
    date_of_birth: Optional[date] = Field(
        None,
        description="User's date of birth",
        examples=["1995-06-15"],
    )
    gender: Optional[str] = Field(
        None,
        max_length=20,
        description="User's gender",
        examples=["male", "female", "other"],
    )
    avatar_url: Optional[str] = Field(
        None,
        max_length=500,
        description="URL to user's avatar image",
    )


class ProfileCreate(ProfileBase):
    """Schema for creating a profile.
    
    Validates: Requirements 2.1
    """
    pass


class ProfileUpdate(ProfileBase):
    """Schema for updating a profile.
    
    Validates: Requirements 2.1
    """
    pass


class ProfileResponse(ProfileBase):
    """Schema for profile response.
    
    Validates: Requirements 2.1
    """
    
    id: UUID = Field(..., description="Profile unique identifier")
    user_id: UUID = Field(..., description="User's unique identifier")
    completion_percentage: int = Field(
        ...,
        ge=0,
        le=100,
        description="Profile completion percentage",
    )
    
    model_config = {"from_attributes": True}


# Student Profile Schemas

class StudentProfileBase(BaseModel):
    """Base schema for student profile data."""
    
    institution: Optional[str] = Field(
        None,
        max_length=255,
        description="Name of educational institution",
        examples=["MIT", "Stanford University"],
    )
    degree: Optional[str] = Field(
        None,
        max_length=100,
        description="Degree type",
        examples=["B.Tech", "M.Tech", "MBA"],
    )
    branch: Optional[str] = Field(
        None,
        max_length=100,
        description="Branch/major of study",
        examples=["Computer Science", "Electrical Engineering"],
    )
    cgpa: Optional[Decimal] = Field(
        None,
        ge=Decimal("0.0"),
        le=Decimal("10.0"),
        description="Cumulative GPA (0.0-10.0)",
        examples=[8.5, 9.0],
    )
    backlogs: Optional[int] = Field(
        None,
        ge=0,
        description="Number of backlogs",
        examples=[0, 1, 2],
    )
    graduation_year: Optional[int] = Field(
        None,
        ge=1900,
        le=2100,
        description="Expected graduation year",
        examples=[2024, 2025],
    )
    
    @field_validator("cgpa")
    @classmethod
    def validate_cgpa_range(cls, v: Optional[Decimal]) -> Optional[Decimal]:
        """Validate CGPA is between 0.0 and 10.0.
        
        Validates: Requirements 2.4
        """
        if v is not None:
            if v < Decimal("0.0") or v > Decimal("10.0"):
                raise ValueError("CGPA must be between 0.0 and 10.0")
        return v


class StudentProfileCreate(StudentProfileBase):
    """Schema for creating a student profile.
    
    Validates: Requirements 2.1
    """
    pass


class StudentProfileUpdate(StudentProfileBase):
    """Schema for updating a student profile.
    
    Validates: Requirements 2.1, 2.4
    """
    pass


class StudentProfileResponse(StudentProfileBase):
    """Schema for student profile response.
    
    Validates: Requirements 2.1
    """
    
    id: UUID = Field(..., description="Student profile unique identifier")
    user_id: UUID = Field(..., description="User's unique identifier")
    
    model_config = {"from_attributes": True}


# Career Preferences Schemas

class CareerPreferencesBase(BaseModel):
    """Base schema for career preferences data."""
    
    preferred_roles: Optional[list[str]] = Field(
        None,
        description="List of preferred job roles",
        examples=[["Software Engineer", "Data Scientist"]],
    )
    preferred_locations: Optional[list[str]] = Field(
        None,
        description="List of preferred work locations",
        examples=[["San Francisco", "New York", "Remote"]],
    )
    min_salary: Optional[Decimal] = Field(
        None,
        ge=Decimal("0"),
        description="Minimum expected salary",
        examples=[50000, 80000],
    )
    max_salary: Optional[Decimal] = Field(
        None,
        ge=Decimal("0"),
        description="Maximum expected salary",
        examples=[100000, 150000],
    )
    job_type: Optional[str] = Field(
        None,
        max_length=50,
        description="Type of job",
        examples=["full-time", "part-time", "internship", "contract"],
    )
    
    @field_validator("max_salary")
    @classmethod
    def validate_salary_range(cls, v: Optional[Decimal], info) -> Optional[Decimal]:
        """Validate max_salary >= min_salary if both are provided."""
        if v is not None and info.data.get("min_salary") is not None:
            if v < info.data["min_salary"]:
                raise ValueError("max_salary must be greater than or equal to min_salary")
        return v


class CareerPreferencesCreate(CareerPreferencesBase):
    """Schema for creating career preferences.
    
    Validates: Requirements 2.5
    """
    pass


class CareerPreferencesUpdate(CareerPreferencesBase):
    """Schema for updating career preferences.
    
    Validates: Requirements 2.5
    """
    pass


class CareerPreferencesResponse(CareerPreferencesBase):
    """Schema for career preferences response.
    
    Validates: Requirements 2.5
    """
    
    id: UUID = Field(..., description="Career preferences unique identifier")
    user_id: UUID = Field(..., description="User's unique identifier")
    
    model_config = {"from_attributes": True}
