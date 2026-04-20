"""Medicine router for medicine tracking and dose management endpoints.

Validates: Requirements 15.1, 15.2, 15.3, 15.4, 15.5, 15.6
"""

from datetime import datetime, date
from typing import Annotated, List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import CurrentUser
from app.schemas.medicine import (
    MedicineCreate,
    MedicineUpdate,
    MedicineResponse,
    DoseLogCreate,
    DoseResponse,
    AdherenceStats,
    OverallAdherenceStats,
    MedicineReminderResponse,
    RefillAlertResponse,
    PaginatedMedicineResponse,
    PaginatedDoseResponse,
    MedicineFrequencyEnum,
    DoseStatusEnum,
)
from app.services.medicine import MedicineService

router = APIRouter()


# ============================================================================
# Medicine CRUD Endpoints
# ============================================================================

@router.post(
    "",
    response_model=MedicineResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a medicine",
    description="Add a new medicine to track with optional reminder times.",
    responses={
        201: {"description": "Medicine created successfully"},
        401: {"description": "Not authenticated"},
        422: {"description": "Validation error"},
    },
)
async def create_medicine(
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
    data: MedicineCreate,
) -> MedicineResponse:
    """Create a new medicine.
    
    Validates: Requirements 15.1
    
    Args:
        current_user: Authenticated user (injected)
        db: Database session (injected)
        data: Medicine creation data
        
    Returns:
        Created medicine
    """
    service = MedicineService(db)
    return await service.create_medicine(current_user.id, data)


@router.get(
    "",
    response_model=PaginatedMedicineResponse,
    status_code=status.HTTP_200_OK,
    summary="List medicines",
    description="List all medicines for the authenticated user.",
    responses={
        200: {"description": "Medicines returned successfully"},
        401: {"description": "Not authenticated"},
    },
)
async def list_medicines(
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
    is_active: Annotated[
        Optional[bool],
        Query(description="Filter by active/inactive status")
    ] = None,
    page: Annotated[int, Query(ge=1, description="Page number (1-indexed)")] = 1,
    page_size: Annotated[int, Query(ge=1, le=100, description="Number of results per page")] = 20,
) -> PaginatedMedicineResponse:
    """List all medicines.
    
    Args:
        current_user: Authenticated user (injected)
        db: Database session (injected)
        is_active: Optional filter for active/inactive medicines
        page: Page number (1-indexed)
        page_size: Number of results per page
        
    Returns:
        Paginated list of medicines
    """
    service = MedicineService(db)
    return await service.list_medicines(current_user.id, is_active, page, page_size)


@router.get(
    "/frequencies",
    response_model=List[str],
    status_code=status.HTTP_200_OK,
    summary="List medicine frequencies",
    description="Get the list of valid medicine frequency options.",
    responses={
        200: {"description": "Frequencies returned successfully"},
    },
)
async def list_frequencies() -> List[str]:
    """List all valid medicine frequency options.
    
    Validates: Requirements 15.1
    
    Returns:
        List of valid frequency values
    """
    return MedicineFrequencyEnum.ALL


@router.get(
    "/reminders",
    response_model=List[MedicineReminderResponse],
    status_code=status.HTTP_200_OK,
    summary="Get upcoming reminders",
    description="Get upcoming medicine reminders for the next 24 hours.",
    responses={
        200: {"description": "Reminders returned successfully"},
        401: {"description": "Not authenticated"},
    },
)
async def get_upcoming_reminders(
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
    hours_ahead: Annotated[
        int,
        Query(ge=1, le=168, description="Hours ahead to look (max 7 days)")
    ] = 24,
) -> List[MedicineReminderResponse]:
    """Get upcoming medicine reminders.
    
    Validates: Requirements 15.2
    
    Args:
        current_user: Authenticated user (injected)
        db: Database session (injected)
        hours_ahead: How many hours ahead to look
        
    Returns:
        List of upcoming reminders
    """
    service = MedicineService(db)
    return await service.get_upcoming_reminders(current_user.id, hours_ahead)


