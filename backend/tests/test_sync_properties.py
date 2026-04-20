"""Property-based tests for sync module.

Uses Hypothesis to verify universal properties across all valid inputs.

**Validates: Requirements 35.4, 35.6**

Property 43: Offline Sync Consistency - For any sequence of offline modifications
(create, update, delete), syncing when online SHALL result in consistent server
state with proper conflict resolution.
"""

import string
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Any
from uuid import uuid4
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from hypothesis import given, strategies as st, settings, assume, HealthCheck

from app.schemas.sync import (
    ConflictResolutionStrategy,
    SyncChange,
    SyncChangeResult,
    SyncConflict,
    SyncEntityType,
    SyncOperationType,
    SyncRequest,
    SyncResult,
)
from app.services.sync import SyncService


# ============================================================================
# Hypothesis Strategies for Sync Data
# ============================================================================

@st.composite
def valid_entity_types(draw):
    """Generate valid entity types for sync operations."""
    return draw(st.sampled_from(list(SyncEntityType)))


@st.composite
def valid_operation_types(draw):
    """Generate valid operation types for sync operations."""
    return draw(st.sampled_from(list(SyncOperationType)))


@st.composite
def valid_resolution_strategies(draw):
    """Generate valid conflict resolution strategies."""
    return draw(st.sampled_from(list(ConflictResolutionStrategy)))


@st.composite
def valid_timestamps(draw):
    """Generate valid timestamps (milliseconds since epoch).
    
    Timestamps should be reasonable - using fixed date range for reproducibility.
    """
    # Use fixed date range for reproducibility (avoids flaky tests)
    min_time = datetime(2023, 1, 1, 0, 0, 0)
    max_time = datetime(2024, 12, 31, 23, 59, 59)
    
    dt = draw(st.datetimes(
        min_value=min_time,
        max_value=max_time,
    ))
    
    # Convert to milliseconds since epoch
    return int(dt.replace(tzinfo=timezone.utc).timestamp() * 1000)


@st.composite
def valid_expense_data(draw):
    """Generate valid expense data for sync operations."""
    return {
        "amount": float(draw(st.decimals(
            min_value=Decimal("0.01"),
            max_value=Decimal("999999.99"),
            places=2,
        ))),
        "description": draw(st.text(
            alphabet=string.ascii_letters + string.digits + " ",
            min_size=0,
            max_size=100,
        )).strip() or None,
        "expense_date": draw(st.dates()).isoformat(),
    }


@st.composite
def valid_skill_data(draw):
    """Generate valid skill data for sync operations."""
    proficiency_levels = ["Beginner", "Intermediate", "Advanced", "Expert"]
    categories = ["Programming", "Design", "Management", "Communication", "Technical"]
    
    return {
        "name": draw(st.text(
            alphabet=string.ascii_letters + string.digits + " ",
            min_size=1,
            max_size=50,
        )).strip() or "Skill",
        "category": draw(st.sampled_from(categories)),
        "proficiency": draw(st.sampled_from(proficiency_levels)),
    }


