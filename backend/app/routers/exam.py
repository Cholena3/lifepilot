"""API router for exam feed and discovery.

Implements Requirements 3.1-3.8 for exam feed, filtering, and tracking.
Implements Requirements 4.1-4.5 for exam calendar integration.
"""

import uuid
from decimal import Decimal
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.exceptions import AuthenticationError, NotFoundError, ServiceError
from app.models.exam import ApplicationStatus, ExamType
from app.schemas.calendar import (
    CalendarEventCreate,
    CalendarEventResponse,
    CalendarSyncResponse,
    GoogleCalendarAuthURL,
    GoogleCalendarCallback,
    GoogleCalendarStatus,
    GoogleCalendarTokenResponse,
)
from app.schemas.exam import (
    ExamApplicationCreate,
    ExamApplicationResponse,
    ExamApplicationUpdate,
    ExamBookmarkCreate,
    ExamBookmarkResponse,
    ExamCreate,
    ExamDetailResponse,
    ExamFeedGroupedResponse,
    ExamFeedResponse,
    ExamFilters,
    ExamResponse,
    ExamUpdate,
)
from app.services.exam import ExamService
from app.services.google_calendar import GoogleCalendarService

router = APIRouter(prefix="/exams", tags=["exams"])


def get_current_user_id() -> uuid.UUID:
    """Get current user ID from auth context.
    
    TODO: Replace with actual auth dependency when auth is integrated.
    """
    return uuid.UUID("00000000-0000-0000-0000-000000000001")


# ============================================================================
# Exam Feed Endpoints
# ============================================================================

@router.get(
    "/feed",
    response_model=ExamFeedResponse,
    summary="Get exam feed",
    description="""
    Get personalized exam feed with eligibility filtering.
    
    Requirement 3.1: Filter by degree, branch, graduation year
    Requirement 3.2: Apply CGPA filter
    Requirement 3.3: Apply backlog filter
    Requirement 3.4: Filter by exam type
    """,
)
async def get_exam_feed(
    exam_type: Optional[ExamType] = Query(None, description="Filter by exam type"),
    degree: Optional[str] = Query(None, description="User's degree for eligibility filtering"),
    branch: Optional[str] = Query(None, description="User's branch for eligibility filtering"),
    graduation_year: Optional[int] = Query(None, description="User's graduation year"),
    cgpa: Optional[Decimal] = Query(None, ge=0, le=10, description="User's CGPA for filtering"),
    backlogs: Optional[int] = Query(None, ge=0, description="User's backlog count"),
    search: Optional[str] = Query(None, description="Search in name and organization"),
    upcoming_only: bool = Query(True, description="Show only exams with future deadlines"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    db: AsyncSession = Depends(get_db),
    user_id: uuid.UUID = Depends(get_current_user_id),
) -> ExamFeedResponse:
    """Get personalized exam feed with eligibility filtering."""
    service = ExamService(db)
    filters = ExamFilters(
        exam_type=exam_type,
        degree=degree,
        branch=branch,
        graduation_year=graduation_year,
        min_cgpa=cgpa,
        backlogs=backlogs,
        search=search,
        upcoming_only=upcoming_only,
    )
    return await service.get_exam_feed(user_id, filters, page, page_size)


@router.get(
    "/feed/grouped",
    response_model=ExamFeedGroupedResponse,
    summary="Get exam feed grouped by type",
    description="""
    Get exams grouped by type with eligibility filtering.
    
    Requirement 3.4: Categorize exams into Campus Placements, Off-campus, 
    Internships, Higher Education, Government, and Scholarships
    """,
)
async def get_exam_feed_grouped(
    degree: Optional[str] = Query(None, description="User's degree for eligibility filtering"),
    branch: Optional[str] = Query(None, description="User's branch for eligibility filtering"),
    graduation_year: Optional[int] = Query(None, description="User's graduation year"),
    cgpa: Optional[Decimal] = Query(None, ge=0, le=10, description="User's CGPA for filtering"),
    backlogs: Optional[int] = Query(None, ge=0, description="User's backlog count"),
    db: AsyncSession = Depends(get_db),
    user_id: uuid.UUID = Depends(get_current_user_id),
) -> ExamFeedGroupedResponse:
    """Get exams grouped by type with eligibility filtering."""
    service = ExamService(db)
    return await service.get_exams_grouped_by_type(
        user_id=user_id,
        degree=degree,
        branch=branch,
        graduation_year=graduation_year,
        cgpa=cgpa,
        backlogs=backlogs,
    )


# ============================================================================
# Exam Detail Endpoints
# ============================================================================

@router.get(
    "/{exam_id}",
    response_model=ExamDetailResponse,
    summary="Get exam details",
    description="""
    Get detailed exam information including syllabus and resources.
    
    Requirement 3.8: Return syllabus, cutoffs, previous papers, and resource links
    """,
)
async def get_exam_details(
    exam_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user_id: uuid.UUID = Depends(get_current_user_id),
) -> ExamDetailResponse:
    """Get detailed exam information."""
    service = ExamService(db)
    exam = await service.get_exam_details(exam_id, user_id)
    if not exam:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Exam not found",
        )
    return exam


