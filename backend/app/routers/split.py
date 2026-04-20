"""Split router for Bill Splitting module endpoints.

Provides endpoints for split groups, members, shared expenses, and settlements.

Validates: Requirements 13.1, 13.2, 13.3, 13.4, 13.5, 13.6, 13.7
"""

from typing import Annotated, List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import CurrentUser
from app.schemas.document import PaginatedResponse
from app.schemas.split import (
    SplitGroupCreate,
    SplitGroupUpdate,
    SplitGroupResponse,
    SplitGroupWithMembersResponse,
    SplitGroupMemberCreate,
    SplitGroupMemberResponse,
    SharedExpenseCreate,
    SharedExpenseResponse,
    SettlementCreate,
    SettlementResponse,
    GroupBalancesResponse,
    SimplifiedDebtsResponse,
)
from app.services.split import SplitService

router = APIRouter()


# ============================================================================
# Split Group Endpoints
# ============================================================================

@router.post(
    "/groups",
    response_model=SplitGroupWithMembersResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create split group",
    description="Create a new split group for sharing expenses.",
    responses={
        201: {"description": "Group created successfully"},
        401: {"description": "Not authenticated"},
        422: {"description": "Validation error"},
    },
)
async def create_group(
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
    data: SplitGroupCreate,
) -> SplitGroupWithMembersResponse:
    """Create a new split group.
    
    Validates: Requirements 13.1
    
    Args:
        current_user: Authenticated user
        db: Database session
        data: Group creation data
        
    Returns:
        Created group with members
    """
    service = SplitService(db)
    return await service.create_group(current_user.id, data)


@router.get(
    "/groups",
    response_model=PaginatedResponse[SplitGroupWithMembersResponse],
    status_code=status.HTTP_200_OK,
    summary="List split groups",
    description="Get all split groups the user is a member of or created.",
    responses={
        200: {"description": "Groups returned successfully"},
        401: {"description": "Not authenticated"},
    },
)
async def list_groups(
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
    page: Annotated[
        int,
        Query(ge=1, description="Page number (1-indexed)")
    ] = 1,
    page_size: Annotated[
        int,
        Query(ge=1, le=100, description="Number of results per page")
    ] = 20,
) -> PaginatedResponse[SplitGroupWithMembersResponse]:
    """Get all split groups for the user.
    
    Validates: Requirements 13.1
    
    Args:
        current_user: Authenticated user
        db: Database session
        page: Page number (1-indexed)
        page_size: Number of results per page
        
    Returns:
        Paginated list of groups
    """
    service = SplitService(db)
    return await service.get_groups(current_user.id, page, page_size)


@router.get(
    "/groups/{group_id}",
    response_model=SplitGroupWithMembersResponse,
    status_code=status.HTTP_200_OK,
    summary="Get split group",
    description="Get a specific split group by ID with all members.",
    responses={
        200: {"description": "Group returned successfully"},
        401: {"description": "Not authenticated"},
        404: {"description": "Group not found"},
    },
)
async def get_group(
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
    group_id: UUID,
) -> SplitGroupWithMembersResponse:
    """Get a split group by ID.
    
    Args:
        current_user: Authenticated user
        db: Database session
        group_id: Group UUID
        
    Returns:
        Group details with members
        
    Raises:
        HTTPException 404: Group not found
    """
    service = SplitService(db)
    group = await service.get_group(group_id, current_user.id)
    if group is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Group not found",
        )
    return group


@router.put(
    "/groups/{group_id}",
    response_model=SplitGroupWithMembersResponse,
    status_code=status.HTTP_200_OK,
    summary="Update split group",
    description="Update a split group. Only the creator can update.",
    responses={
        200: {"description": "Group updated successfully"},
        400: {"description": "Not authorized to update"},
        401: {"description": "Not authenticated"},
        404: {"description": "Group not found"},
        422: {"description": "Validation error"},
    },
)
async def update_group(
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
    group_id: UUID,
    data: SplitGroupUpdate,
) -> SplitGroupWithMembersResponse:
    """Update a split group.
    
    Args:
        current_user: Authenticated user
        db: Database session
        group_id: Group UUID
        data: Group update data
        
    Returns:
        Updated group
        
    Raises:
        HTTPException 400: Not authorized
        HTTPException 404: Group not found
    """
    service = SplitService(db)
    try:
        group = await service.update_group(group_id, current_user.id, data)
        if group is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Group not found",
            )
        return group
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.delete(
    "/groups/{group_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete split group",
    description="Delete a split group. Only the creator can delete.",
    responses={
        204: {"description": "Group deleted successfully"},
        400: {"description": "Not authorized to delete"},
        401: {"description": "Not authenticated"},
        404: {"description": "Group not found"},
    },
)
async def delete_group(
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
    group_id: UUID,
) -> None:
    """Delete a split group.
    
    Args:
        current_user: Authenticated user
        db: Database session
        group_id: Group UUID
        
    Raises:
        HTTPException 400: Not authorized
        HTTPException 404: Group not found
    """
    service = SplitService(db)
    try:
        deleted = await service.delete_group(group_id, current_user.id)
        if not deleted:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Group not found",
            )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


