"""API router for learning progress tracking.

Validates: Requirements 25.1, 25.2, 25.3, 25.4, 25.5
"""

import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.schemas.course import (
    CourseCreate,
    CourseProgressUpdate,
    CourseResponse,
    CourseUpdate,
    CourseWithSessionsResponse,
    InactiveCourseResponse,
    LearningSessionCreate,
    LearningSessionResponse,
    LearningStatsResponse,
    PaginatedCourseResponse,
)
from app.services.course import CourseService

router = APIRouter(prefix="/courses", tags=["career"])


def get_current_user_id() -> uuid.UUID:
    """Get current user ID from auth context.
    
    TODO: Replace with actual auth dependency when auth is integrated.
    """
    return uuid.UUID("00000000-0000-0000-0000-000000000001")


@router.post(
    "",
    response_model=CourseResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Add a new course",
    description="Add a new course to track learning progress. Requirement 25.1",
)
async def create_course(
    data: CourseCreate,
    db: AsyncSession = Depends(get_db),
    user_id: uuid.UUID = Depends(get_current_user_id),
) -> CourseResponse:
    """Create a new course for the current user."""
    service = CourseService(db)
    try:
        course = await service.add_course(user_id, data)
        return CourseResponse.model_validate(course)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(e),
        )


@router.get(
    "",
    response_model=PaginatedCourseResponse,
    summary="List courses",
    description="Get a paginated list of user's courses with optional filtering.",
)
async def list_courses(
    is_completed: Optional[bool] = Query(None, description="Filter by completion status"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    db: AsyncSession = Depends(get_db),
    user_id: uuid.UUID = Depends(get_current_user_id),
) -> PaginatedCourseResponse:
    """Get paginated list of courses for the current user."""
    service = CourseService(db)
    return await service.get_courses(
        user_id=user_id,
        is_completed=is_completed,
        page=page,
        page_size=page_size,
    )


@router.get(
    "/stats",
    response_model=LearningStatsResponse,
    summary="Get learning statistics",
    description="Get learning statistics including streak and hours invested. Requirement 25.3",
)
async def get_learning_stats(
    db: AsyncSession = Depends(get_db),
    user_id: uuid.UUID = Depends(get_current_user_id),
) -> LearningStatsResponse:
    """Get learning statistics for the current user."""
    service = CourseService(db)
    return await service.get_learning_stats(user_id)


@router.get(
    "/inactive",
    response_model=list[InactiveCourseResponse],
    summary="Get inactive courses",
    description="Get courses with no progress in the specified number of days. Requirement 25.5",
)
async def get_inactive_courses(
    days: int = Query(7, ge=1, le=365, description="Number of days of inactivity"),
    db: AsyncSession = Depends(get_db),
    user_id: uuid.UUID = Depends(get_current_user_id),
) -> list[InactiveCourseResponse]:
    """Get inactive courses for the current user."""
    service = CourseService(db)
    return await service.get_inactive_courses(user_id, days)


@router.post(
    "/inactive/remind",
    summary="Send inactive course reminders",
    description="Send reminders for courses with no progress. Requirement 25.5",
)
async def send_inactive_reminders(
    days: int = Query(7, ge=1, le=365, description="Number of days of inactivity"),
    db: AsyncSession = Depends(get_db),
    user_id: uuid.UUID = Depends(get_current_user_id),
) -> dict:
    """Send reminders for inactive courses."""
    service = CourseService(db)
    count = await service.send_inactive_course_reminders(user_id, days)
    return {"reminders_sent": count}


@router.get(
    "/{course_id}",
    response_model=CourseWithSessionsResponse,
    summary="Get course details",
    description="Get a course with its learning sessions.",
)
async def get_course(
    course_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user_id: uuid.UUID = Depends(get_current_user_id),
) -> CourseWithSessionsResponse:
    """Get a course by ID with learning sessions."""
    service = CourseService(db)
    course = await service.get_course_with_sessions(course_id, user_id)
    if not course:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Course not found",
        )
    return course


@router.put(
    "/{course_id}",
    response_model=CourseResponse,
    summary="Update a course",
    description="Update a course's details.",
)
async def update_course(
    course_id: uuid.UUID,
    data: CourseUpdate,
    db: AsyncSession = Depends(get_db),
    user_id: uuid.UUID = Depends(get_current_user_id),
) -> CourseResponse:
    """Update a course for the current user."""
    service = CourseService(db)
    try:
        course = await service.update_course(course_id, user_id, data)
        if not course:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Course not found",
            )
        return CourseResponse.model_validate(course)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(e),
        )


@router.delete(
    "/{course_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a course",
    description="Delete a course from the user's learning list.",
)
async def delete_course(
    course_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user_id: uuid.UUID = Depends(get_current_user_id),
) -> None:
    """Delete a course for the current user."""
    service = CourseService(db)
    deleted = await service.delete_course(course_id, user_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Course not found",
        )


@router.post(
    "/{course_id}/sessions",
    response_model=LearningSessionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Log a learning session",
    description="Log a learning session and update course progress. Requirement 25.2",
)
async def log_learning_session(
    course_id: uuid.UUID,
    data: LearningSessionCreate,
    db: AsyncSession = Depends(get_db),
    user_id: uuid.UUID = Depends(get_current_user_id),
) -> LearningSessionResponse:
    """Log a learning session for a course."""
    service = CourseService(db)
    try:
        session, _ = await service.log_learning_session(course_id, user_id, data)
        return LearningSessionResponse.model_validate(session)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )


@router.put(
    "/{course_id}/progress",
    response_model=CourseResponse,
    summary="Update course progress",
    description="Update course completion percentage directly. Requirement 25.2",
)
async def update_course_progress(
    course_id: uuid.UUID,
    data: CourseProgressUpdate,
    db: AsyncSession = Depends(get_db),
    user_id: uuid.UUID = Depends(get_current_user_id),
) -> CourseResponse:
    """Update course progress directly."""
    service = CourseService(db)
    course = await service.update_progress(course_id, user_id, data)
    if not course:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Course not found",
        )
    return CourseResponse.model_validate(course)


@router.post(
    "/{course_id}/complete",
    response_model=CourseResponse,
    summary="Mark course as complete",
    description="Mark a course as complete. Requirement 25.4",
)
async def mark_course_complete(
    course_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user_id: uuid.UUID = Depends(get_current_user_id),
) -> CourseResponse:
    """Mark a course as complete."""
    service = CourseService(db)
    course = await service.mark_course_complete(course_id, user_id)
    if not course:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Course not found",
        )
    return CourseResponse.model_validate(course)