# ============================================================================
# Exam CRUD Endpoints (Admin)
# ============================================================================

@router.post(
    "",
    response_model=ExamResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create an exam",
    description="Create a new exam (admin/scraper use).",
)
async def create_exam(
    data: ExamCreate,
    db: AsyncSession = Depends(get_db),
) -> ExamResponse:
    """Create a new exam."""
    service = ExamService(db)
    exam = await service.create_exam(data)
    return ExamResponse.model_validate(exam)


@router.put(
    "/{exam_id}",
    response_model=ExamResponse,
    summary="Update an exam",
    description="Update an existing exam (admin use).",
)
async def update_exam(
    exam_id: uuid.UUID,
    data: ExamUpdate,
    db: AsyncSession = Depends(get_db),
) -> ExamResponse:
    """Update an exam."""
    service = ExamService(db)
    exam = await service.update_exam(exam_id, data)
    if not exam:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Exam not found",
        )
    return ExamResponse.model_validate(exam)


@router.delete(
    "/{exam_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete an exam",
    description="Delete an exam (admin use).",
)
async def delete_exam(
    exam_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> None:
    """Delete an exam."""
    service = ExamService(db)
    deleted = await service.delete_exam(exam_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Exam not found",
        )


# ============================================================================
# Bookmark Endpoints
# ============================================================================

@router.post(
    "/bookmarks",
    response_model=ExamBookmarkResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Bookmark an exam",
    description="""
    Add an exam to user's saved exams list.
    
    Requirement 3.5: Add exam to user's saved exams list
    """,
)
async def bookmark_exam(
    data: ExamBookmarkCreate,
    db: AsyncSession = Depends(get_db),
    user_id: uuid.UUID = Depends(get_current_user_id),
) -> ExamBookmarkResponse:
    """Bookmark an exam."""
    service = ExamService(db)
    try:
        bookmark = await service.bookmark_exam(user_id, data.exam_id)
        return ExamBookmarkResponse(
            id=bookmark.id,
            user_id=bookmark.user_id,
            exam_id=bookmark.exam_id,
            created_at=bookmark.created_at,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.get(
    "/bookmarks",
    summary="Get bookmarked exams",
    description="Get user's bookmarked exams.",
)
async def get_bookmarks(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    db: AsyncSession = Depends(get_db),
    user_id: uuid.UUID = Depends(get_current_user_id),
) -> dict:
    """Get user's bookmarked exams."""
    service = ExamService(db)
    bookmarks, total = await service.get_user_bookmarks(user_id, page, page_size)
    total_pages = (total + page_size - 1) // page_size if page_size > 0 else 0
    return {
        "items": bookmarks,
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": total_pages,
    }


@router.delete(
    "/bookmarks/{exam_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Remove bookmark",
    description="Remove an exam from user's saved exams list.",
)
async def remove_bookmark(
    exam_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user_id: uuid.UUID = Depends(get_current_user_id),
) -> None:
    """Remove an exam bookmark."""
    service = ExamService(db)
    removed = await service.remove_bookmark(user_id, exam_id)
    if not removed:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Bookmark not found",
        )


# ============================================================================
# Application Endpoints
# ============================================================================

@router.post(
    "/applications",
    response_model=ExamApplicationResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Mark exam as applied",
    description="""
    Record that user has applied to an exam.
    
    Requirement 3.6: Record application date and update status
    """,
)
async def mark_applied(
    data: ExamApplicationCreate,
    db: AsyncSession = Depends(get_db),
    user_id: uuid.UUID = Depends(get_current_user_id),
) -> ExamApplicationResponse:
    """Mark an exam as applied."""
    service = ExamService(db)
    try:
        application = await service.mark_applied(user_id, data)
        return ExamApplicationResponse(
            id=application.id,
            user_id=application.user_id,
            exam_id=application.exam_id,
            status=application.status,
            applied_date=application.applied_date,
            notes=application.notes,
            created_at=application.created_at,
            updated_at=application.updated_at,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.get(
    "/applications",
    summary="Get exam applications",
    description="Get user's exam applications.",
)
async def get_applications(
    status_filter: Optional[ApplicationStatus] = Query(None, alias="status", description="Filter by status"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    db: AsyncSession = Depends(get_db),
    user_id: uuid.UUID = Depends(get_current_user_id),
) -> dict:
    """Get user's exam applications."""
    service = ExamService(db)
    applications, total = await service.get_user_applications(
        user_id, status_filter, page, page_size
    )
    total_pages = (total + page_size - 1) // page_size if page_size > 0 else 0
    return {
        "items": applications,
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": total_pages,
    }


@router.put(
    "/applications/{application_id}",
    response_model=ExamApplicationResponse,
    summary="Update application",
    description="Update an exam application status or notes.",
)
async def update_application(
    application_id: uuid.UUID,
    data: ExamApplicationUpdate,
    db: AsyncSession = Depends(get_db),
    user_id: uuid.UUID = Depends(get_current_user_id),
) -> ExamApplicationResponse:
    """Update an exam application."""
    service = ExamService(db)
    application = await service.update_application(user_id, application_id, data)
    if not application:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Application not found",
        )
    return ExamApplicationResponse(
        id=application.id,
        user_id=application.user_id,
        exam_id=application.exam_id,
        status=application.status,
        applied_date=application.applied_date,
        notes=application.notes,
        created_at=application.created_at,
        updated_at=application.updated_at,
    )


@router.delete(
    "/applications/{application_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete application",
    description="Delete an exam application.",
)
async def delete_application(
    application_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user_id: uuid.UUID = Depends(get_current_user_id),
) -> None:
    """Delete an exam application."""
    service = ExamService(db)
    deleted = await service.delete_application(user_id, application_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Application not found",
        )


# ============================================================================
# Google Calendar Integration Endpoints (Requirements 4.1-4.5)
# ============================================================================

@router.get(
    "/calendar/auth",
    response_model=GoogleCalendarAuthURL,
    summary="Get Google Calendar authorization URL",
    description="""
    Get the Google OAuth authorization URL to connect Google Calendar.
    
    Requirement 4.1: Obtain OAuth tokens
    """,
)
async def get_calendar_auth_url(
    db: AsyncSession = Depends(get_db),
    user_id: uuid.UUID = Depends(get_current_user_id),
) -> GoogleCalendarAuthURL:
    """Get Google Calendar OAuth authorization URL."""
    service = GoogleCalendarService(db)
    return service.get_auth_url()


@router.post(
    "/calendar/callback",
    response_model=GoogleCalendarTokenResponse,
    summary="Handle Google Calendar OAuth callback",
    description="""
    Handle the OAuth callback from Google and store tokens.
    
    Requirement 4.1: Obtain OAuth tokens and store them securely
    """,
)
async def calendar_oauth_callback(
    data: GoogleCalendarCallback,
    db: AsyncSession = Depends(get_db),
    user_id: uuid.UUID = Depends(get_current_user_id),
) -> GoogleCalendarTokenResponse:
    """Handle Google Calendar OAuth callback."""
    service = GoogleCalendarService(db)
    try:
        return await service.handle_callback(user_id, data.code)
    except AuthenticationError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e),
        )