@router.get(
    "/refill-alerts",
    response_model=List[RefillAlertResponse],
    status_code=status.HTTP_200_OK,
    summary="Get refill alerts",
    description="Get medicines that need refill (remaining quantity at or below threshold).",
    responses={
        200: {"description": "Refill alerts returned successfully"},
        401: {"description": "Not authenticated"},
    },
)
async def get_refill_alerts(
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> List[RefillAlertResponse]:
    """Get medicines that need refill.
    
    Validates: Requirements 15.5
    
    Args:
        current_user: Authenticated user (injected)
        db: Database session (injected)
        
    Returns:
        List of refill alerts
    """
    service = MedicineService(db)
    return await service.get_refill_alerts(current_user.id)


@router.get(
    "/adherence",
    response_model=OverallAdherenceStats,
    status_code=status.HTTP_200_OK,
    summary="Get overall adherence statistics",
    description="Get adherence statistics across all medicines.",
    responses={
        200: {"description": "Statistics returned successfully"},
        401: {"description": "Not authenticated"},
    },
)
async def get_overall_adherence(
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> OverallAdherenceStats:
    """Get overall adherence statistics.
    
    Validates: Requirements 15.6
    
    Args:
        current_user: Authenticated user (injected)
        db: Database session (injected)
        
    Returns:
        Overall adherence statistics
    """
    service = MedicineService(db)
    return await service.get_overall_adherence_stats(current_user.id)


@router.get(
    "/{medicine_id}",
    response_model=MedicineResponse,
    status_code=status.HTTP_200_OK,
    summary="Get a medicine",
    description="Get a specific medicine by ID.",
    responses={
        200: {"description": "Medicine returned successfully"},
        401: {"description": "Not authenticated"},
        404: {"description": "Medicine not found"},
    },
)
async def get_medicine(
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
    medicine_id: UUID,
) -> MedicineResponse:
    """Get a medicine by ID.
    
    Args:
        current_user: Authenticated user (injected)
        db: Database session (injected)
        medicine_id: Medicine's UUID
        
    Returns:
        Medicine details
        
    Raises:
        HTTPException 404: Medicine not found
    """
    service = MedicineService(db)
    result = await service.get_medicine(current_user.id, medicine_id)
    if result is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Medicine not found",
        )
    return result


@router.patch(
    "/{medicine_id}",
    response_model=MedicineResponse,
    status_code=status.HTTP_200_OK,
    summary="Update a medicine",
    description="Update a specific medicine by ID.",
    responses={
        200: {"description": "Medicine updated successfully"},
        401: {"description": "Not authenticated"},
        404: {"description": "Medicine not found"},
        422: {"description": "Validation error"},
    },
)
async def update_medicine(
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
    medicine_id: UUID,
    data: MedicineUpdate,
) -> MedicineResponse:
    """Update a medicine.
    
    Args:
        current_user: Authenticated user (injected)
        db: Database session (injected)
        medicine_id: Medicine's UUID
        data: Medicine update data
        
    Returns:
        Updated medicine
        
    Raises:
        HTTPException 404: Medicine not found
    """
    service = MedicineService(db)
    result = await service.update_medicine(current_user.id, medicine_id, data)
    if result is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Medicine not found",
        )
    return result


@router.delete(
    "/{medicine_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a medicine",
    description="Delete a specific medicine by ID.",
    responses={
        204: {"description": "Medicine deleted successfully"},
        401: {"description": "Not authenticated"},
        404: {"description": "Medicine not found"},
    },
)
async def delete_medicine(
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
    medicine_id: UUID,
) -> None:
    """Delete a medicine.
    
    Args:
        current_user: Authenticated user (injected)
        db: Database session (injected)
        medicine_id: Medicine's UUID
        
    Raises:
        HTTPException 404: Medicine not found
    """
    service = MedicineService(db)
    deleted = await service.delete_medicine(current_user.id, medicine_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Medicine not found",
        )


# ============================================================================
# Adherence Statistics Endpoints
# ============================================================================

@router.get(
    "/{medicine_id}/adherence",
    response_model=AdherenceStats,
    status_code=status.HTTP_200_OK,
    summary="Get medicine adherence statistics",
    description="Get adherence statistics for a specific medicine.",
    responses={
        200: {"description": "Statistics returned successfully"},
        401: {"description": "Not authenticated"},
        404: {"description": "Medicine not found"},
    },
)
async def get_medicine_adherence(
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
    medicine_id: UUID,
    start_date: Annotated[
        Optional[date],
        Query(description="Start of statistics period")
    ] = None,
    end_date: Annotated[
        Optional[date],
        Query(description="End of statistics period")
    ] = None,
) -> AdherenceStats:
    """Get adherence statistics for a medicine.
    
    Validates: Requirements 15.6
    
    Args:
        current_user: Authenticated user (injected)
        db: Database session (injected)
        medicine_id: Medicine's UUID
        start_date: Optional start of period
        end_date: Optional end of period
        
    Returns:
        Adherence statistics
        
    Raises:
        HTTPException 404: Medicine not found
    """
    service = MedicineService(db)
    result = await service.get_adherence_stats(
        current_user.id, medicine_id, start_date, end_date
    )
    if result is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Medicine not found",
        )
    return result


# ============================================================================
# Dose Endpoints
# ============================================================================

