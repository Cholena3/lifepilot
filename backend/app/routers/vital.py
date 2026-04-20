"""Vital router for vitals tracking endpoints.

Validates: Requirements 16.1, 16.2, 16.3, 16.4, 16.5
"""

from datetime import date
from typing import Annotated, List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import CurrentUser
from app.schemas.vital import (
    VitalCreate,
    VitalUpdate,
    VitalResponse,
    VitalTargetRangeCreate,
    VitalTargetRangeResponse,
    VitalTrendResponse,
    VitalsDashboardResponse,
    VitalExportRequest,
    PaginatedVitalResponse,
    PaginatedVitalTargetRangeResponse,
    VitalTypeEnum,
)
from app.services.vital import VitalService

router = APIRouter()


# ============================================================================
# Vital CRUD Endpoints
# ============================================================================

@router.post(
    "",
    response_model=VitalResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Log a vital reading",
    description="Log a new vital reading (blood pressure, heart rate, weight, etc.).",
    responses={
        201: {"description": "Vital logged successfully"},
        401: {"description": "Not authenticated"},
        422: {"description": "Validation error"},
    },
)
async def create_vital(
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
    data: VitalCreate,
) -> VitalResponse:
    """Log a new vital reading.
    
    Validates: Requirements 16.1
    
    Args:
        current_user: Authenticated user (injected)
        db: Database session (injected)
        data: Vital creation data
        
    Returns:
        Created vital with warning level
    """
    service = VitalService(db)
    try:
        return await service.create_vital(current_user.id, data)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.get(
    "",
    response_model=PaginatedVitalResponse,
    status_code=status.HTTP_200_OK,
    summary="List vitals",
    description="List vital readings with optional filtering.",
    responses={
        200: {"description": "Vitals returned successfully"},
        401: {"description": "Not authenticated"},
    },
)
async def list_vitals(
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
    vital_type: Annotated[
        Optional[str],
        Query(description="Filter by vital type")
    ] = None,
    family_member_id: Annotated[
        Optional[UUID],
        Query(description="Filter by family member (null for self)")
    ] = None,
    start_date: Annotated[
        Optional[date],
        Query(description="Filter readings from this date")
    ] = None,
    end_date: Annotated[
        Optional[date],
        Query(description="Filter readings until this date")
    ] = None,
    page: Annotated[int, Query(ge=1, description="Page number (1-indexed)")] = 1,
    page_size: Annotated[int, Query(ge=1, le=100, description="Number of results per page")] = 20,
) -> PaginatedVitalResponse:
    """List vital readings.
    
    Args:
        current_user: Authenticated user (injected)
        db: Database session (injected)
        vital_type: Optional vital type filter
        family_member_id: Optional family member filter
        start_date: Optional start date filter
        end_date: Optional end date filter
        page: Page number (1-indexed)
        page_size: Number of results per page
        
    Returns:
        Paginated list of vitals
    """
    # Validate vital type if provided
    if vital_type is not None and vital_type not in VitalTypeEnum.ALL:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Vital type must be one of: {', '.join(VitalTypeEnum.ALL)}",
        )
    
    service = VitalService(db)
    return await service.list_vitals(
        current_user.id,
        vital_type=vital_type,
        family_member_id=family_member_id,
        start_date=start_date,
        end_date=end_date,
        page=page,
        page_size=page_size,
    )


@router.get(
    "/types",
    response_model=List[dict],
    status_code=status.HTTP_200_OK,
    summary="List vital types",
    description="Get the list of valid vital types with their default ranges.",
    responses={
        200: {"description": "Vital types returned successfully"},
    },
)
async def list_vital_types(
    db: Annotated[AsyncSession, Depends(get_db)],
) -> List[dict]:
    """List all valid vital types with default ranges.
    
    Validates: Requirements 16.1
    
    Returns:
        List of vital type info
    """
    service = VitalService(db)
    return await service.get_vital_types()


@router.get(
    "/dashboard",
    response_model=VitalsDashboardResponse,
    status_code=status.HTTP_200_OK,
    summary="Get vitals dashboard",
    description="Get vitals dashboard overview with summaries and recent readings.",
    responses={
        200: {"description": "Dashboard returned successfully"},
        401: {"description": "Not authenticated"},
    },
)
async def get_vitals_dashboard(
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
    family_member_id: Annotated[
        Optional[UUID],
        Query(description="Filter by family member (null for self)")
    ] = None,
) -> VitalsDashboardResponse:
    """Get vitals dashboard overview.
    
    Args:
        current_user: Authenticated user (injected)
        db: Database session (injected)
        family_member_id: Optional family member filter
        
    Returns:
        Dashboard with summaries and recent readings
    """
    service = VitalService(db)
    return await service.get_vitals_dashboard(current_user.id, family_member_id)