@router.get(
    "/calendar/status",
    response_model=GoogleCalendarStatus,
    summary="Get Google Calendar connection status",
    description="Check if Google Calendar is connected for the current user.",
)
async def get_calendar_status(
    db: AsyncSession = Depends(get_db),
    user_id: uuid.UUID = Depends(get_current_user_id),
) -> GoogleCalendarStatus:
    """Get Google Calendar connection status."""
    service = GoogleCalendarService(db)
    return await service.get_connection_status(user_id)


@router.delete(
    "/calendar/disconnect",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Disconnect Google Calendar",
    description="Disconnect Google Calendar and remove all synced events.",
)
async def disconnect_calendar(
    db: AsyncSession = Depends(get_db),
    user_id: uuid.UUID = Depends(get_current_user_id),
) -> None:
    """Disconnect Google Calendar."""
    service = GoogleCalendarService(db)
    disconnected = await service.disconnect(user_id)
    if not disconnected:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Google Calendar not connected",
        )


@router.post(
    "/calendar/sync/{exam_id}",
    response_model=CalendarEventResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Sync exam to Google Calendar",
    description="""
    Create a Google Calendar event for an exam.
    
    Requirement 4.2: Create a Google Calendar event with exam details
    """,
)
async def sync_exam_to_calendar(
    exam_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user_id: uuid.UUID = Depends(get_current_user_id),
) -> CalendarEventResponse:
    """Sync an exam to Google Calendar."""
    service = GoogleCalendarService(db)
    try:
        return await service.create_event(user_id, exam_id)
    except NotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except AuthenticationError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e),
        )
    except ServiceError as e:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(e),
        )


