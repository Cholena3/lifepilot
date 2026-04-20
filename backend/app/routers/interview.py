"""API router for interview preparation.

Validates: Requirements 28.1, 28.2, 28.3, 28.4, 28.5
"""

import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.interview import InterviewType
from app.schemas.interview import (
    InterviewHistoryResponse,
    InterviewNoteCreate,
    InterviewNoteResponse,
    InterviewNoteUpdate,
    InterviewNoteWithQAResponse,
    InterviewStatisticsResponse,
    PaginatedInterviewNoteResponse,
    PerformanceRatingUpdate,
    PreparationReminderCreate,
    PreparationReminderResponse,
    QuestionAnswerCreate,
    QuestionAnswerResponse,
    QuestionAnswerUpdate,
)
from app.services.interview import InterviewService

router = APIRouter(prefix="/interviews", tags=["career"])


def get_current_user_id() -> uuid.UUID:
    """Get current user ID from auth context.
    
    TODO: Replace with actual auth dependency when auth is integrated.
    """
    return uuid.UUID("00000000-0000-0000-0000-000000000001")


@router.post(
    "",
    response_model=InterviewNoteResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Add interview notes",
    description="Add interview notes for a job application. Requirement 28.1",
)
async def create_interview_note(
    data: InterviewNoteCreate,
    db: AsyncSession = Depends(get_db),
    user_id: uuid.UUID = Depends(get_current_user_id),
) -> InterviewNoteResponse:
    """Create interview notes for a job application."""
    service = InterviewService(db)
    note = await service.add_interview_note(user_id, data)
    if not note:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job application not found",
        )
    return InterviewNoteResponse.model_validate(note)


@router.get(
    "",
    response_model=PaginatedInterviewNoteResponse,
    summary="List interview notes",
    description="Get a paginated list of user's interview notes with optional filtering.",
)
async def list_interview_notes(
    interview_type: Optional[InterviewType] = Query(None, description="Filter by type"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    db: AsyncSession = Depends(get_db),
    user_id: uuid.UUID = Depends(get_current_user_id),
) -> PaginatedInterviewNoteResponse:
    """Get paginated list of interview notes for the current user."""
    service = InterviewService(db)
    return await service.get_interview_notes(
        user_id=user_id,
        interview_type=interview_type,
        page=page,
        page_size=page_size,
    )


@router.get(
    "/history",
    response_model=list[InterviewHistoryResponse],
    summary="Get interview history",
    description="Get interview history with outcomes for pattern analysis. Requirement 28.5",
)
async def get_interview_history(
    db: AsyncSession = Depends(get_db),
    user_id: uuid.UUID = Depends(get_current_user_id),
) -> list[InterviewHistoryResponse]:
    """Get interview history with outcomes."""
    service = InterviewService(db)
    return await service.get_interview_history(user_id)


@router.get(
    "/statistics",
    response_model=InterviewStatisticsResponse,
    summary="Get interview statistics",
    description="Get interview statistics for pattern analysis. Requirement 28.5",
)
async def get_interview_statistics(
    db: AsyncSession = Depends(get_db),
    user_id: uuid.UUID = Depends(get_current_user_id),
) -> InterviewStatisticsResponse:
    """Get interview statistics for the current user."""
    service = InterviewService(db)
    return await service.get_interview_statistics(user_id)


@router.get(
    "/upcoming",
    response_model=list[InterviewNoteResponse],
    summary="Get upcoming interviews",
    description="Get interviews scheduled within the next N days.",
)
async def get_upcoming_interviews(
    days: int = Query(7, ge=1, le=30, description="Days ahead to look"),
    db: AsyncSession = Depends(get_db),
    user_id: uuid.UUID = Depends(get_current_user_id),
) -> list[InterviewNoteResponse]:
    """Get upcoming interviews."""
    service = InterviewService(db)
    return await service.get_upcoming_interviews(user_id, days)


@router.post(
    "/reminders/send",
    summary="Send preparation reminders",
    description="Send all pending preparation reminders. Requirement 28.3",
)
async def send_preparation_reminders(
    db: AsyncSession = Depends(get_db),
    user_id: uuid.UUID = Depends(get_current_user_id),
) -> dict:
    """Send pending preparation reminders."""
    service = InterviewService(db)
    count = await service.send_preparation_reminders(user_id)
    return {"reminders_sent": count}


@router.get(
    "/application/{application_id}",
    response_model=list[InterviewNoteResponse],
    summary="Get interview notes for application",
    description="Get all interview notes for a specific job application.",
)
async def get_interview_notes_for_application(
    application_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user_id: uuid.UUID = Depends(get_current_user_id),
) -> list[InterviewNoteResponse]:
    """Get interview notes for a job application."""
    service = InterviewService(db)
    return await service.get_interview_notes_for_application(application_id, user_id)


@router.get(
    "/{note_id}",
    response_model=InterviewNoteWithQAResponse,
    summary="Get interview note details",
    description="Get an interview note with Q&A entries and reminders.",
)
async def get_interview_note(
    note_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user_id: uuid.UUID = Depends(get_current_user_id),
) -> InterviewNoteWithQAResponse:
    """Get an interview note by ID with details."""
    service = InterviewService(db)
    note = await service.get_interview_note_with_details(note_id, user_id)
    if not note:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Interview note not found",
        )
    return note



