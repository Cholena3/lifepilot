"""Expense router for Money Manager module endpoints.

Provides CRUD endpoints for expenses and expense categories.

Validates: Requirements 10.1, 10.4, 10.5, 10.6
"""

from datetime import date
from decimal import Decimal
from typing import Annotated, List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import CurrentUser
from app.schemas.document import PaginatedResponse
from app.schemas.expense import (
    ExpenseCreate,
    ExpenseUpdate,
    ExpenseResponse,
    ExpenseWithCategoryResponse,
    ExpenseCategoryCreate,
    ExpenseCategoryUpdate,
    ExpenseCategoryResponse,
    ReceiptUploadResponse,
)
from app.services.expense import ExpenseService

router = APIRouter()


# ============================================================================
# Category Endpoints
# ============================================================================

@router.post(
    "/categories",
    response_model=ExpenseCategoryResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create expense category",
    description="Create a new custom expense category for the user.",
    responses={
        201: {"description": "Category created successfully"},
        401: {"description": "Not authenticated"},
        422: {"description": "Validation error"},
    },
)
async def create_category(
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
    data: ExpenseCategoryCreate,
) -> ExpenseCategoryResponse:
    """Create a new expense category.
    
    Validates: Requirements 10.4
    
    Args:
        current_user: Authenticated user
        db: Database session
        data: Category creation data
        
    Returns:
        Created category
    """
    service = ExpenseService(db)
    return await service.create_category(current_user.id, data)


@router.get(
    "/categories",
    response_model=List[ExpenseCategoryResponse],
    status_code=status.HTTP_200_OK,
    summary="List expense categories",
    description="Get all expense categories available to the user (custom + defaults).",
    responses={
        200: {"description": "Categories returned successfully"},
        401: {"description": "Not authenticated"},
    },
)
async def list_categories(
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> List[ExpenseCategoryResponse]:
    """Get all expense categories for the user.
    
    Validates: Requirements 10.4
    
    Returns both user's custom categories and system default categories.
    
    Args:
        current_user: Authenticated user
        db: Database session
        
    Returns:
        List of categories
    """
    service = ExpenseService(db)
    return await service.get_categories(current_user.id)


@router.get(
    "/categories/{category_id}",
    response_model=ExpenseCategoryResponse,
    status_code=status.HTTP_200_OK,
    summary="Get expense category",
    description="Get a specific expense category by ID.",
    responses={
        200: {"description": "Category returned successfully"},
        401: {"description": "Not authenticated"},
        404: {"description": "Category not found"},
    },
)
async def get_category(
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
    category_id: UUID,
) -> ExpenseCategoryResponse:
    """Get an expense category by ID.
    
    Args:
        current_user: Authenticated user
        db: Database session
        category_id: Category UUID
        
    Returns:
        Category details
        
    Raises:
        HTTPException 404: Category not found
    """
    service = ExpenseService(db)
    category = await service.get_category(category_id, current_user.id)
    if category is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Category not found",
        )
    return category


@router.put(
    "/categories/{category_id}",
    response_model=ExpenseCategoryResponse,
    status_code=status.HTTP_200_OK,
    summary="Update expense category",
    description="Update a custom expense category. Default categories cannot be updated.",
    responses={
        200: {"description": "Category updated successfully"},
        400: {"description": "Cannot update default category"},
        401: {"description": "Not authenticated"},
        404: {"description": "Category not found"},
        422: {"description": "Validation error"},
    },
)
async def update_category(
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
    category_id: UUID,
    data: ExpenseCategoryUpdate,
) -> ExpenseCategoryResponse:
    """Update an expense category.
    
    Validates: Requirements 10.4
    
    Args:
        current_user: Authenticated user
        db: Database session
        category_id: Category UUID
        data: Category update data
        
    Returns:
        Updated category
        
    Raises:
        HTTPException 400: Cannot update default category
        HTTPException 404: Category not found
    """
    service = ExpenseService(db)
    try:
        category = await service.update_category(category_id, current_user.id, data)
        if category is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Category not found",
            )
        return category
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.delete(
    "/categories/{category_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete expense category",
    description="Delete a custom expense category. Default categories and categories with expenses cannot be deleted.",
    responses={
        204: {"description": "Category deleted successfully"},
        400: {"description": "Cannot delete default category or category with expenses"},
        401: {"description": "Not authenticated"},
        404: {"description": "Category not found"},
    },
)
async def delete_category(
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
    category_id: UUID,
) -> None:
    """Delete an expense category.
    
    Validates: Requirements 10.4
    
    Args:
        current_user: Authenticated user
        db: Database session
        category_id: Category UUID
        
    Raises:
        HTTPException 400: Cannot delete default category or category with expenses
        HTTPException 404: Category not found
    """
    service = ExpenseService(db)
    try:
        deleted = await service.delete_category(category_id, current_user.id)
        if not deleted:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Category not found",
            )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