@router.get(
    "/trends/{vital_type}",
    response_model=VitalTrendResponse,
    status_code=status.HTTP_200_OK,
    summary="Get vital trends",
    description="Get vital trends over a date range with charts data.",
    responses={
        200: {"description": "Trends returned successfully"},
        401: {"description": "Not authenticated"},
        422: {"description": "Invalid vital type"},
    },
)
async def get_vital_trends(
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
    vital_type: str,
    start_date: Annotated[date, Query(description="Start date for trends")],
    end_date: Annotated[date, Query(description="End date for trends")],
    family_member_id: Annotated[
        Optional[UUID],
        Query(description="Filter by family member (null for self)")
    ] = None,
) -> VitalTrendResponse:
    """Get vital trends over a date range.
    
    Validates: Requirements 16.2, 16.3
    
    Args:
        current_user: Authenticated user (injected)
        db: Database session (injected)
        vital_type: Type of vital to get trends for
        start_date: Start of period
        end_date: End of period
        family_member_id: Optional family member filter
        
    Returns:
        Trend data with statistics
    """
    if vital_type not in VitalTypeEnum.ALL:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Vital type must be one of: {', '.join(VitalTypeEnum.ALL)}",
        )
    
    service = VitalService(db)
    return await service.get_vital_trends(
        current_user.id,
        vital_type,
        start_date,
        end_date,
        family_member_id,
    )


@router.post(
    "/export",
    status_code=status.HTTP_200_OK,
    summary="Export vitals report",
    description="Export vitals report as PDF.",
    responses={
        200: {"description": "PDF report generated successfully", "content": {"application/pdf": {}}},
        401: {"description": "Not authenticated"},
        422: {"description": "Validation error"},
    },
)
async def export_vitals_report(
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
    request: VitalExportRequest,
) -> Response:
    """Export vitals report as PDF.
    
    Validates: Requirements 16.5
    
    Args:
        current_user: Authenticated user (injected)
        db: Database session (injected)
        request: Export request parameters
        
    Returns:
        PDF file response
    """
    service = VitalService(db)
    try:
        pdf_bytes = await service.export_vitals_report(current_user.id, request)
        
        # Generate filename
        filename = f"vitals_report_{request.start_date}_{request.end_date}.pdf"
        
        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={
                "Content-Disposition": f'attachment; filename="{filename}"',
            },
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.get(
    "/{vital_id}",
    response_model=VitalResponse,
    status_code=status.HTTP_200_OK,
    summary="Get a vital",
    description="Get a specific vital reading by ID.",
    responses={
        200: {"description": "Vital returned successfully"},
        401: {"description": "Not authenticated"},
        404: {"description": "Vital not found"},
    },
)
async def get_vital(
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
    vital_id: UUID,
) -> VitalResponse:
    """Get a vital by ID.
    
    Args:
        current_user: Authenticated user (injected)
        db: Database session (injected)
        vital_id: Vital's UUID
        
    Returns:
        Vital details with warning level
        
    Raises:
        HTTPException 404: Vital not found
    """
    service = VitalService(db)
    result = await service.get_vital(current_user.id, vital_id)
    if result is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Vital not found",
        )
    return result


@router.patch(
    "/{vital_id}",
    response_model=VitalResponse,
    status_code=status.HTTP_200_OK,
    summary="Update a vital",
    description="Update a specific vital reading by ID.",
    responses={
        200: {"description": "Vital updated successfully"},
        401: {"description": "Not authenticated"},
        404: {"description": "Vital not found"},
        422: {"description": "Validation error"},
    },
)
async def update_vital(
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
    vital_id: UUID,
    data: VitalUpdate,
) -> VitalResponse:
    """Update a vital reading.
    
    Args:
        current_user: Authenticated user (injected)
        db: Database session (injected)
        vital_id: Vital's UUID
        data: Vital update data
        
    Returns:
        Updated vital
        
    Raises:
        HTTPException 404: Vital not found
    """
    service = VitalService(db)
    result = await service.update_vital(current_user.id, vital_id, data)
    if result is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Vital not found",
        )
    return result


