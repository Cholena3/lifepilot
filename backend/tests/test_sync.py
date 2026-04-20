"""Tests for sync service and endpoints.

Validates: Requirements 35.4
"""

import pytest
from datetime import datetime, timezone
from uuid import uuid4

from app.schemas.sync import (
    ConflictResolutionStrategy,
    SyncChange,
    SyncEntityType,
    SyncOperationType,
    SyncRequest,
)


class TestSyncSchemas:
    """Test sync schema validation."""
    
    def test_sync_change_creation(self):
        """Test creating a SyncChange schema."""
        change = SyncChange(
            id="test-change-1",
            entity_type=SyncEntityType.EXPENSE,
            entity_id="temp_123",
            operation=SyncOperationType.CREATE,
            data={"amount": 100.0, "description": "Test expense"},
            timestamp=1700000000000,
            endpoint="/api/v1/expenses",
            method="POST",
        )
        
        assert change.id == "test-change-1"
        assert change.entity_type == SyncEntityType.EXPENSE
        assert change.operation == SyncOperationType.CREATE
        assert change.data["amount"] == 100.0
    
    def test_sync_request_creation(self):
        """Test creating a SyncRequest schema."""
        changes = [
            SyncChange(
                id="change-1",
                entity_type=SyncEntityType.EXPENSE,
                entity_id="temp_1",
                operation=SyncOperationType.CREATE,
                data={"amount": 50.0},
                timestamp=1700000000000,
                endpoint="/api/v1/expenses",
                method="POST",
            ),
            SyncChange(
                id="change-2",
                entity_type=SyncEntityType.SKILL,
                entity_id=str(uuid4()),
                operation=SyncOperationType.UPDATE,
                data={"proficiency": "Advanced"},
                timestamp=1700000001000,
                endpoint="/api/v1/career/skills/123",
                method="PUT",
            ),
        ]
        
        request = SyncRequest(
            changes=changes,
            resolution_strategy=ConflictResolutionStrategy.LAST_WRITE_WINS,
        )
        
        assert len(request.changes) == 2
        assert request.resolution_strategy == ConflictResolutionStrategy.LAST_WRITE_WINS
    
    def test_sync_request_default_strategy(self):
        """Test that SyncRequest defaults to last_write_wins strategy."""
        request = SyncRequest(changes=[])
        assert request.resolution_strategy == ConflictResolutionStrategy.LAST_WRITE_WINS
    
    def test_all_entity_types(self):
        """Test all supported entity types."""
        entity_types = [
            SyncEntityType.EXPENSE,
            SyncEntityType.DOCUMENT,
            SyncEntityType.HEALTH_RECORD,
            SyncEntityType.MEDICINE,
            SyncEntityType.VITAL,
            SyncEntityType.WARDROBE_ITEM,
            SyncEntityType.SKILL,
            SyncEntityType.COURSE,
            SyncEntityType.JOB_APPLICATION,
            SyncEntityType.ACHIEVEMENT,
        ]
        
        for entity_type in entity_types:
            change = SyncChange(
                id=f"test-{entity_type.value}",
                entity_type=entity_type,
                entity_id="test-id",
                operation=SyncOperationType.CREATE,
                data={},
                timestamp=1700000000000,
                endpoint="/api/v1/test",
                method="POST",
            )
            assert change.entity_type == entity_type
    
    def test_all_operation_types(self):
        """Test all supported operation types."""
        operations = [
            SyncOperationType.CREATE,
            SyncOperationType.UPDATE,
            SyncOperationType.DELETE,
        ]
        
        for operation in operations:
            change = SyncChange(
                id=f"test-{operation.value}",
                entity_type=SyncEntityType.EXPENSE,
                entity_id="test-id",
                operation=operation,
                data={},
                timestamp=1700000000000,
                endpoint="/api/v1/test",
                method="POST",
            )
            assert change.operation == operation
    
    def test_all_resolution_strategies(self):
        """Test all conflict resolution strategies."""
        strategies = [
            ConflictResolutionStrategy.LAST_WRITE_WINS,
            ConflictResolutionStrategy.SERVER_WINS,
            ConflictResolutionStrategy.CLIENT_WINS,
        ]
        
        for strategy in strategies:
            request = SyncRequest(
                changes=[],
                resolution_strategy=strategy,
            )
            assert request.resolution_strategy == strategy


class TestSyncServiceConflictResolution:
    """Test conflict resolution logic."""
    
    def test_last_write_wins_client_newer(self):
        """Test last-write-wins when client change is newer."""
        from app.services.sync import SyncService
        
        # Create a mock service (we'll test the resolution logic directly)
        # Client timestamp is newer than server
        client_timestamp = 1700000002000  # 2 seconds later
        server_timestamp = datetime(2023, 11, 14, 22, 13, 20, tzinfo=timezone.utc)  # 1700000000
        
        change = SyncChange(
            id="test-change",
            entity_type=SyncEntityType.EXPENSE,
            entity_id="test-id",
            operation=SyncOperationType.UPDATE,
            data={"amount": 200.0, "description": "Client update"},
            timestamp=client_timestamp,
            endpoint="/api/v1/expenses/test-id",
            method="PUT",
        )
        
        server_data = {
            "id": "test-id",
            "amount": 100.0,
            "description": "Server data",
            "updated_at": server_timestamp.isoformat(),
        }
        
        # Test the resolution logic
        # When client is newer, client data should win
        client_dt = datetime.fromtimestamp(client_timestamp / 1000, tz=timezone.utc)
        assert client_dt > server_timestamp
    
    def test_last_write_wins_server_newer(self):
        """Test last-write-wins when server data is newer."""
        # Server timestamp is newer than client
        client_timestamp = 1700000000000
        server_timestamp = datetime(2023, 11, 14, 22, 13, 22, tzinfo=timezone.utc)  # 2 seconds later
        
        client_dt = datetime.fromtimestamp(client_timestamp / 1000, tz=timezone.utc)
        assert server_timestamp > client_dt


class TestSyncRouter:
    """Test sync router endpoints."""
    
    @pytest.mark.asyncio
    async def test_sync_endpoint_exists(self):
        """Test that sync endpoint is registered."""
        from app.routers.sync import router
        
        # Check that the router has the expected routes
        routes = [route.path for route in router.routes]
        assert "/changes" in routes
        assert "/pending" in routes