@router.get(
    "/{medicine_id}/doses",
    response_model=PaginatedDoseResponse,
    status_code=status.HTTP_200_OK,
    summary="List doses for a medicine",
    description="List all doses for a specific medicine with optional filtering.",
    responses={
        200: {"description": "Doses returned successfully"},
        401: {"description": "Not authenticated"},
        404: {"description": "Medicine not found"},
    },
)
async def list_doses(
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
    medicine_id: UUID,
    status_filter: Annotated[
        Optional[str],
        Query(alias="status", description="Filter by dose status")
    ] = None,
    start_date: Annotated[
        Optional[datetime],
        Query(description="Filter doses from this datetime")
    ] = None,
    end_date: Annotated[
        Optional[datetime],
        Query(description="Filter doses until this datetime")
    ] = None,
    page: Annotated[int, Query(ge=1, description="Page number (1-indexed)")] = 1,
    page_size: Annotated[int, Query(ge=1, le=100, description="Number of results per page")] = 20,
) -> PaginatedDoseResponse:
    """List doses for a medicine.
    
    Args:
        current_user: Authenticated user (injected)
        db: Database session (injected)
        medicine_id: Medicine's UUID
        status_filter: Optional status filter
        start_date: Optional start date filter
        end_date: Optional end date filter
        page: Page number (1-indexed)
        page_size: Number of results per page
        
    Returns:
        Paginated list of doses
        
    Raises:
        HTTPException 404: Medicine not found
        HTTPException 422: Invalid status
    """
    # Validate status if provided
    if status_filter is not None and status_filter not in DoseStatusEnum.ALL:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Status must be one of: {', '.join(DoseStatusEnum.ALL)}",
        )
    
    service = MedicineService(db)
    result = await service.get_doses(
        current_user.id,
        medicine_id,
        status=status_filter,
        start_date=start_date,
        end_date=end_date,
        page=page,
        page_size=page_size,
    )
    if result is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Medicine not found",
        )
    return result


@router.post(
    "/{medicine_id}/doses/{dose_id}/log",
    response_model=DoseResponse,
    status_code=status.HTTP_200_OK,
    summary="Log a dose",
    description="Mark a dose as taken or missed.",
    responses={
        200: {"description": "Dose logged successfully"},
        401: {"description": "Not authenticated"},
        404: {"description": "Medicine or dose not found"},
    },
)
async def log_dose(
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
    medicine_id: UUID,
    dose_id: UUID,
    data: DoseLogCreate,
) -> DoseResponse:
    """Log a dose as taken or missed.
    
    Validates: Requirements 15.3, 15.4
    
    Args:
        current_user: Authenticated user (injected)
        db: Database session (injected)
        medicine_id: Medicine's UUID
        dose_id: Dose's UUID
        data: Dose log data
        
    Returns:
        Updated dose
        
    Raises:
        HTTPException 404: Medicine or dose not found
    """
    service = MedicineService(db)
    result = await service.log_dose(current_user.id, medicine_id, dose_id, data)
    if result is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Medicine or dose not found",
        )
    return result


@router.post(
    "/{medicine_id}/doses/{dose_id}/skip",
    response_model=DoseResponse,
    status_code=status.HTTP_200_OK,
    summary="Skip a dose",
    description="Mark a scheduled dose as skipped.",
    responses={
        200: {"description": "Dose skipped successfully"},
        401: {"description": "Not authenticated"},
        404: {"description": "Medicine or dose not found"},
    },
)
async def skip_dose(
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
    medicine_id: UUID,
    dose_id: UUID,
    notes: Annotated[
        Optional[str],
        Query(description="Optional reason for skipping")
    ] = None,
) -> DoseResponse:
    """Skip a scheduled dose.
    
    Args:
        current_user: Authenticated user (injected)
        db: Database session (injected)
        medicine_id: Medicine's UUID
        dose_id: Dose's UUID
        notes: Optional reason for skipping
        
    Returns:
        Updated dose
        
    Raises:
        HTTPException 404: Medicine or dose not found
    """
    service = MedicineService(db)
    result = await service.skip_dose(current_user.id, medicine_id, dose_id, notes)
    if result is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Medicine or dose not found",
        )
    return result


@router.post(
    "/{medicine_id}/schedule",
    status_code=status.HTTP_200_OK,
    summary="Schedule doses",
    description="Schedule doses for a medicine for the next N days.",
    responses={
        200: {"description": "Doses scheduled successfully"},
        401: {"description": "Not authenticated"},
        404: {"description": "Medicine not found"},
    },
)
async def schedule_doses(
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
    medicine_id: UUID,
    days_ahead: Annotated[
        int,
        Query(ge=1, le=30, description="Number of days to schedule ahead")
    ] = 7,
) -> dict:
    """Schedule doses for a medicine.
    
    Args:
        current_user: Authenticated user (injected)
        db: Database session (injected)
        medicine_id: Medicine's UUID
        days_ahead: Number of days to schedule ahead
        
    Returns:
        Dict with number of doses scheduled
        
    Raises:
        HTTPException 404: Medicine not found
    """
    service = MedicineService(db)
    count = await service.schedule_doses(current_user.id, medicine_id, days_ahead)
    if count is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Medicine not found",
        )
    return {"doses_scheduled": count}