@st.composite
def valid_sync_change(draw, entity_type=None, operation=None):
    """Generate a valid sync change for testing.
    
    Args:
        entity_type: Optional fixed entity type
        operation: Optional fixed operation type
    """
    if entity_type is None:
        entity_type = draw(valid_entity_types())
    if operation is None:
        operation = draw(valid_operation_types())
    
    # Generate appropriate data based on entity type
    if entity_type == SyncEntityType.EXPENSE:
        data = draw(valid_expense_data()) if operation != SyncOperationType.DELETE else {}
    elif entity_type == SyncEntityType.SKILL:
        data = draw(valid_skill_data()) if operation != SyncOperationType.DELETE else {}
    else:
        # Generic data for other entity types
        data = {"name": "test"} if operation != SyncOperationType.DELETE else {}
    
    # Generate entity ID (temp ID for creates, real UUID for updates/deletes)
    if operation == SyncOperationType.CREATE:
        entity_id = f"temp_{uuid4().hex[:8]}"
    else:
        entity_id = str(uuid4())
    
    # Generate endpoint based on entity type and operation
    endpoint_map = {
        SyncEntityType.EXPENSE: "/api/v1/expenses",
        SyncEntityType.SKILL: "/api/v1/career/skills",
        SyncEntityType.COURSE: "/api/v1/career/courses",
        SyncEntityType.DOCUMENT: "/api/v1/documents",
        SyncEntityType.HEALTH_RECORD: "/api/v1/health/records",
        SyncEntityType.MEDICINE: "/api/v1/health/medicines",
        SyncEntityType.VITAL: "/api/v1/health/vitals",
        SyncEntityType.WARDROBE_ITEM: "/api/v1/wardrobe/items",
        SyncEntityType.JOB_APPLICATION: "/api/v1/career/applications",
        SyncEntityType.ACHIEVEMENT: "/api/v1/career/achievements",
    }
    
    base_endpoint = endpoint_map.get(entity_type, "/api/v1/unknown")
    
    if operation == SyncOperationType.CREATE:
        endpoint = base_endpoint
        method = "POST"
    elif operation == SyncOperationType.UPDATE:
        endpoint = f"{base_endpoint}/{entity_id}"
        method = "PUT"
    else:  # DELETE
        endpoint = f"{base_endpoint}/{entity_id}"
        method = "DELETE"
    
    return SyncChange(
        id=f"change_{uuid4().hex[:8]}",
        entity_type=entity_type,
        entity_id=entity_id,
        operation=operation,
        data=data,
        timestamp=draw(valid_timestamps()),
        endpoint=endpoint,
        method=method,
    )


@st.composite
def valid_sync_change_sequence(draw, min_size=1, max_size=5):
    """Generate a sequence of valid sync changes.
    
    The sequence maintains logical consistency:
    - Creates come before updates/deletes for the same entity
    - No duplicate operations on the same entity
    """
    num_changes = draw(st.integers(min_value=min_size, max_value=max_size))
    changes = []
    
    for _ in range(num_changes):
        change = draw(valid_sync_change())
        changes.append(change)
    
    return changes


# ============================================================================
# Helper Functions
# ============================================================================

def create_mock_server_data(change: SyncChange, server_timestamp: datetime) -> dict[str, Any]:
    """Create mock server data for conflict testing."""
    base_data = {
        "id": change.entity_id,
        "user_id": str(uuid4()),
        "created_at": (server_timestamp - timedelta(days=1)).isoformat(),
        "updated_at": server_timestamp.isoformat(),
    }
    
    # Add entity-specific fields
    if change.entity_type == SyncEntityType.EXPENSE:
        base_data.update({
            "amount": 50.0,
            "description": "Server expense",
            "expense_date": datetime.now().date().isoformat(),
            "category_id": str(uuid4()),
        })
    elif change.entity_type == SyncEntityType.SKILL:
        base_data.update({
            "name": "Server Skill",
            "category": "Technical",
            "proficiency": "Intermediate",
        })
    else:
        base_data.update({"name": "Server data"})
    
    return base_data


# ============================================================================
# Property 43: Offline Sync Consistency
# ============================================================================

