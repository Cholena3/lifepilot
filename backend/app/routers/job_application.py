"""API router for job application tracking.

Validates: Requirements 27.1, 27.2, 27.3, 27.4, 27.5, 27.6
"""

import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.job_application import ApplicationSource, ApplicationStatus
from app.schemas.job_application import (
    ApplicationStatisticsResponse,
    FollowUpReminderCreate,
    FollowUpReminderResponse,
    JobApplicationCreate,
    JobApplicationResponse,
    JobApplicationUpdate,
    JobApplicationWithHistoryResponse,
    KanbanBoardResponse,
    PaginatedJobApplicationResponse,
    StaleApplicationResponse,
    StatusUpdateRequest,
)
from app.services.job_application import JobApplicationService

router = APIRouter(prefix="/job-applications", tags=["career"])


def get_current_user_id() -> uuid.UUID:
    """Get current user ID from auth context.
    
    TODO: Replace with actual auth dependency when auth is integrated.
    """
    return uuid.UUID("00000000-0000-0000-0000-000000000001")


@router.post(
    "",
    response_model=JobApplicationResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Add a new job application",
    description="Add a new job application to track. Requirement 27.1",
)
async def create_application(
    data: JobApplicationCreate,
    db: AsyncSession = Depends(get_db),
    user_id: uuid.UUID = Depends(get_current_user_id),
) -> JobApplicationResponse:
    """Create a new job application for the current user."""
    service = JobApplicationService(db)
    application = await service.add_application(user_id, data)
    return JobApplicationResponse.model_validate(application)


@router.get(
    "",
    response_model=PaginatedJobApplicationResponse,
    summary="List job applications",
    description="Get a paginated list of user's job applications with optional filtering.",
)
async def list_applications(
    status: Optional[ApplicationStatus] = Query(None, description="Filter by status"),
    source: Optional[ApplicationSource] = Query(None, description="Filter by source"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    db: AsyncSession = Depends(get_db),
    user_id: uuid.UUID = Depends(get_current_user_id),
) -> PaginatedJobApplicationResponse:
    """Get paginated list of job applications for the current user."""
    service = JobApplicationService(db)
    return await service.get_applications(
        user_id=user_id,
        status=status,
        source=source,
        page=page,
        page_size=page_size,
    )


@router.get(
    "/kanban",
    response_model=KanbanBoardResponse,
    summary="Get kanban board view",
    description="Get job applications organized as a kanban board by status. Requirement 27.4",
)
async def get_kanban_board(
    db: AsyncSession = Depends(get_db),
    user_id: uuid.UUID = Depends(get_current_user_id),
) -> KanbanBoardResponse:
    """Get kanban board view of job applications."""
    service = JobApplicationService(db)
    return await service.get_kanban_board(user_id)


@router.get(
    "/statistics",
    response_model=ApplicationStatisticsResponse,
    summary="Get application statistics",
    description="Get job application statistics including response rate and time to response. Requirement 27.6",
)
async def get_statistics(
    db: AsyncSession = Depends(get_db),
    user_id: uuid.UUID = Depends(get_current_user_id),
) -> ApplicationStatisticsResponse:
    """Get application statistics for the current user."""
    service = JobApplicationService(db)
    return await service.get_statistics(user_id)


@router.get(
    "/stale",
    response_model=list[StaleApplicationResponse],
    summary="Get stale applications",
    description="Get applications with no status update in the specified number of days. Requirement 27.5",
)
async def get_stale_applications(
    days: int = Query(14, ge=1, le=365, description="Number of days without update"),
    db: AsyncSession = Depends(get_db),
    user_id: uuid.UUID = Depends(get_current_user_id),
) -> list[StaleApplicationResponse]:
    """Get stale applications needing follow-up."""
    service = JobApplicationService(db)
    return await service.get_stale_applications(user_id, days)


@router.post(
    "/stale/remind",
    summary="Send stale application reminders",
    description="Send reminders for applications with no update. Requirement 27.5",
)
async def send_stale_reminders(
    days: int = Query(14, ge=1, le=365, description="Number of days without update"),
    db: AsyncSession = Depends(get_db),
    user_id: uuid.UUID = Depends(get_current_user_id),
) -> dict:
    """Send reminders for stale applications."""
    service = JobApplicationService(db)
    count = await service.send_stale_application_reminders(user_id, days)
    return {"reminders_sent": count}


@router.post(
    "/reminders/send",
    summary="Send pending follow-up reminders",
    description="Send all pending follow-up reminders. Requirement 27.5",
)
async def send_follow_up_reminders(
    db: AsyncSession = Depends(get_db),
    user_id: uuid.UUID = Depends(get_current_user_id),
) -> dict:
    """Send pending follow-up reminders."""
    service = JobApplicationService(db)
    count = await service.send_follow_up_reminders(user_id)
    return {"reminders_sent": count}


@router.get(
    "/{application_id}",
    response_model=JobApplicationWithHistoryResponse,
    summary="Get application details",
    description="Get a job application with its status history and reminders.",
)
async def get_application(
    application_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user_id: uuid.UUID = Depends(get_current_user_id),
) -> JobApplicationWithHistoryResponse:
    """Get a job application by ID with status history."""
    service = JobApplicationService(db)
    application = await service.get_application_with_history(application_id, user_id)
    if not application:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job application not found",
        )
    return application


@router.put(
    "/{application_id}",
    response_model=JobApplicationResponse,
    summary="Update a job application",
    description="Update a job application's details.",
)
async def update_application(
    application_id: uuid.UUID,
    data: JobApplicationUpdate,
    db: AsyncSession = Depends(get_db),
    user_id: uuid.UUID = Depends(get_current_user_id),
) -> JobApplicationResponse:
    """Update a job application for the current user."""
    service = JobApplicationService(db)
    application = await service.update_application(application_id, user_id, data)
    if not application:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job application not found",
        )
    return JobApplicationResponse.model_validate(application)


@router.put(
    "/{application_id}/status",
    response_model=JobApplicationResponse,
    summary="Update application status",
    description="Update a job application's status and record the change. Requirements 27.2, 27.3",
)
async def update_application_status(
    application_id: uuid.UUID,
    data: StatusUpdateRequest,
    db: AsyncSession = Depends(get_db),
    user_id: uuid.UUID = Depends(get_current_user_id),
) -> JobApplicationResponse:
    """Update application status and record the change."""
    service = JobApplicationService(db)
    application = await service.update_status(application_id, user_id, data)
    if not application:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job application not found",
        )
    return JobApplicationResponse.model_validate(application)


@router.delete(
    "/{application_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a job application",
    description="Delete a job application from tracking.",
)
async def delete_application(
    application_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user_id: uuid.UUID = Depends(get_current_user_id),
) -> None:
    """Delete a job application for the current user."""
    service = JobApplicationService(db)
    deleted = await service.delete_application(application_id, user_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job application not found",
        )


@router.post(
    "/{application_id}/reminders",
    response_model=FollowUpReminderResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Add a follow-up reminder",
    description="Add a follow-up reminder for a job application. Requirement 27.5",
)
async def add_follow_up_reminder(
    application_id: uuid.UUID,
    data: FollowUpReminderCreate,
    db: AsyncSession = Depends(get_db),
    user_id: uuid.UUID = Depends(get_current_user_id),
) -> FollowUpReminderResponse:
    """Add a follow-up reminder for a job application."""
    service = JobApplicationService(db)
    reminder = await service.add_follow_up_reminder(application_id, user_id, data)
    if not reminder:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job application not found",
        )
    return FollowUpReminderResponse.model_validate(reminder)
