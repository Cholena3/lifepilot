"""Health records router for health record management endpoints.

Validates: Requirements 14.1, 14.2, 14.3, 14.4, 14.5, 14.6
"""

from datetime import date
from typing import Annotated, List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import CurrentUser
from app.schemas.health import (
    HealthRecordCategory,
    HealthRecordCreate,
    HealthRecordUpdate,
    HealthRecordResponse,
    FamilyMemberCreate,
    FamilyMemberUpdate,
    FamilyMemberResponse,
    PaginatedHealthRecordResponse,
    PaginatedFamilyMemberResponse,
    HealthTimelineResponse,
)
from app.schemas.ocr import (
    PrescriptionOCRTaskResponse,
    MedicineInfoResponse,
    MedicineTrackerEntryCreate,
)
from app.services.health import HealthService

router = APIRouter()


# ============================================================================
# Family Member Endpoints
# ============================================================================

@router.post(
    "/family-members",
    response_model=FamilyMemberResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a family member",
    description="Create a new family member for managing health records.",
    responses={
        201: {"description": "Family member created successfully"},
        401: {"description": "Not authenticated"},
        422: {"description": "Validation error"},
    },
)
async def create_family_member(
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
    data: FamilyMemberCreate,
) -> FamilyMemberResponse:
    """Create a new family member.
    
    Validates: Requirements 14.2
    
    Args:
        current_user: Authenticated user (injected)
        db: Database session (injected)
        data: Family member creation data
        
    Returns:
        Created family member
    """
    service = HealthService(db)
    return await service.create_family_member(current_user.id, data)


@router.get(
    "/family-members",
    response_model=PaginatedFamilyMemberResponse,
    status_code=status.HTTP_200_OK,
    summary="List family members",
    description="List all family members for the authenticated user.",
    responses={
        200: {"description": "Family members returned successfully"},
        401: {"description": "Not authenticated"},
    },
)
async def list_family_members(
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
    page: Annotated[int, Query(ge=1, description="Page number (1-indexed)")] = 1,
    page_size: Annotated[int, Query(ge=1, le=100, description="Number of results per page")] = 20,
) -> PaginatedFamilyMemberResponse:
    """List all family members.
    
    Validates: Requirements 14.2
    
    Args:
        current_user: Authenticated user (injected)
        db: Database session (injected)
        page: Page number (1-indexed)
        page_size: Number of results per page
        
    Returns:
        Paginated list of family members
    """
    service = HealthService(db)
    return await service.list_family_members(current_user.id, page, page_size)


@router.get(
    "/family-members/{family_member_id}",
    response_model=FamilyMemberResponse,
    status_code=status.HTTP_200_OK,
    summary="Get a family member",
    description="Get a specific family member by ID.",
    responses={
        200: {"description": "Family member returned successfully"},
        401: {"description": "Not authenticated"},
        404: {"description": "Family member not found"},
    },
)
async def get_family_member(
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
    family_member_id: UUID,
) -> FamilyMemberResponse:
    """Get a family member by ID.
    
    Args:
        current_user: Authenticated user (injected)
        db: Database session (injected)
        family_member_id: Family member's UUID
        
    Returns:
        Family member details
        
    Raises:
        HTTPException 404: Family member not found
    """
    service = HealthService(db)
    result = await service.get_family_member(current_user.id, family_member_id)
    if result is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Family member not found",
        )
    return result


@router.patch(
    "/family-members/{family_member_id}",
    response_model=FamilyMemberResponse,
    status_code=status.HTTP_200_OK,
    summary="Update a family member",
    description="Update a specific family member by ID.",
    responses={
        200: {"description": "Family member updated successfully"},
        401: {"description": "Not authenticated"},
        404: {"description": "Family member not found"},
        422: {"description": "Validation error"},
    },
)
async def update_family_member(
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
    family_member_id: UUID,
    data: FamilyMemberUpdate,
) -> FamilyMemberResponse:
    """Update a family member.
    
    Args:
        current_user: Authenticated user (injected)
        db: Database session (injected)
        family_member_id: Family member's UUID
        data: Family member update data
        
    Returns:
        Updated family member
        
    Raises:
        HTTPException 404: Family member not found
    """
    service = HealthService(db)
    result = await service.update_family_member(current_user.id, family_member_id, data)
    if result is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Family member not found",
        )
    return result


@router.delete(
    "/family-members/{family_member_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a family member",
    description="Delete a specific family member by ID.",
    responses={
        204: {"description": "Family member deleted successfully"},
        401: {"description": "Not authenticated"},
        404: {"description": "Family member not found"},
    },
)
async def delete_family_member(
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
    family_member_id: UUID,
) -> None:
    """Delete a family member.
    
    Args:
        current_user: Authenticated user (injected)
        db: Database session (injected)
        family_member_id: Family member's UUID
        
    Raises:
        HTTPException 404: Family member not found
    """
    service = HealthService(db)
    deleted = await service.delete_family_member(current_user.id, family_member_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Family member not found",
        )