# ============================================================================
# Member Endpoints
# ============================================================================

@router.post(
    "/groups/{group_id}/members",
    response_model=SplitGroupMemberResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Add member to group",
    description="Add a new member to a split group.",
    responses={
        201: {"description": "Member added successfully"},
        400: {"description": "Group not found or not accessible"},
        401: {"description": "Not authenticated"},
        422: {"description": "Validation error"},
    },
)
async def add_member(
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
    group_id: UUID,
    data: SplitGroupMemberCreate,
) -> SplitGroupMemberResponse:
    """Add a member to a split group.
    
    Validates: Requirements 13.1
    
    Args:
        current_user: Authenticated user
        db: Database session
        group_id: Group UUID
        data: Member creation data
        
    Returns:
        Created member
        
    Raises:
        HTTPException 400: Group not found or not accessible
    """
    service = SplitService(db)
    try:
        return await service.add_member(group_id, current_user.id, data)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.delete(
    "/groups/{group_id}/members/{member_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Remove member from group",
    description="Remove a member from a split group. Cannot remove members with expenses.",
    responses={
        204: {"description": "Member removed successfully"},
        400: {"description": "Cannot remove member with expenses"},
        401: {"description": "Not authenticated"},
        404: {"description": "Member not found"},
    },
)
async def remove_member(
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
    group_id: UUID,
    member_id: UUID,
) -> None:
    """Remove a member from a split group.
    
    Args:
        current_user: Authenticated user
        db: Database session
        group_id: Group UUID
        member_id: Member UUID
        
    Raises:
        HTTPException 400: Cannot remove member with expenses
        HTTPException 404: Member not found
    """
    service = SplitService(db)
    try:
        removed = await service.remove_member(group_id, member_id, current_user.id)
        if not removed:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Member not found",
            )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


# ============================================================================
# Shared Expense Endpoints
# ============================================================================

@router.post(
    "/groups/{group_id}/expenses",
    response_model=SharedExpenseResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Add shared expense",
    description="Add a shared expense to a group with automatic split calculation.",
    responses={
        201: {"description": "Expense added successfully"},
        400: {"description": "Invalid expense data"},
        401: {"description": "Not authenticated"},
        422: {"description": "Validation error"},
    },
)
async def add_expense(
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
    group_id: UUID,
    data: SharedExpenseCreate,
) -> SharedExpenseResponse:
    """Add a shared expense to a group.
    
    Validates: Requirements 13.2, 13.3
    
    Supports three split types:
    - equal: Divides amount equally among all members
    - percentage: Divides by specified percentages (must sum to 100%)
    - exact: Uses specified amounts (must sum to total)
    
    Args:
        current_user: Authenticated user
        db: Database session
        group_id: Group UUID
        data: Expense creation data
        
    Returns:
        Created expense with splits
        
    Raises:
        HTTPException 400: Invalid expense data
    """
    service = SplitService(db)
    try:
        return await service.add_expense(group_id, current_user.id, data)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.get(
    "/groups/{group_id}/expenses",
    response_model=PaginatedResponse[SharedExpenseResponse],
    status_code=status.HTTP_200_OK,
    summary="List group expenses",
    description="Get all shared expenses for a group.",
    responses={
        200: {"description": "Expenses returned successfully"},
        400: {"description": "Group not found or not accessible"},
        401: {"description": "Not authenticated"},
    },
)
async def list_expenses(
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
    group_id: UUID,
    page: Annotated[
        int,
        Query(ge=1, description="Page number (1-indexed)")
    ] = 1,
    page_size: Annotated[
        int,
        Query(ge=1, le=100, description="Number of results per page")
    ] = 20,
) -> PaginatedResponse[SharedExpenseResponse]:
    """Get all shared expenses for a group.
    
    Args:
        current_user: Authenticated user
        db: Database session
        group_id: Group UUID
        page: Page number (1-indexed)
        page_size: Number of results per page
        
    Returns:
        Paginated list of expenses
        
    Raises:
        HTTPException 400: Group not found or not accessible
    """
    service = SplitService(db)
    try:
        return await service.get_expenses(group_id, current_user.id, page, page_size)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.delete(
    "/groups/{group_id}/expenses/{expense_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete shared expense",
    description="Delete a shared expense from a group.",
    responses={
        204: {"description": "Expense deleted successfully"},
        400: {"description": "Group not found or not accessible"},
        401: {"description": "Not authenticated"},
        404: {"description": "Expense not found"},
    },
)
async def delete_expense(
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
    group_id: UUID,
    expense_id: UUID,
) -> None:
    """Delete a shared expense.
    
    Args:
        current_user: Authenticated user
        db: Database session
        group_id: Group UUID
        expense_id: Expense UUID
        
    Raises:
        HTTPException 400: Group not found or not accessible
        HTTPException 404: Expense not found
    """
    service = SplitService(db)
    try:
        deleted = await service.delete_expense(group_id, expense_id, current_user.id)
        if not deleted:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Expense not found",
            )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