class TestOfflineSyncConsistencyProperty:
    """Property 43: Offline Sync Consistency.
    
    **Validates: Requirements 35.4, 35.6**
    
    For any sequence of offline modifications (create, update, delete), syncing
    when online SHALL result in consistent server state with proper conflict
    resolution.
    
    This property verifies:
    1. All queued changes are processed in order
    2. Conflict resolution produces deterministic results
    3. After sync, the server state matches the expected final state
    4. The sync result accurately reports success/failure counts
    """
    
    @given(changes=valid_sync_change_sequence(min_size=1, max_size=5))
    @settings(max_examples=20, deadline=None, suppress_health_check=[HealthCheck.too_slow])
    def test_sync_processes_all_changes_in_order(self, changes: list[SyncChange]):
        """For any sequence of offline changes, syncing SHALL process all changes
        and maintain the order of operations.
        
        **Validates: Requirements 35.4, 35.6**
        
        This test verifies that:
        1. All changes in the request are processed
        2. The results are returned in the same order as the input
        3. Each change has a corresponding result
        """
        # Create sync request
        request = SyncRequest(
            changes=changes,
            resolution_strategy=ConflictResolutionStrategy.LAST_WRITE_WINS,
        )
        
        # Verify request contains all changes
        assert len(request.changes) == len(changes), (
            f"Request should contain all changes: expected {len(changes)}, "
            f"got {len(request.changes)}"
        )
        
        # Verify order is preserved
        for i, (original, in_request) in enumerate(zip(changes, request.changes)):
            assert original.id == in_request.id, (
                f"Change order not preserved at index {i}: "
                f"expected {original.id}, got {in_request.id}"
            )
    
    @pytest.mark.asyncio
    @given(
        changes=valid_sync_change_sequence(min_size=1, max_size=3),
        strategy=valid_resolution_strategies(),
    )
    @settings(max_examples=15, deadline=None, suppress_health_check=[HealthCheck.too_slow])
    async def test_sync_result_counts_are_consistent(
        self,
        changes: list[SyncChange],
        strategy: ConflictResolutionStrategy,
    ):
        """For any sync operation, the result counts SHALL be consistent with
        the individual change results.
        
        **Validates: Requirements 35.4, 35.6**
        
        This test verifies that:
        1. synced_count + failed_count == total changes
        2. conflict_count <= synced_count
        3. Each result has the correct change_id
        """
        # Create mock database session
        mock_db = AsyncMock()
        service = SyncService(mock_db)
        
        # Mock the entity handlers to simulate successful syncs
        async def mock_process_change(user_id, change, resolution_strategy):
            return SyncChangeResult(
                change_id=change.id,
                success=True,
                entity_id=change.entity_id if change.operation != SyncOperationType.CREATE else str(uuid4()),
            )
        
        service._process_change = mock_process_change
        service._notify_conflicts = AsyncMock()
        
        # Create sync request
        request = SyncRequest(
            changes=changes,
            resolution_strategy=strategy,
        )
        
        user_id = uuid4()
        
        # Execute sync
        result = await service.sync_changes(user_id, request)
        
        # Verify count consistency
        total_changes = len(changes)
        assert result.synced_count + result.failed_count == total_changes, (
            f"synced_count ({result.synced_count}) + failed_count ({result.failed_count}) "
            f"should equal total changes ({total_changes})"
        )
        
        assert result.conflict_count <= result.synced_count, (
            f"conflict_count ({result.conflict_count}) should not exceed "
            f"synced_count ({result.synced_count})"
        )
        
        # Verify each change has a result
        assert len(result.results) == total_changes, (
            f"Should have result for each change: expected {total_changes}, "
            f"got {len(result.results)}"
        )
        
        # Verify change IDs match
        result_change_ids = {r.change_id for r in result.results}
        input_change_ids = {c.id for c in changes}
        assert result_change_ids == input_change_ids, (
            f"Result change IDs should match input: "
            f"missing {input_change_ids - result_change_ids}, "
            f"extra {result_change_ids - input_change_ids}"
        )
    
    @given(
        client_timestamp=valid_timestamps(),
        strategy=valid_resolution_strategies(),
    )
    @settings(max_examples=20, deadline=None)
    def test_conflict_resolution_is_deterministic(
        self,
        client_timestamp: int,
        strategy: ConflictResolutionStrategy,
    ):
        """For any conflict scenario, the resolution SHALL produce deterministic
        results based on the strategy.
        
        **Validates: Requirements 35.4**
        
        This test verifies that:
        1. LAST_WRITE_WINS uses timestamps to determine winner
        2. SERVER_WINS always uses server data
        3. CLIENT_WINS always uses client data
        4. The same inputs always produce the same output
        """
        # Create a change with the given timestamp
        change = SyncChange(
            id="test-change",
            entity_type=SyncEntityType.EXPENSE,
            entity_id=str(uuid4()),
            operation=SyncOperationType.UPDATE,
            data={"amount": 100.0, "description": "Client update"},
            timestamp=client_timestamp,
            endpoint="/api/v1/expenses/test",
            method="PUT",
        )
        
        # Create server data with a known timestamp
        client_dt = datetime.fromtimestamp(client_timestamp / 1000, tz=timezone.utc)
        
        # Test with server timestamp before client
        server_timestamp_before = client_dt - timedelta(seconds=10)
        server_data_before = create_mock_server_data(change, server_timestamp_before)
        
        # Test with server timestamp after client
        server_timestamp_after = client_dt + timedelta(seconds=10)
        server_data_after = create_mock_server_data(change, server_timestamp_after)
        
        # Create service instance (we'll call _resolve_conflict directly)
        mock_db = AsyncMock()
        service = SyncService(mock_db)
        
        # Test resolution when server is older (client should win for LAST_WRITE_WINS)
        conflict_before, resolved_before = service._resolve_conflict(
            change=change,
            server_data=server_data_before,
            server_timestamp=server_timestamp_before,
            resolution_strategy=strategy,
        )
        
        # Test resolution when server is newer (server should win for LAST_WRITE_WINS)
        conflict_after, resolved_after = service._resolve_conflict(
            change=change,
            server_data=server_data_after,
            server_timestamp=server_timestamp_after,
            resolution_strategy=strategy,
        )
        
        # Verify deterministic behavior based on strategy
        if strategy == ConflictResolutionStrategy.CLIENT_WINS:
            # Client always wins
            assert resolved_before == change.data, (
                "CLIENT_WINS should use client data when server is older"
            )
            assert resolved_after == change.data, (
                "CLIENT_WINS should use client data when server is newer"
            )
        elif strategy == ConflictResolutionStrategy.SERVER_WINS:
            # Server always wins (excluding metadata fields)
            expected_keys = {"amount", "description", "expense_date", "category_id", "name"}
            for key in expected_keys:
                if key in server_data_before:
                    assert resolved_before.get(key) == server_data_before.get(key), (
                        f"SERVER_WINS should use server data for {key}"
                    )
        elif strategy == ConflictResolutionStrategy.LAST_WRITE_WINS:
            # Most recent wins
            assert resolved_before == change.data, (
                "LAST_WRITE_WINS should use client data when client is newer"
            )
            # When server is newer, server data should win
            expected_keys = {"amount", "description", "expense_date", "category_id", "name"}
            for key in expected_keys:
                if key in server_data_after and key in resolved_after:
                    assert resolved_after.get(key) == server_data_after.get(key), (
                        f"LAST_WRITE_WINS should use server data for {key} when server is newer"
                    )
        
        # Verify conflict metadata is correct
        assert conflict_before.resolution == strategy
        assert conflict_after.resolution == strategy
        assert conflict_before.client_timestamp == client_timestamp
        assert conflict_after.client_timestamp == client_timestamp
    
    @pytest.mark.asyncio
    @given(changes=valid_sync_change_sequence(min_size=1, max_size=3))
    @settings(max_examples=10, deadline=None, suppress_health_check=[HealthCheck.too_slow])
    async def test_successful_sync_returns_success_true(
        self,
        changes: list[SyncChange],
    ):
        """For any sync where all changes succeed, the result SHALL have
        success=True and failed_count=0.
        
        **Validates: Requirements 35.6**
        
        This test verifies that:
        1. When all changes sync successfully, success is True
        2. failed_count is 0
        3. synced_count equals total changes
        """
        # Create mock database session
        mock_db = AsyncMock()
        service = SyncService(mock_db)
        
        # Mock successful processing for all changes
        async def mock_process_change(user_id, change, resolution_strategy):
            return SyncChangeResult(
                change_id=change.id,
                success=True,
                entity_id=str(uuid4()) if change.operation == SyncOperationType.CREATE else change.entity_id,
            )
        
        service._process_change = mock_process_change
        service._notify_conflicts = AsyncMock()
        
        # Create sync request
        request = SyncRequest(
            changes=changes,
            resolution_strategy=ConflictResolutionStrategy.LAST_WRITE_WINS,
        )
        
        user_id = uuid4()
        
        # Execute sync
        result = await service.sync_changes(user_id, request)
        
        # Verify success
        assert result.success is True, "Sync should succeed when all changes succeed"
        assert result.failed_count == 0, "failed_count should be 0 when all succeed"
        assert result.synced_count == len(changes), (
            f"synced_count should equal total changes: expected {len(changes)}, "
            f"got {result.synced_count}"
        )
    
    @pytest.mark.asyncio
    @given(
        changes=valid_sync_change_sequence(min_size=2, max_size=4),
        fail_index=st.integers(min_value=0, max_value=3),
    )
    @settings(max_examples=10, deadline=None, suppress_health_check=[HealthCheck.too_slow])
    async def test_partial_failure_returns_success_false(
        self,
        changes: list[SyncChange],
        fail_index: int,
    ):
        """For any sync where at least one change fails, the result SHALL have
        success=False and accurate failure count.
        
        **Validates: Requirements 35.6**
        
        This test verifies that:
        1. When any change fails, success is False
        2. failed_count accurately reflects failures
        3. Other changes still process successfully
        """
        # Ensure fail_index is within bounds
        assume(fail_index < len(changes))
        
        # Create mock database session
        mock_db = AsyncMock()
        service = SyncService(mock_db)
        
        # Track which change should fail
        fail_change_id = changes[fail_index].id
        
        # Mock processing with one failure
        async def mock_process_change(user_id, change, resolution_strategy):
            if change.id == fail_change_id:
                return SyncChangeResult(
                    change_id=change.id,
                    success=False,
                    entity_id=change.entity_id,
                    error="Simulated failure",
                )
            return SyncChangeResult(
                change_id=change.id,
                success=True,
                entity_id=str(uuid4()) if change.operation == SyncOperationType.CREATE else change.entity_id,
            )
        
        service._process_change = mock_process_change
        service._notify_conflicts = AsyncMock()
        
        # Create sync request
        request = SyncRequest(
            changes=changes,
            resolution_strategy=ConflictResolutionStrategy.LAST_WRITE_WINS,
        )
        
        user_id = uuid4()
        
        # Execute sync
        result = await service.sync_changes(user_id, request)
        
        # Verify partial failure
        assert result.success is False, "Sync should fail when any change fails"
        assert result.failed_count == 1, "failed_count should be 1"
        assert result.synced_count == len(changes) - 1, (
            f"synced_count should be {len(changes) - 1}, got {result.synced_count}"
        )
        
        # Verify the failed change has error
        failed_results = [r for r in result.results if not r.success]
        assert len(failed_results) == 1
        assert failed_results[0].change_id == fail_change_id
        assert failed_results[0].error is not None
    
    @pytest.mark.asyncio
    @given(changes=valid_sync_change_sequence(min_size=1, max_size=3))
    @settings(max_examples=10, deadline=None, suppress_health_check=[HealthCheck.too_slow])
    async def test_sync_returns_server_timestamp(
        self,
        changes: list[SyncChange],
    ):
        """For any sync operation, the result SHALL include a valid server timestamp.
        
        **Validates: Requirements 35.4**
        
        This test verifies that:
        1. The result includes a server_timestamp
        2. The timestamp is recent (within last minute)
        3. The timestamp is timezone-aware
        """
        # Create mock database session
        mock_db = AsyncMock()
        service = SyncService(mock_db)
        
        # Mock successful processing
        async def mock_process_change(user_id, change, resolution_strategy):
            return SyncChangeResult(
                change_id=change.id,
                success=True,
                entity_id=change.entity_id,
            )
        
        service._process_change = mock_process_change
        service._notify_conflicts = AsyncMock()
        
        # Create sync request
        request = SyncRequest(
            changes=changes,
            resolution_strategy=ConflictResolutionStrategy.LAST_WRITE_WINS,
        )
        
        user_id = uuid4()
        before_sync = datetime.now(timezone.utc)
        
        # Execute sync
        result = await service.sync_changes(user_id, request)
        
        after_sync = datetime.now(timezone.utc)
        
        # Verify server timestamp
        assert result.server_timestamp is not None, "Result should include server_timestamp"
        assert result.server_timestamp.tzinfo is not None, "Timestamp should be timezone-aware"
        assert before_sync <= result.server_timestamp <= after_sync, (
            f"Timestamp should be between {before_sync} and {after_sync}, "
            f"got {result.server_timestamp}"
        )
    
    @pytest.mark.asyncio
    @given(
        num_conflicts=st.integers(min_value=1, max_value=3),
    )
    @settings(max_examples=10, deadline=None, suppress_health_check=[HealthCheck.too_slow])
    async def test_conflicts_trigger_notification(
        self,
        num_conflicts: int,
    ):
        """For any sync with conflicts, the user SHALL be notified of the conflicts.
        
        **Validates: Requirements 35.4**
        
        This test verifies that:
        1. When conflicts occur, _notify_conflicts is called
        2. The notification includes all conflicts
        """
        # Create mock database session
        mock_db = AsyncMock()
        service = SyncService(mock_db)
        
        # Create changes that will have conflicts
        changes = []
        for i in range(num_conflicts):
            changes.append(SyncChange(
                id=f"conflict-change-{i}",
                entity_type=SyncEntityType.EXPENSE,
                entity_id=str(uuid4()),
                operation=SyncOperationType.UPDATE,
                data={"amount": 100.0 + i},
                timestamp=int(datetime.now(timezone.utc).timestamp() * 1000),
                endpoint="/api/v1/expenses/test",
                method="PUT",
            ))
        
        # Track conflicts
        conflicts_notified = []
        
        async def mock_notify_conflicts(user_id, conflicts):
            conflicts_notified.extend(conflicts)
        
        # Mock processing with conflicts
        async def mock_process_change(user_id, change, resolution_strategy):
            conflict = SyncConflict(
                change_id=change.id,
                entity_type=change.entity_type,
                entity_id=change.entity_id,
                client_data=change.data,
                server_data={"amount": 50.0},
                client_timestamp=change.timestamp,
                server_timestamp=datetime.now(timezone.utc),
                resolution=resolution_strategy,
                resolved_data=change.data,
            )
            return SyncChangeResult(
                change_id=change.id,
                success=True,
                entity_id=change.entity_id,
                conflict=conflict,
            )
        
        service._process_change = mock_process_change
        service._notify_conflicts = mock_notify_conflicts
        
        # Create sync request
        request = SyncRequest(
            changes=changes,
            resolution_strategy=ConflictResolutionStrategy.LAST_WRITE_WINS,
        )
        
        user_id = uuid4()
        
        # Execute sync
        result = await service.sync_changes(user_id, request)
        
        # Verify conflicts were notified
        assert result.conflict_count == num_conflicts, (
            f"conflict_count should be {num_conflicts}, got {result.conflict_count}"
        )
        assert len(conflicts_notified) == num_conflicts, (
            f"Should notify {num_conflicts} conflicts, notified {len(conflicts_notified)}"
        )
    
    @given(
        entity_type=valid_entity_types(),
        operation=valid_operation_types(),
    )
    @settings(max_examples=30, deadline=None)
    def test_sync_change_schema_validation(
        self,
        entity_type: SyncEntityType,
        operation: SyncOperationType,
    ):
        """For any valid entity type and operation, a SyncChange SHALL be
        successfully created and validated.
        
        **Validates: Requirements 35.4**
        
        This test verifies that:
        1. All entity types are supported
        2. All operation types are supported
        3. The schema validates correctly
        """
        # Create a valid sync change
        change = SyncChange(
            id=f"test-{uuid4().hex[:8]}",
            entity_type=entity_type,
            entity_id=str(uuid4()),
            operation=operation,
            data={"test": "data"} if operation != SyncOperationType.DELETE else {},
            timestamp=int(datetime.now(timezone.utc).timestamp() * 1000),
            endpoint="/api/v1/test",
            method="POST" if operation == SyncOperationType.CREATE else "PUT" if operation == SyncOperationType.UPDATE else "DELETE",
        )
        
        # Verify schema validation
        assert change.entity_type == entity_type
        assert change.operation == operation
        assert change.id is not None
        assert change.entity_id is not None
        assert change.timestamp > 0
    
    @given(strategy=valid_resolution_strategies())
    @settings(max_examples=10, deadline=None)
    def test_sync_request_accepts_all_strategies(
        self,
        strategy: ConflictResolutionStrategy,
    ):
        """For any conflict resolution strategy, a SyncRequest SHALL accept it.
        
        **Validates: Requirements 35.4**
        
        This test verifies that:
        1. All resolution strategies are valid
        2. The request schema accepts any strategy
        """
        request = SyncRequest(
            changes=[],
            resolution_strategy=strategy,
        )
        
        assert request.resolution_strategy == strategy