# ============================================================================
# Health Record Endpoints
# ============================================================================

@router.post(
    "/records",
    response_model=HealthRecordResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a health record",
    description="Upload a new health record with categorization.",
    responses={
        201: {"description": "Health record created successfully"},
        401: {"description": "Not authenticated"},
        422: {"description": "Validation error"},
    },
)
async def create_health_record(
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
    data: HealthRecordCreate,
) -> HealthRecordResponse:
    """Create a new health record.
    
    Validates: Requirements 14.1, 14.2
    
    Args:
        current_user: Authenticated user (injected)
        db: Database session (injected)
        data: Health record creation data
        
    Returns:
        Created health record
        
    Raises:
        HTTPException 422: Invalid family member
    """
    service = HealthService(db)
    
    # TODO: In production, handle file upload and encryption
    # For now, use placeholder values
    file_path = f"health_records/{current_user.id}/{data.title}"
    encryption_key = "placeholder_encryption_key"
    
    try:
        return await service.create_health_record(
            current_user.id, data, file_path, encryption_key
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(e),
        )


@router.get(
    "/records",
    response_model=PaginatedHealthRecordResponse,
    status_code=status.HTTP_200_OK,
    summary="List health records",
    description="List health records with optional filtering by category and family member.",
    responses={
        200: {"description": "Health records returned successfully"},
        401: {"description": "Not authenticated"},
        422: {"description": "Validation error"},
    },
)
async def list_health_records(
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
    category: Annotated[
        Optional[str],
        Query(description="Filter by category (prescription, lab_report, scan, vaccine, insurance)")
    ] = None,
    family_member_id: Annotated[
        Optional[UUID],
        Query(description="Filter by family member ID")
    ] = None,
    start_date: Annotated[
        Optional[date],
        Query(description="Filter records from this date")
    ] = None,
    end_date: Annotated[
        Optional[date],
        Query(description="Filter records until this date")
    ] = None,
    page: Annotated[int, Query(ge=1, description="Page number (1-indexed)")] = 1,
    page_size: Annotated[int, Query(ge=1, le=100, description="Number of results per page")] = 20,
) -> PaginatedHealthRecordResponse:
    """List health records with optional filtering.
    
    Validates: Requirements 14.1, 14.2, 14.5
    
    Args:
        current_user: Authenticated user (injected)
        db: Database session (injected)
        category: Optional category filter
        family_member_id: Optional family member filter
        start_date: Optional start date filter
        end_date: Optional end date filter
        page: Page number (1-indexed)
        page_size: Number of results per page
        
    Returns:
        Paginated list of health records
    """
    # Validate category if provided
    if category is not None and category not in HealthRecordCategory.ALL:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Category must be one of: {', '.join(HealthRecordCategory.ALL)}",
        )
    
    service = HealthService(db)
    return await service.list_health_records(
        current_user.id,
        category=category,
        family_member_id=family_member_id,
        start_date=start_date,
        end_date=end_date,
        page=page,
        page_size=page_size,
    )


@router.get(
    "/records/search",
    response_model=PaginatedHealthRecordResponse,
    status_code=status.HTTP_200_OK,
    summary="Search health records",
    description="Search health records by full-text search across all record types and family members.",
    responses={
        200: {"description": "Search results returned successfully"},
        401: {"description": "Not authenticated"},
        422: {"description": "Validation error"},
    },
)
async def search_health_records(
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
    query: Annotated[
        str,
        Query(min_length=1, max_length=500, description="Search query string")
    ],
    category: Annotated[
        Optional[str],
        Query(description="Optional category filter")
    ] = None,
    family_member_id: Annotated[
        Optional[UUID],
        Query(description="Optional family member filter")
    ] = None,
    page: Annotated[int, Query(ge=1, description="Page number (1-indexed)")] = 1,
    page_size: Annotated[int, Query(ge=1, le=100, description="Number of results per page")] = 20,
) -> PaginatedHealthRecordResponse:
    """Search health records by full-text search.
    
    Validates: Requirements 14.6
    
    Searches across:
    - Record title
    - Doctor name
    - Hospital name
    - OCR extracted text
    - Notes
    
    Args:
        current_user: Authenticated user (injected)
        db: Database session (injected)
        query: Search query string
        category: Optional category filter
        family_member_id: Optional family member filter
        page: Page number (1-indexed)
        page_size: Number of results per page
        
    Returns:
        Paginated search results
    """
    # Validate category if provided
    if category is not None and category not in HealthRecordCategory.ALL:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Category must be one of: {', '.join(HealthRecordCategory.ALL)}",
        )
    
    service = HealthService(db)
    return await service.search_health_records(
        current_user.id,
        query,
        category=category,
        family_member_id=family_member_id,
        page=page,
        page_size=page_size,
    )