# ============================================================================
# Balance Endpoints
# ============================================================================

@router.get(
    "/groups/{group_id}/balances",
    response_model=GroupBalancesResponse,
    status_code=status.HTTP_200_OK,
    summary="Get group balances",
    description="Get member balances showing who owes whom in the group.",
    responses={
        200: {"description": "Balances returned successfully"},
        400: {"description": "Group not found or not accessible"},
        401: {"description": "Not authenticated"},
    },
)
async def get_balances(
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
    group_id: UUID,
) -> GroupBalancesResponse:
    """Get member balances for a group.
    
    Validates: Requirements 13.7
    
    Returns net balance for each member:
    - Positive balance: Others owe this member money
    - Negative balance: This member owes others money
    
    Args:
        current_user: Authenticated user
        db: Database session
        group_id: Group UUID
        
    Returns:
        Group balances with member details
        
    Raises:
        HTTPException 400: Group not found or not accessible
    """
    service = SplitService(db)
    try:
        return await service.get_balances(group_id, current_user.id)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.get(
    "/groups/{group_id}/simplified-debts",
    response_model=SimplifiedDebtsResponse,
    status_code=status.HTTP_200_OK,
    summary="Get simplified debts",
    description="Get simplified debt transactions that minimize the number of payments needed to settle all debts.",
    responses={
        200: {"description": "Simplified debts returned successfully"},
        400: {"description": "Group not found or not accessible"},
        401: {"description": "Not authenticated"},
    },
)
async def get_simplified_debts(
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
    group_id: UUID,
) -> SimplifiedDebtsResponse:
    """Get simplified debts for a group.
    
    Validates: Requirements 13.4, 13.6
    
    Returns optimized settlement transactions that minimize the number of
    payments needed to settle all debts in the group. Each transaction
    includes a UPI deep link for easy payment.
    
    Args:
        current_user: Authenticated user
        db: Database session
        group_id: Group UUID
        
    Returns:
        Simplified debts with UPI payment links
        
    Raises:
        HTTPException 400: Group not found or not accessible
    """
    service = SplitService(db)
    try:
        return await service.simplify_debts(group_id, current_user.id)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


# ============================================================================
# Settlement Endpoints
# ============================================================================

@router.post(
    "/groups/{group_id}/settlements",
    response_model=SettlementResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create settlement",
    description="Record a settlement payment between two members.",
    responses={
        201: {"description": "Settlement created successfully"},
        400: {"description": "Invalid settlement data"},
        401: {"description": "Not authenticated"},
        422: {"description": "Validation error"},
    },
)
async def create_settlement(
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
    group_id: UUID,
    data: SettlementCreate,
) -> SettlementResponse:
    """Create a settlement between members.
    
    Validates: Requirements 13.5
    
    Args:
        current_user: Authenticated user
        db: Database session
        group_id: Group UUID
        data: Settlement creation data
        
    Returns:
        Created settlement
        
    Raises:
        HTTPException 400: Invalid settlement data
    """
    service = SplitService(db)
    try:
        return await service.create_settlement(group_id, current_user.id, data)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.get(
    "/groups/{group_id}/settlements",
    response_model=PaginatedResponse[SettlementResponse],
    status_code=status.HTTP_200_OK,
    summary="List settlements",
    description="Get all settlements for a group.",
    responses={
        200: {"description": "Settlements returned successfully"},
        400: {"description": "Group not found or not accessible"},
        401: {"description": "Not authenticated"},
    },
)
async def list_settlements(
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
    group_id: UUID,
    page: Annotated[
        int,
        Query(ge=1, description="Page number (1-indexed)")
    ] = 1,
    page_size: Annotated[
        int,
        Query(ge=1, le=100, description="Number of results per page")
    ] = 20,
) -> PaginatedResponse[SettlementResponse]:
    """Get all settlements for a group.
    
    Args:
        current_user: Authenticated user
        db: Database session
        group_id: Group UUID
        page: Page number (1-indexed)
        page_size: Number of results per page
        
    Returns:
        Paginated list of settlements
        
    Raises:
        HTTPException 400: Group not found or not accessible
    """
    service = SplitService(db)
    try:
        return await service.get_settlements(group_id, current_user.id, page, page_size)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
