"""Budget router for Money Manager module endpoints.

Provides CRUD endpoints for budgets and budget progress tracking.

Validates: Requirements 11.1, 11.2, 11.3, 11.4, 11.5, 11.6
"""

from typing import Annotated, List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import CurrentUser
from app.schemas.budget import (
    BudgetCreate,
    BudgetUpdate,
    BudgetWithCategoryResponse,
    BudgetProgressResponse,
    BudgetHistoryResponse,
    BudgetSummaryResponse,
)
from app.schemas.document import PaginatedResponse
from app.services.budget import BudgetService

router = APIRouter()


# ============================================================================
# Budget CRUD Endpoints
# ============================================================================

@router.post(
    "",
    response_model=BudgetWithCategoryResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create budget",
    description="Create a new budget for a category with amount and period (weekly/monthly).",
    responses={
        201: {"description": "Budget created successfully"},
        400: {"description": "Invalid category or budget already exists"},
        401: {"description": "Not authenticated"},
        422: {"description": "Validation error"},
    },
)
async def create_budget(
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
    data: BudgetCreate,
) -> BudgetWithCategoryResponse:
    """Create a new budget.
    
    Validates: Requirements 11.1
    
    Args:
        current_user: Authenticated user
        db: Database session
        data: Budget creation data
        
    Returns:
        Created budget with category details
        
    Raises:
        HTTPException 400: Invalid category or budget already exists
    """
    service = BudgetService(db)
    try:
        return await service.create_budget(current_user.id, data)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.get(
    "",
    response_model=List[BudgetWithCategoryResponse],
    status_code=status.HTTP_200_OK,
    summary="List budgets",
    description="Get all budgets for the user.",
    responses={
        200: {"description": "Budgets returned successfully"},
        401: {"description": "Not authenticated"},
    },
)
async def list_budgets(
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
    active_only: Annotated[
        bool,
        Query(description="Only return active budgets")
    ] = True,
) -> List[BudgetWithCategoryResponse]:
    """Get all budgets for the user.
    
    Args:
        current_user: Authenticated user
        db: Database session
        active_only: Only return active budgets
        
    Returns:
        List of budgets with category details
    """
    service = BudgetService(db)
    return await service.get_budgets(current_user.id, active_only)