@router.get(
    "/records/timeline",
    response_model=HealthTimelineResponse,
    status_code=status.HTTP_200_OK,
    summary="Get health timeline",
    description="Get a chronological health timeline for the user and optionally filtered by family member.",
    responses={
        200: {"description": "Timeline returned successfully"},
        401: {"description": "Not authenticated"},
    },
)
async def get_health_timeline(
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
    family_member_id: Annotated[
        Optional[UUID],
        Query(description="Optional family member filter (null for all records)")
    ] = None,
    page: Annotated[int, Query(ge=1, description="Page number (1-indexed)")] = 1,
    page_size: Annotated[int, Query(ge=1, le=100, description="Number of results per page")] = 20,
) -> HealthTimelineResponse:
    """Get chronological health timeline.
    
    Validates: Requirements 14.5, 14.6
    
    Returns health records in chronological order (most recent first),
    including records for the user and all family members unless filtered.
    
    Args:
        current_user: Authenticated user (injected)
        db: Database session (injected)
        family_member_id: Optional family member filter
        page: Page number (1-indexed)
        page_size: Number of results per page
        
    Returns:
        Chronological health timeline
    """
    service = HealthService(db)
    return await service.get_health_timeline(
        current_user.id,
        family_member_id=family_member_id,
        page=page,
        page_size=page_size,
    )


@router.get(
    "/records/{record_id}",
    response_model=HealthRecordResponse,
    status_code=status.HTTP_200_OK,
    summary="Get a health record",
    description="Get a specific health record by ID.",
    responses={
        200: {"description": "Health record returned successfully"},
        401: {"description": "Not authenticated"},
        404: {"description": "Health record not found"},
    },
)
async def get_health_record(
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
    record_id: UUID,
) -> HealthRecordResponse:
    """Get a health record by ID.
    
    Args:
        current_user: Authenticated user (injected)
        db: Database session (injected)
        record_id: Health record's UUID
        
    Returns:
        Health record details
        
    Raises:
        HTTPException 404: Health record not found
    """
    service = HealthService(db)
    result = await service.get_health_record(current_user.id, record_id)
    if result is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Health record not found",
        )
    return result


@router.patch(
    "/records/{record_id}",
    response_model=HealthRecordResponse,
    status_code=status.HTTP_200_OK,
    summary="Update a health record",
    description="Update a specific health record by ID.",
    responses={
        200: {"description": "Health record updated successfully"},
        401: {"description": "Not authenticated"},
        404: {"description": "Health record not found"},
        422: {"description": "Validation error"},
    },
)
async def update_health_record(
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
    record_id: UUID,
    data: HealthRecordUpdate,
) -> HealthRecordResponse:
    """Update a health record.
    
    Args:
        current_user: Authenticated user (injected)
        db: Database session (injected)
        record_id: Health record's UUID
        data: Health record update data
        
    Returns:
        Updated health record
        
    Raises:
        HTTPException 404: Health record not found
        HTTPException 422: Invalid family member
    """
    service = HealthService(db)
    try:
        result = await service.update_health_record(current_user.id, record_id, data)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(e),
        )
    
    if result is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Health record not found",
        )
    return result


@router.delete(
    "/records/{record_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a health record",
    description="Delete a specific health record by ID.",
    responses={
        204: {"description": "Health record deleted successfully"},
        401: {"description": "Not authenticated"},
        404: {"description": "Health record not found"},
    },
)
async def delete_health_record(
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
    record_id: UUID,
) -> None:
    """Delete a health record.
    
    Args:
        current_user: Authenticated user (injected)
        db: Database session (injected)
        record_id: Health record's UUID
        
    Raises:
        HTTPException 404: Health record not found
    """
    service = HealthService(db)
    deleted = await service.delete_health_record(current_user.id, record_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Health record not found",
        )


# ============================================================================
# Category Endpoint
# ============================================================================

@router.get(
    "/categories",
    response_model=list[str],
    status_code=status.HTTP_200_OK,
    summary="List health record categories",
    description="Get the list of valid health record categories.",
    responses={
        200: {"description": "Categories returned successfully"},
    },
)
async def list_categories() -> list[str]:
    """List all valid health record categories.
    
    Validates: Requirements 14.1
    
    Returns:
        List of valid category names
    """
    return HealthRecordCategory.ALL


# ============================================================================
# Prescription OCR Endpoints
# ============================================================================

