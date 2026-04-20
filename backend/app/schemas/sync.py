"""Pydantic schemas for sync module.

Includes schemas for offline sync operations and conflict resolution.

Validates: Requirements 35.4
"""

from datetime import datetime
from enum import Enum
from typing import Any, List, Optional
from uuid import UUID

from pydantic import BaseModel, Field


class SyncOperationType(str, Enum):
    """Type of sync operation."""
    CREATE = "create"
    UPDATE = "update"
    DELETE = "delete"


class SyncEntityType(str, Enum):
    """Entity types that can be synced."""
    EXPENSE = "expense"
    DOCUMENT = "document"
    HEALTH_RECORD = "health_record"
    MEDICINE = "medicine"
    VITAL = "vital"
    WARDROBE_ITEM = "wardrobe_item"
    SKILL = "skill"
    COURSE = "course"
    JOB_APPLICATION = "job_application"
    ACHIEVEMENT = "achievement"


class ConflictResolutionStrategy(str, Enum):
    """Strategy for resolving sync conflicts."""
    LAST_WRITE_WINS = "last_write_wins"
    SERVER_WINS = "server_wins"
    CLIENT_WINS = "client_wins"


class SyncChange(BaseModel):
    """A single change to be synced.
    
    Validates: Requirements 35.4
    """
    
    id: str = Field(..., description="Unique ID of the queued operation")
    entity_type: SyncEntityType = Field(..., description="Type of entity being synced")
    entity_id: str = Field(..., description="ID of the entity (may be temporary for creates)")
    operation: SyncOperationType = Field(..., description="Type of operation")
    data: dict[str, Any] = Field(default_factory=dict, description="Entity data for create/update")
    timestamp: int = Field(..., description="Client timestamp when change was made (ms since epoch)")
    endpoint: str = Field(..., description="API endpoint for the operation")
    method: str = Field(..., description="HTTP method (POST, PUT, PATCH, DELETE)")


class SyncConflict(BaseModel):
    """A sync conflict that occurred during synchronization.
    
    Validates: Requirements 35.4
    """
    
    change_id: str = Field(..., description="ID of the conflicting change")
    entity_type: SyncEntityType = Field(..., description="Type of entity")
    entity_id: str = Field(..., description="ID of the entity")
    client_data: dict[str, Any] = Field(..., description="Data from client")
    server_data: dict[str, Any] = Field(..., description="Current data on server")
    client_timestamp: int = Field(..., description="Client modification timestamp")
    server_timestamp: datetime = Field(..., description="Server modification timestamp")
    resolution: ConflictResolutionStrategy = Field(..., description="How the conflict was resolved")
    resolved_data: dict[str, Any] = Field(..., description="Final resolved data")


class SyncChangeResult(BaseModel):
    """Result of syncing a single change.
    
    Validates: Requirements 35.4
    """
    
    change_id: str = Field(..., description="ID of the synced change")
    success: bool = Field(..., description="Whether the sync was successful")
    entity_id: str = Field(..., description="Final entity ID (may differ from temp ID)")
    conflict: Optional[SyncConflict] = Field(None, description="Conflict details if one occurred")
    error: Optional[str] = Field(None, description="Error message if sync failed")


class SyncRequest(BaseModel):
    """Request to sync multiple changes.
    
    Validates: Requirements 35.4
    """
    
    changes: List[SyncChange] = Field(..., description="List of changes to sync")
    resolution_strategy: ConflictResolutionStrategy = Field(
        default=ConflictResolutionStrategy.LAST_WRITE_WINS,
        description="Strategy for resolving conflicts"
    )


class SyncResult(BaseModel):
    """Result of a sync operation.
    
    Validates: Requirements 35.4
    """
    
    success: bool = Field(..., description="Whether all changes synced successfully")
    synced_count: int = Field(..., description="Number of successfully synced changes")
    failed_count: int = Field(..., description="Number of failed changes")
    conflict_count: int = Field(..., description="Number of conflicts resolved")
    results: List[SyncChangeResult] = Field(..., description="Results for each change")
    server_timestamp: datetime = Field(..., description="Current server timestamp")


class PendingChange(BaseModel):
    """A pending change from the server.
    
    Validates: Requirements 35.4
    """
    
    entity_type: SyncEntityType = Field(..., description="Type of entity")
    entity_id: UUID = Field(..., description="ID of the entity")
    operation: SyncOperationType = Field(..., description="Type of operation")
    data: dict[str, Any] = Field(..., description="Entity data")
    timestamp: datetime = Field(..., description="Server timestamp of the change")


class PendingChangesResponse(BaseModel):
    """Response containing pending changes from server.
    
    Validates: Requirements 35.4
    """
    
    changes: List[PendingChange] = Field(..., description="List of pending changes")
    server_timestamp: datetime = Field(..., description="Current server timestamp")