# ============================================================================
# Expense Endpoints
# ============================================================================

@router.post(
    "",
    response_model=ExpenseWithCategoryResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create expense",
    description="Log a new expense with amount, category, description, and date.",
    responses={
        201: {"description": "Expense created successfully"},
        400: {"description": "Invalid category"},
        401: {"description": "Not authenticated"},
        422: {"description": "Validation error"},
    },
)
async def create_expense(
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
    data: ExpenseCreate,
) -> ExpenseWithCategoryResponse:
    """Create a new expense.
    
    Validates: Requirements 10.1
    
    Args:
        current_user: Authenticated user
        db: Database session
        data: Expense creation data
        
    Returns:
        Created expense with category details
        
    Raises:
        HTTPException 400: Invalid category
    """
    service = ExpenseService(db)
    try:
        return await service.create_expense(current_user.id, data)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.get(
    "",
    response_model=PaginatedResponse[ExpenseWithCategoryResponse],
    status_code=status.HTTP_200_OK,
    summary="List expenses",
    description="Get expenses with optional filtering by category, date range, and amount.",
    responses={
        200: {"description": "Expenses returned successfully"},
        401: {"description": "Not authenticated"},
        422: {"description": "Validation error"},
    },
)
async def list_expenses(
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
    category_id: Annotated[
        Optional[UUID],
        Query(description="Filter by category ID")
    ] = None,
    start_date: Annotated[
        Optional[date],
        Query(description="Filter expenses from this date")
    ] = None,
    end_date: Annotated[
        Optional[date],
        Query(description="Filter expenses until this date")
    ] = None,
    min_amount: Annotated[
        Optional[Decimal],
        Query(ge=0, description="Minimum expense amount")
    ] = None,
    max_amount: Annotated[
        Optional[Decimal],
        Query(ge=0, description="Maximum expense amount")
    ] = None,
    page: Annotated[
        int,
        Query(ge=1, description="Page number (1-indexed)")
    ] = 1,
    page_size: Annotated[
        int,
        Query(ge=1, le=100, description="Number of results per page")
    ] = 20,
) -> PaginatedResponse[ExpenseWithCategoryResponse]:
    """Get expenses for the user with optional filtering.
    
    Args:
        current_user: Authenticated user
        db: Database session
        category_id: Optional category filter
        start_date: Optional start date filter
        end_date: Optional end date filter
        min_amount: Optional minimum amount filter
        max_amount: Optional maximum amount filter
        page: Page number (1-indexed)
        page_size: Number of results per page
        
    Returns:
        Paginated list of expenses
    """
    # Validate date range
    if start_date and end_date and end_date < start_date:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="end_date must not be before start_date",
        )
    
    service = ExpenseService(db)
    return await service.get_expenses(
        user_id=current_user.id,
        category_id=category_id,
        start_date=start_date,
        end_date=end_date,
        min_amount=min_amount,
        max_amount=max_amount,
        page=page,
        page_size=page_size,
    )


@router.get(
    "/{expense_id}",
    response_model=ExpenseWithCategoryResponse,
    status_code=status.HTTP_200_OK,
    summary="Get expense",
    description="Get a specific expense by ID.",
    responses={
        200: {"description": "Expense returned successfully"},
        401: {"description": "Not authenticated"},
        404: {"description": "Expense not found"},
    },
)
async def get_expense(
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
    expense_id: UUID,
) -> ExpenseWithCategoryResponse:
    """Get an expense by ID.
    
    Args:
        current_user: Authenticated user
        db: Database session
        expense_id: Expense UUID
        
    Returns:
        Expense details with category
        
    Raises:
        HTTPException 404: Expense not found
    """
    service = ExpenseService(db)
    expense = await service.get_expense(expense_id, current_user.id)
    if expense is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Expense not found",
        )
    return expense