@router.put(
    "/{note_id}",
    response_model=InterviewNoteResponse,
    summary="Update interview note",
    description="Update an interview note's details.",
)
async def update_interview_note(
    note_id: uuid.UUID,
    data: InterviewNoteUpdate,
    db: AsyncSession = Depends(get_db),
    user_id: uuid.UUID = Depends(get_current_user_id),
) -> InterviewNoteResponse:
    """Update an interview note."""
    service = InterviewService(db)
    note = await service.update_interview_note(note_id, user_id, data)
    if not note:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Interview note not found",
        )
    return InterviewNoteResponse.model_validate(note)


@router.put(
    "/{note_id}/rating",
    response_model=InterviewNoteResponse,
    summary="Update performance rating",
    description="Update interview performance rating. Requirement 28.4",
)
async def update_performance_rating(
    note_id: uuid.UUID,
    data: PerformanceRatingUpdate,
    db: AsyncSession = Depends(get_db),
    user_id: uuid.UUID = Depends(get_current_user_id),
) -> InterviewNoteResponse:
    """Update interview performance rating."""
    service = InterviewService(db)
    note = await service.update_performance_rating(note_id, user_id, data)
    if not note:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Interview note not found",
        )
    return InterviewNoteResponse.model_validate(note)


@router.delete(
    "/{note_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete interview note",
    description="Delete an interview note.",
)
async def delete_interview_note(
    note_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user_id: uuid.UUID = Depends(get_current_user_id),
) -> None:
    """Delete an interview note."""
    service = InterviewService(db)
    deleted = await service.delete_interview_note(note_id, user_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Interview note not found",
        )


@router.post(
    "/{note_id}/reminders",
    response_model=PreparationReminderResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Add preparation reminder",
    description="Add a preparation reminder for an interview. Requirement 28.3",
)
async def add_preparation_reminder(
    note_id: uuid.UUID,
    data: PreparationReminderCreate,
    db: AsyncSession = Depends(get_db),
    user_id: uuid.UUID = Depends(get_current_user_id),
) -> PreparationReminderResponse:
    """Add a preparation reminder for an interview."""
    service = InterviewService(db)
    reminder = await service.add_preparation_reminder(note_id, user_id, data)
    if not reminder:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Interview note not found",
        )
    return PreparationReminderResponse.model_validate(reminder)


# Q&A Endpoints
@router.post(
    "/{note_id}/qa",
    response_model=QuestionAnswerResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Add Q&A entry",
    description="Add a question and answer entry to an interview note. Requirement 28.2",
)
async def add_qa_entry(
    note_id: uuid.UUID,
    data: QuestionAnswerCreate,
    db: AsyncSession = Depends(get_db),
    user_id: uuid.UUID = Depends(get_current_user_id),
) -> QuestionAnswerResponse:
    """Add a Q&A entry to an interview note."""
    service = InterviewService(db)
    qa = await service.add_qa_entry(note_id, user_id, data)
    if not qa:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Interview note not found",
        )
    return QuestionAnswerResponse.model_validate(qa)


@router.get(
    "/{note_id}/qa",
    response_model=list[QuestionAnswerResponse],
    summary="Get Q&A entries",
    description="Get all Q&A entries for an interview note. Requirement 28.2",
)
async def get_qa_entries(
    note_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user_id: uuid.UUID = Depends(get_current_user_id),
) -> list[QuestionAnswerResponse]:
    """Get all Q&A entries for an interview note."""
    service = InterviewService(db)
    return await service.get_qa_entries(note_id, user_id)


@router.put(
    "/qa/{qa_id}",
    response_model=QuestionAnswerResponse,
    summary="Update Q&A entry",
    description="Update a Q&A entry.",
)
async def update_qa_entry(
    qa_id: uuid.UUID,
    data: QuestionAnswerUpdate,
    db: AsyncSession = Depends(get_db),
    user_id: uuid.UUID = Depends(get_current_user_id),
) -> QuestionAnswerResponse:
    """Update a Q&A entry."""
    service = InterviewService(db)
    qa = await service.update_qa_entry(qa_id, user_id, data)
    if not qa:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Q&A entry not found",
        )
    return QuestionAnswerResponse.model_validate(qa)


@router.delete(
    "/qa/{qa_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete Q&A entry",
    description="Delete a Q&A entry.",
)
async def delete_qa_entry(
    qa_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user_id: uuid.UUID = Depends(get_current_user_id),
) -> None:
    """Delete a Q&A entry."""
    service = InterviewService(db)
    deleted = await service.delete_qa_entry(qa_id, user_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Q&A entry not found",
        )