@router.delete(
    "/{vital_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a vital",
    description="Delete a specific vital reading by ID.",
    responses={
        204: {"description": "Vital deleted successfully"},
        401: {"description": "Not authenticated"},
        404: {"description": "Vital not found"},
    },
)
async def delete_vital(
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
    vital_id: UUID,
) -> None:
    """Delete a vital reading.
    
    Args:
        current_user: Authenticated user (injected)
        db: Database session (injected)
        vital_id: Vital's UUID
        
    Raises:
        HTTPException 404: Vital not found
    """
    service = VitalService(db)
    deleted = await service.delete_vital(current_user.id, vital_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Vital not found",
        )


# ============================================================================
# Target Range Endpoints
# ============================================================================

@router.post(
    "/target-ranges",
    response_model=VitalTargetRangeResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Set target range",
    description="Set a custom target range for a vital type.",
    responses={
        201: {"description": "Target range set successfully"},
        401: {"description": "Not authenticated"},
        422: {"description": "Validation error"},
    },
)
async def set_target_range(
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
    data: VitalTargetRangeCreate,
) -> VitalTargetRangeResponse:
    """Set a custom target range.
    
    Validates: Requirements 16.4
    
    Args:
        current_user: Authenticated user (injected)
        db: Database session (injected)
        data: Target range data
        
    Returns:
        Created or updated target range
    """
    service = VitalService(db)
    try:
        return await service.set_target_range(current_user.id, data)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.get(
    "/target-ranges",
    response_model=PaginatedVitalTargetRangeResponse,
    status_code=status.HTTP_200_OK,
    summary="List target ranges",
    description="List all custom target ranges.",
    responses={
        200: {"description": "Target ranges returned successfully"},
        401: {"description": "Not authenticated"},
    },
)
async def list_target_ranges(
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
    family_member_id: Annotated[
        Optional[UUID],
        Query(description="Filter by family member (null for self)")
    ] = None,
    page: Annotated[int, Query(ge=1, description="Page number (1-indexed)")] = 1,
    page_size: Annotated[int, Query(ge=1, le=100, description="Number of results per page")] = 20,
) -> PaginatedVitalTargetRangeResponse:
    """List all custom target ranges.
    
    Args:
        current_user: Authenticated user (injected)
        db: Database session (injected)
        family_member_id: Optional family member filter
        page: Page number (1-indexed)
        page_size: Number of results per page
        
    Returns:
        Paginated list of target ranges
    """
    service = VitalService(db)
    return await service.list_target_ranges(
        current_user.id, family_member_id, page, page_size
    )


@router.get(
    "/target-ranges/{vital_type}",
    response_model=VitalTargetRangeResponse,
    status_code=status.HTTP_200_OK,
    summary="Get target range",
    description="Get target range for a specific vital type.",
    responses={
        200: {"description": "Target range returned successfully"},
        401: {"description": "Not authenticated"},
        404: {"description": "Target range not found"},
    },
)
async def get_target_range(
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
    vital_type: str,
    family_member_id: Annotated[
        Optional[UUID],
        Query(description="Filter by family member (null for self)")
    ] = None,
) -> VitalTargetRangeResponse:
    """Get target range for a vital type.
    
    Args:
        current_user: Authenticated user (injected)
        db: Database session (injected)
        vital_type: Type of vital
        family_member_id: Optional family member filter
        
    Returns:
        Target range
        
    Raises:
        HTTPException 404: Target range not found
    """
    if vital_type not in VitalTypeEnum.ALL:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Vital type must be one of: {', '.join(VitalTypeEnum.ALL)}",
        )
    
    service = VitalService(db)
    result = await service.get_target_range(current_user.id, vital_type, family_member_id)
    if result is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Target range not found",
        )
    return result


@router.delete(
    "/target-ranges/{range_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete target range",
    description="Delete a custom target range.",
    responses={
        204: {"description": "Target range deleted successfully"},
        401: {"description": "Not authenticated"},
        404: {"description": "Target range not found"},
    },
)
async def delete_target_range(
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
    range_id: UUID,
) -> None:
    """Delete a custom target range.
    
    Args:
        current_user: Authenticated user (injected)
        db: Database session (injected)
        range_id: Target range's UUID
        
    Raises:
        HTTPException 404: Target range not found
    """
    service = VitalService(db)
    deleted = await service.delete_target_range(current_user.id, range_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Target range not found",
        )
