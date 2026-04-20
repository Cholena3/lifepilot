"""Sync router for offline data synchronization endpoints.

Provides endpoints for syncing offline changes and retrieving pending changes.

Validates: Requirements 35.4
"""

from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import CurrentUser
from app.schemas.sync import (
    PendingChangesResponse,
    SyncRequest,
    SyncResult,
)
from app.services.sync import SyncService

router = APIRouter()


@router.post(
    "/changes",
    response_model=SyncResult,
    status_code=status.HTTP_200_OK,
    summary="Sync offline changes",
    description="Synchronize queued offline changes with the server. "
                "Implements last-write-wins conflict resolution and notifies users of conflicts.",
    responses={
        200: {"description": "Sync completed (may include partial failures)"},
        401: {"description": "Not authenticated"},
        422: {"description": "Validation error"},
    },
)
async def sync_changes(
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
    request: SyncRequest,
) -> SyncResult:
    """Sync offline changes to the server.
    
    Validates: Requirements 35.4
    
    This endpoint processes queued changes made while offline:
    - Creates new entities
    - Updates existing entities with conflict detection
    - Deletes entities
    
    Conflicts are resolved using the specified strategy (default: last-write-wins).
    Users are notified of any conflicts that occurred.
    
    Args:
        current_user: Authenticated user
        db: Database session
        request: Sync request with changes and resolution strategy
        
    Returns:
        SyncResult with details of each synced change
    """
    service = SyncService(db)
    return await service.sync_changes(current_user.id, request)


@router.get(
    "/pending",
    response_model=PendingChangesResponse,
    status_code=status.HTTP_200_OK,
    summary="Get pending server changes",
    description="Get changes from the server since a given timestamp. "
                "Used to sync server changes to the client after reconnecting.",
    responses={
        200: {"description": "Pending changes returned successfully"},
        401: {"description": "Not authenticated"},
        422: {"description": "Validation error"},
    },
)
async def get_pending_changes(
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
    since: Annotated[
        datetime,
        Query(description="Get changes after this timestamp (ISO 8601 format)")
    ],
) -> PendingChangesResponse:
    """Get pending changes from the server.
    
    Validates: Requirements 35.4
    
    Returns all changes made on the server since the given timestamp.
    This allows the client to sync server-side changes after reconnecting.
    
    Args:
        current_user: Authenticated user
        db: Database session
        since: Get changes after this timestamp
        
    Returns:
        PendingChangesResponse with list of changes
    """
    service = SyncService(db)
    return await service.get_pending_changes(current_user.id, since)