@router.get(
    "/summary",
    response_model=BudgetSummaryResponse,
    status_code=status.HTTP_200_OK,
    summary="Get budget summary",
    description="Get overall budget summary with all budgets and their progress.",
    responses={
        200: {"description": "Budget summary returned successfully"},
        401: {"description": "Not authenticated"},
    },
)
async def get_budget_summary(
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> BudgetSummaryResponse:
    """Get overall budget summary.
    
    Validates: Requirements 11.5
    
    Args:
        current_user: Authenticated user
        db: Database session
        
    Returns:
        Budget summary with all budgets and progress
    """
    service = BudgetService(db)
    return await service.get_budget_summary(current_user.id)


@router.get(
    "/progress",
    response_model=List[BudgetProgressResponse],
    status_code=status.HTTP_200_OK,
    summary="Get all budget progress",
    description="Get progress for all active budgets with visual indicators.",
    responses={
        200: {"description": "Budget progress returned successfully"},
        401: {"description": "Not authenticated"},
    },
)
async def get_all_budget_progress(
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> List[BudgetProgressResponse]:
    """Get progress for all active budgets.
    
    Validates: Requirements 11.5
    
    Args:
        current_user: Authenticated user
        db: Database session
        
    Returns:
        List of budget progress with visual indicators
    """
    service = BudgetService(db)
    return await service.get_all_budget_progress(current_user.id)


@router.get(
    "/history",
    response_model=PaginatedResponse[BudgetHistoryResponse],
    status_code=status.HTTP_200_OK,
    summary="Get budget history",
    description="Get archived budget history for past periods.",
    responses={
        200: {"description": "Budget history returned successfully"},
        401: {"description": "Not authenticated"},
    },
)
async def get_budget_history(
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
    category_id: Annotated[
        Optional[UUID],
        Query(description="Filter by category ID")
    ] = None,
    page: Annotated[
        int,
        Query(ge=1, description="Page number (1-indexed)")
    ] = 1,
    page_size: Annotated[
        int,
        Query(ge=1, le=100, description="Number of results per page")
    ] = 20,
) -> PaginatedResponse[BudgetHistoryResponse]:
    """Get budget history for past periods.
    
    Validates: Requirements 11.6
    
    Args:
        current_user: Authenticated user
        db: Database session
        category_id: Optional category filter
        page: Page number (1-indexed)
        page_size: Number of results per page
        
    Returns:
        Paginated list of budget history
    """
    service = BudgetService(db)
    return await service.get_budget_history(
        current_user.id, category_id, page, page_size
    )


@router.get(
    "/{budget_id}",
    response_model=BudgetWithCategoryResponse,
    status_code=status.HTTP_200_OK,
    summary="Get budget",
    description="Get a specific budget by ID.",
    responses={
        200: {"description": "Budget returned successfully"},
        401: {"description": "Not authenticated"},
        404: {"description": "Budget not found"},
    },
)
async def get_budget(
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
    budget_id: UUID,
) -> BudgetWithCategoryResponse:
    """Get a budget by ID.
    
    Args:
        current_user: Authenticated user
        db: Database session
        budget_id: Budget UUID
        
    Returns:
        Budget with category details
        
    Raises:
        HTTPException 404: Budget not found
    """
    service = BudgetService(db)
    budget = await service.get_budget(budget_id, current_user.id)
    if budget is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Budget not found",
        )
    return budget


@router.get(
    "/{budget_id}/progress",
    response_model=BudgetProgressResponse,
    status_code=status.HTTP_200_OK,
    summary="Get budget progress",
    description="Get progress for a specific budget with visual indicators.",
    responses={
        200: {"description": "Budget progress returned successfully"},
        401: {"description": "Not authenticated"},
        404: {"description": "Budget not found"},
    },
)
async def get_budget_progress(
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
    budget_id: UUID,
) -> BudgetProgressResponse:
    """Get progress for a specific budget.
    
    Validates: Requirements 11.5
    
    Args:
        current_user: Authenticated user
        db: Database session
        budget_id: Budget UUID
        
    Returns:
        Budget progress with visual indicators
        
    Raises:
        HTTPException 404: Budget not found
    """
    service = BudgetService(db)
    progress = await service.get_budget_progress(budget_id, current_user.id)
    if progress is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Budget not found",
        )
    return progress


@router.put(
    "/{budget_id}",
    response_model=BudgetWithCategoryResponse,
    status_code=status.HTTP_200_OK,
    summary="Update budget",
    description="Update a budget's amount or period.",
    responses={
        200: {"description": "Budget updated successfully"},
        401: {"description": "Not authenticated"},
        404: {"description": "Budget not found"},
        422: {"description": "Validation error"},
    },
)
async def update_budget(
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
    budget_id: UUID,
    data: BudgetUpdate,
) -> BudgetWithCategoryResponse:
    """Update a budget.
    
    Args:
        current_user: Authenticated user
        db: Database session
        budget_id: Budget UUID
        data: Budget update data
        
    Returns:
        Updated budget with category details
        
    Raises:
        HTTPException 404: Budget not found
    """
    service = BudgetService(db)
    budget = await service.update_budget(budget_id, current_user.id, data)
    if budget is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Budget not found",
        )
    return budget


@router.delete(
    "/{budget_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete budget",
    description="Delete a budget.",
    responses={
        204: {"description": "Budget deleted successfully"},
        401: {"description": "Not authenticated"},
        404: {"description": "Budget not found"},
    },
)
async def delete_budget(
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
    budget_id: UUID,
) -> None:
    """Delete a budget.
    
    Args:
        current_user: Authenticated user
        db: Database session
        budget_id: Budget UUID
        
    Raises:
        HTTPException 404: Budget not found
    """
    service = BudgetService(db)
    deleted = await service.delete_budget(budget_id, current_user.id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Budget not found",
        )