@router.post(
    "/records/{record_id}/ocr",
    response_model=PrescriptionOCRTaskResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Trigger prescription OCR processing",
    description="Queue a prescription health record for OCR processing to extract doctor name, medicines, dosage, and frequency.",
    responses={
        202: {"description": "OCR processing queued successfully"},
        401: {"description": "Not authenticated"},
        404: {"description": "Health record not found"},
        422: {"description": "Record is not a prescription"},
    },
)
async def trigger_prescription_ocr(
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
    record_id: UUID,
) -> PrescriptionOCRTaskResponse:
    """Trigger async OCR processing for a prescription health record.
    
    Validates: Requirements 14.3, 14.4
    
    This endpoint queues the prescription for OCR processing using Celery.
    The OCR task will:
    1. Extract text from the prescription image using Google Cloud Vision API
    2. Parse doctor name, hospital name, patient name, and prescription date
    3. Extract medicine names, dosages, frequencies, and durations
    4. Store the extracted data in the health record
    
    Args:
        current_user: Authenticated user (injected)
        db: Database session (injected)
        record_id: Health record's UUID
        
    Returns:
        Task response with Celery task ID for tracking
        
    Raises:
        HTTPException 404: Health record not found
        HTTPException 422: Record is not a prescription category
    """
    service = HealthService(db)
    
    try:
        task_id = await service.trigger_prescription_ocr(current_user.id, record_id)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(e),
        )
    
    if task_id is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Health record not found",
        )
    
    return PrescriptionOCRTaskResponse(
        task_id=task_id,
        health_record_id=record_id,
        status="queued",
        message="Prescription OCR processing queued successfully",
    )


@router.get(
    "/records/{record_id}/medicines",
    response_model=List[MedicineInfoResponse],
    status_code=status.HTTP_200_OK,
    summary="Get extracted medicines from prescription",
    description="Get the list of medicines extracted from a prescription health record via OCR.",
    responses={
        200: {"description": "Medicines returned successfully"},
        401: {"description": "Not authenticated"},
        404: {"description": "Health record not found"},
    },
)
async def get_extracted_medicines(
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
    record_id: UUID,
) -> List[MedicineInfoResponse]:
    """Get extracted medicines from a prescription health record.
    
    Validates: Requirements 14.3, 14.4
    
    Returns the list of medicines that were extracted from the prescription
    via OCR processing. Each medicine includes name, dosage, frequency,
    duration, and instructions if available.
    
    Args:
        current_user: Authenticated user (injected)
        db: Database session (injected)
        record_id: Health record's UUID
        
    Returns:
        List of extracted medicines
        
    Raises:
        HTTPException 404: Health record not found
    """
    service = HealthService(db)
    medicines = await service.get_extracted_medicines(current_user.id, record_id)
    
    if medicines is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Health record not found",
        )
    
    # Convert to response schema
    return [
        MedicineInfoResponse(
            name=med.get("name", "Unknown"),
            dosage=med.get("dosage"),
            frequency=med.get("frequency"),
            duration=med.get("duration"),
            instructions=med.get("instructions"),
            confidence=med.get("confidence", 0.0),
        )
        for med in medicines
    ]


@router.get(
    "/records/{record_id}/medicine-tracker-entries",
    response_model=List[MedicineTrackerEntryCreate],
    status_code=status.HTTP_200_OK,
    summary="Get medicine tracker entries from prescription",
    description="Get prepared medicine tracker entries from a prescription health record for auto-creation.",
    responses={
        200: {"description": "Medicine tracker entries returned successfully"},
        401: {"description": "Not authenticated"},
        404: {"description": "Health record not found"},
    },
)
async def get_medicine_tracker_entries(
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
    record_id: UUID,
) -> List[MedicineTrackerEntryCreate]:
    """Get prepared medicine tracker entries from a prescription.
    
    Validates: Requirements 14.4
    
    This endpoint prepares medicine data from OCR extraction for creating
    medicine tracker entries. The returned data can be used to auto-create
    medicine tracker entries (implemented in task 11.5).
    
    The entries include:
    - Medicine name
    - Dosage
    - Frequency
    - Duration in days (parsed from duration string)
    - Instructions
    - Source health record ID
    
    Args:
        current_user: Authenticated user (injected)
        db: Database session (injected)
        record_id: Health record's UUID
        
    Returns:
        List of medicine tracker entry data ready for creation
        
    Raises:
        HTTPException 404: Health record not found
    """
    service = HealthService(db)
    
    # Check if record exists
    record = await service.get_health_record(current_user.id, record_id)
    if record is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Health record not found",
        )
    
    entries = await service.prepare_medicine_tracker_entries(current_user.id, record_id)
    
    return [
        MedicineTrackerEntryCreate(
            name=entry.get("name", "Unknown"),
            dosage=entry.get("dosage"),
            frequency=entry.get("frequency"),
            duration_days=entry.get("duration_days"),
            instructions=entry.get("instructions"),
            health_record_id=UUID(entry.get("health_record_id")) if entry.get("health_record_id") else None,
        )
        for entry in entries
        if entry.get("name")  # Only include entries with a name
    ]