@router.put(
    "/calendar/sync/{exam_id}",
    response_model=CalendarEventResponse,
    summary="Update synced exam in Google Calendar",
    description="""
    Update the Google Calendar event for an exam.
    
    Requirement 4.3: Update the corresponding Google Calendar event
    """,
)
async def update_calendar_event(
    exam_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user_id: uuid.UUID = Depends(get_current_user_id),
) -> CalendarEventResponse:
    """Update a synced exam in Google Calendar."""
    service = GoogleCalendarService(db)
    try:
        return await service.update_event(user_id, exam_id)
    except NotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except AuthenticationError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e),
        )
    except ServiceError as e:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(e),
        )


@router.delete(
    "/calendar/sync/{exam_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Remove exam from Google Calendar",
    description="""
    Delete the Google Calendar event for an exam.
    
    Requirement 4.4: Delete the Google Calendar event
    """,
)
async def remove_from_calendar(
    exam_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user_id: uuid.UUID = Depends(get_current_user_id),
) -> None:
    """Remove an exam from Google Calendar."""
    service = GoogleCalendarService(db)
    try:
        await service.delete_event(user_id, exam_id)
    except NotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except AuthenticationError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e),
        )
    except ServiceError as e:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(e),
        )


@router.get(
    "/calendar/sync/{exam_id}",
    response_model=CalendarSyncResponse,
    summary="Get calendar sync status for an exam",
    description="Check if an exam is synced to Google Calendar.",
)
async def get_calendar_sync_status(
    exam_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user_id: uuid.UUID = Depends(get_current_user_id),
) -> CalendarSyncResponse:
    """Get calendar sync status for an exam."""
    service = GoogleCalendarService(db)
    return await service.get_sync_status(user_id, exam_id)