@router.put(
    "/{expense_id}",
    response_model=ExpenseWithCategoryResponse,
    status_code=status.HTTP_200_OK,
    summary="Update expense",
    description="Update an existing expense.",
    responses={
        200: {"description": "Expense updated successfully"},
        400: {"description": "Invalid category"},
        401: {"description": "Not authenticated"},
        404: {"description": "Expense not found"},
        422: {"description": "Validation error"},
    },
)
async def update_expense(
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
    expense_id: UUID,
    data: ExpenseUpdate,
) -> ExpenseWithCategoryResponse:
    """Update an expense.
    
    Validates: Requirements 10.5
    
    Args:
        current_user: Authenticated user
        db: Database session
        expense_id: Expense UUID
        data: Expense update data
        
    Returns:
        Updated expense with category details
        
    Raises:
        HTTPException 400: Invalid category
        HTTPException 404: Expense not found
    """
    service = ExpenseService(db)
    try:
        expense = await service.update_expense(expense_id, current_user.id, data)
        if expense is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Expense not found",
            )
        return expense
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.delete(
    "/{expense_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete expense",
    description="Delete an expense and its associated receipt.",
    responses={
        204: {"description": "Expense deleted successfully"},
        401: {"description": "Not authenticated"},
        404: {"description": "Expense not found"},
    },
)
async def delete_expense(
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
    expense_id: UUID,
) -> None:
    """Delete an expense.
    
    Validates: Requirements 10.6
    
    Args:
        current_user: Authenticated user
        db: Database session
        expense_id: Expense UUID
        
    Raises:
        HTTPException 404: Expense not found
    """
    service = ExpenseService(db)
    deleted = await service.delete_expense(expense_id, current_user.id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Expense not found",
        )


# ============================================================================
# Receipt Endpoints
# ============================================================================

@router.post(
    "/{expense_id}/receipt",
    response_model=ReceiptUploadResponse,
    status_code=status.HTTP_200_OK,
    summary="Upload receipt",
    description="Upload a receipt image for an expense. Supports JPEG, PNG, WebP, and PDF.",
    responses={
        200: {"description": "Receipt uploaded successfully"},
        400: {"description": "Invalid file type"},
        401: {"description": "Not authenticated"},
        404: {"description": "Expense not found"},
    },
)
async def upload_receipt(
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
    expense_id: UUID,
    file: Annotated[UploadFile, File(description="Receipt image file")],
) -> ReceiptUploadResponse:
    """Upload a receipt image for an expense.
    
    Args:
        current_user: Authenticated user
        db: Database session
        expense_id: Expense UUID
        file: Receipt image file
        
    Returns:
        Receipt upload response with URL
        
    Raises:
        HTTPException 400: Invalid file type
        HTTPException 404: Expense not found
    """
    service = ExpenseService(db)
    try:
        receipt_url, ocr_data = await service.upload_receipt(
            expense_id, current_user.id, file
        )
        return ReceiptUploadResponse(
            expense_id=expense_id,
            receipt_url=receipt_url,
            ocr_data=ocr_data,
        )
    except ValueError as e:
        if "not found" in str(e).lower():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=str(e),
            )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.get(
    "/{expense_id}/receipt",
    status_code=status.HTTP_200_OK,
    summary="Get receipt URL",
    description="Get a presigned URL for downloading the receipt image.",
    responses={
        200: {"description": "Receipt URL returned successfully"},
        401: {"description": "Not authenticated"},
        404: {"description": "Expense or receipt not found"},
    },
)
async def get_receipt_url(
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
    expense_id: UUID,
    expiry_seconds: Annotated[
        int,
        Query(ge=60, le=86400, description="URL validity period in seconds (1 min to 24 hours)")
    ] = 3600,
) -> dict:
    """Get a presigned URL for downloading the receipt.
    
    Args:
        current_user: Authenticated user
        db: Database session
        expense_id: Expense UUID
        expiry_seconds: URL validity period in seconds
        
    Returns:
        Dict with presigned URL
        
    Raises:
        HTTPException 404: Expense or receipt not found
    """
    service = ExpenseService(db)
    url = await service.get_receipt_url(expense_id, current_user.id, expiry_seconds)
    if url is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Expense or receipt not found",
        )
    return {"url": url, "expires_in": expiry_seconds}
