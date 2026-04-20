"""Profile router for user profile management endpoints.

Validates: Requirements 2.1, 2.4, 2.5
"""

from typing import Annotated

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import CurrentUser
from app.schemas.profile import (
    CareerPreferencesResponse,
    CareerPreferencesUpdate,
    ProfileResponse,
    ProfileUpdate,
    StudentProfileResponse,
    StudentProfileUpdate,
)
from app.services.profile import ProfileService

router = APIRouter()


@router.get(
    "",
    response_model=ProfileResponse,
    status_code=status.HTTP_200_OK,
    summary="Get current user's profile",
    description="Retrieve the authenticated user's profile information.",
    responses={
        200: {"description": "Profile retrieved successfully"},
        401: {"description": "Not authenticated"},
        404: {"description": "Profile not found"},
    },
)
async def get_profile(
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ProfileResponse:
    """Get the current user's profile.
    
    Validates: Requirements 2.1
    
    Args:
        current_user: Authenticated user (injected)
        db: Database session (injected)
        
    Returns:
        ProfileResponse with user's profile data
        
    Raises:
        HTTPException 401: Not authenticated
        HTTPException 404: Profile not found
    """
    service = ProfileService(db)
    return await service.get_profile(current_user.id)


@router.put(
    "",
    response_model=ProfileResponse,
    status_code=status.HTTP_200_OK,
    summary="Update current user's profile",
    description="Update the authenticated user's profile information.",
    responses={
        200: {"description": "Profile updated successfully"},
        401: {"description": "Not authenticated"},
    },
)
async def update_profile(
    profile_data: ProfileUpdate,
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> ProfileResponse:
    """Update the current user's profile.
    
    Validates: Requirements 2.1
    
    Args:
        profile_data: Profile update data
        current_user: Authenticated user (injected)
        db: Database session (injected)
        
    Returns:
        ProfileResponse with updated profile data
        
    Raises:
        HTTPException 401: Not authenticated
    """
    service = ProfileService(db)
    return await service.update_profile(current_user.id, profile_data)


@router.get(
    "/student",
    response_model=StudentProfileResponse,
    status_code=status.HTTP_200_OK,
    summary="Get current user's student profile",
    description="Retrieve the authenticated user's student profile information.",
    responses={
        200: {"description": "Student profile retrieved successfully"},
        401: {"description": "Not authenticated"},
        404: {"description": "Student profile not found"},
    },
)
async def get_student_profile(
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> StudentProfileResponse:
    """Get the current user's student profile.
    
    Validates: Requirements 2.1
    
    Args:
        current_user: Authenticated user (injected)
        db: Database session (injected)
        
    Returns:
        StudentProfileResponse with user's student profile data
        
    Raises:
        HTTPException 401: Not authenticated
        HTTPException 404: Student profile not found
    """
    service = ProfileService(db)
    return await service.get_student_profile(current_user.id)


@router.put(
    "/student",
    response_model=StudentProfileResponse,
    status_code=status.HTTP_200_OK,
    summary="Update current user's student profile",
    description="Update the authenticated user's student profile information. CGPA must be between 0.0 and 10.0.",
    responses={
        200: {"description": "Student profile updated successfully"},
        401: {"description": "Not authenticated"},
        422: {"description": "Validation error (e.g., CGPA out of range)"},
    },
)
async def update_student_profile(
    student_profile_data: StudentProfileUpdate,
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> StudentProfileResponse:
    """Update the current user's student profile.
    
    Validates: Requirements 2.1, 2.4
    
    - CGPA must be between 0.0 and 10.0 (Requirement 2.4)
    
    Args:
        student_profile_data: Student profile update data
        current_user: Authenticated user (injected)
        db: Database session (injected)
        
    Returns:
        StudentProfileResponse with updated student profile data
        
    Raises:
        HTTPException 401: Not authenticated
        HTTPException 422: Validation error (e.g., CGPA out of range)
    """
    service = ProfileService(db)
    return await service.update_student_profile(current_user.id, student_profile_data)


@router.get(
    "/career",
    response_model=CareerPreferencesResponse,
    status_code=status.HTTP_200_OK,
    summary="Get current user's career preferences",
    description="Retrieve the authenticated user's career preferences.",
    responses={
        200: {"description": "Career preferences retrieved successfully"},
        401: {"description": "Not authenticated"},
        404: {"description": "Career preferences not found"},
    },
)
async def get_career_preferences(
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> CareerPreferencesResponse:
    """Get the current user's career preferences.
    
    Validates: Requirements 2.5
    
    Args:
        current_user: Authenticated user (injected)
        db: Database session (injected)
        
    Returns:
        CareerPreferencesResponse with user's career preferences data
        
    Raises:
        HTTPException 401: Not authenticated
        HTTPException 404: Career preferences not found
    """
    service = ProfileService(db)
    return await service.get_career_preferences(current_user.id)


@router.put(
    "/career",
    response_model=CareerPreferencesResponse,
    status_code=status.HTTP_200_OK,
    summary="Update current user's career preferences",
    description="Update the authenticated user's career preferences including preferred roles, locations, and salary expectations.",
    responses={
        200: {"description": "Career preferences updated successfully"},
        401: {"description": "Not authenticated"},
        422: {"description": "Validation error"},
    },
)
async def update_career_preferences(
    career_preferences_data: CareerPreferencesUpdate,
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> CareerPreferencesResponse:
    """Update the current user's career preferences.
    
    Validates: Requirements 2.5
    
    Args:
        career_preferences_data: Career preferences update data
        current_user: Authenticated user (injected)
        db: Database session (injected)
        
    Returns:
        CareerPreferencesResponse with updated career preferences data
        
    Raises:
        HTTPException 401: Not authenticated
        HTTPException 422: Validation error
    """
    service = ProfileService(db)
    return await service.update_career_preferences(
        current_user.id, career_preferences_data
    )
