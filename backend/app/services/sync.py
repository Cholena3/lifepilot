"""Sync service for offline data synchronization with conflict resolution.

Validates: Requirements 35.4
"""

import logging
from datetime import datetime, timezone
from typing import Any, Optional
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.notification import NotificationChannel
from app.schemas.sync import (
    ConflictResolutionStrategy,
    PendingChange,
    PendingChangesResponse,
    SyncChange,
    SyncChangeResult,
    SyncConflict,
    SyncEntityType,
    SyncOperationType,
    SyncRequest,
    SyncResult,
)
from app.services.notification import NotificationService

logger = logging.getLogger(__name__)


class SyncService:
    """Service for synchronizing offline changes with conflict resolution.
    
    Validates: Requirements 35.4
    
    Implements:
    - sync_changes: Sync queued changes when online
    - Last-write-wins conflict resolution
    - User notification for sync conflicts
    """
    
    def __init__(self, db: AsyncSession) -> None:
        """Initialize the sync service.
        
        Args:
            db: Async database session
        """
        self.db = db
        self.notification_service = NotificationService(db)
    
    async def sync_changes(
        self,
        user_id: UUID,
        request: SyncRequest,
    ) -> SyncResult:
        """Synchronize queued changes from client.
        
        Validates: Requirements 35.4
        
        Args:
            user_id: User's UUID
            request: Sync request with changes and resolution strategy
            
        Returns:
            SyncResult with details of each synced change
        """
        results: list[SyncChangeResult] = []
        synced_count = 0
        failed_count = 0
        conflict_count = 0
        conflicts_to_notify: list[SyncConflict] = []
        
        for change in request.changes:
            try:
                result = await self._process_change(
                    user_id=user_id,
                    change=change,
                    resolution_strategy=request.resolution_strategy,
                )
                results.append(result)
                
                if result.success:
                    synced_count += 1
                    if result.conflict:
                        conflict_count += 1
                        conflicts_to_notify.append(result.conflict)
                else:
                    failed_count += 1
                    
            except Exception as e:
                logger.exception(f"Error processing sync change {change.id}: {e}")
                results.append(SyncChangeResult(
                    change_id=change.id,
                    success=False,
                    entity_id=change.entity_id,
                    error=str(e),
                ))
                failed_count += 1
        
        # Notify user of conflicts if any
        if conflicts_to_notify:
            await self._notify_conflicts(user_id, conflicts_to_notify)
        
        logger.info(
            f"Sync completed for user {user_id}: "
            f"{synced_count} synced, {failed_count} failed, {conflict_count} conflicts"
        )
        
        return SyncResult(
            success=failed_count == 0,
            synced_count=synced_count,
            failed_count=failed_count,
            conflict_count=conflict_count,
            results=results,
            server_timestamp=datetime.now(timezone.utc),
        )
    
    async def _process_change(
        self,
        user_id: UUID,
        change: SyncChange,
        resolution_strategy: ConflictResolutionStrategy,
    ) -> SyncChangeResult:
        """Process a single sync change.
        
        Args:
            user_id: User's UUID
            change: The change to process
            resolution_strategy: Strategy for resolving conflicts
            
        Returns:
            SyncChangeResult with details of the sync
        """
        # Get the appropriate handler for the entity type
        handler = self._get_entity_handler(change.entity_type)
        
        if change.operation == SyncOperationType.CREATE:
            return await self._handle_create(user_id, change, handler)
        elif change.operation == SyncOperationType.UPDATE:
            return await self._handle_update(user_id, change, handler, resolution_strategy)
        elif change.operation == SyncOperationType.DELETE:
            return await self._handle_delete(user_id, change, handler)
        else:
            return SyncChangeResult(
                change_id=change.id,
                success=False,
                entity_id=change.entity_id,
                error=f"Unknown operation: {change.operation}",
            )
    
    async def _handle_create(
        self,
        user_id: UUID,
        change: SyncChange,
        handler: "EntitySyncHandler",
    ) -> SyncChangeResult:
        """Handle a create operation.
        
        Args:
            user_id: User's UUID
            change: The create change
            handler: Entity-specific handler
            
        Returns:
            SyncChangeResult
        """
        try:
            # Create the entity
            new_entity_id = await handler.create(user_id, change.data)
            
            logger.info(
                f"Created {change.entity_type.value} for user {user_id}: "
                f"temp_id={change.entity_id} -> id={new_entity_id}"
            )
            
            return SyncChangeResult(
                change_id=change.id,
                success=True,
                entity_id=str(new_entity_id),
            )
        except Exception as e:
            logger.error(f"Failed to create {change.entity_type.value}: {e}")
            return SyncChangeResult(
                change_id=change.id,
                success=False,
                entity_id=change.entity_id,
                error=str(e),
            )
    
    async def _handle_update(
        self,
        user_id: UUID,
        change: SyncChange,
        handler: "EntitySyncHandler",
        resolution_strategy: ConflictResolutionStrategy,
    ) -> SyncChangeResult:
        """Handle an update operation with conflict detection.
        
        Args:
            user_id: User's UUID
            change: The update change
            handler: Entity-specific handler
            resolution_strategy: Strategy for resolving conflicts
            
        Returns:
            SyncChangeResult with conflict details if applicable
        """
        try:
            # Get current server state
            entity_id = UUID(change.entity_id)
            server_data = await handler.get(user_id, entity_id)
            
            if server_data is None:
                return SyncChangeResult(
                    change_id=change.id,
                    success=False,
                    entity_id=change.entity_id,
                    error="Entity not found on server",
                )
            
            # Check for conflict
            server_timestamp = server_data.get("updated_at")
            if server_timestamp:
                # Convert client timestamp (ms) to datetime
                client_dt = datetime.fromtimestamp(change.timestamp / 1000, tz=timezone.utc)
                
                # Parse server timestamp if it's a string
                if isinstance(server_timestamp, str):
                    server_dt = datetime.fromisoformat(server_timestamp.replace("Z", "+00:00"))
                else:
                    server_dt = server_timestamp
                
                # Ensure server_dt is timezone-aware
                if server_dt.tzinfo is None:
                    server_dt = server_dt.replace(tzinfo=timezone.utc)
                
                # Conflict if server was modified after client change
                if server_dt > client_dt:
                    # Resolve conflict
                    conflict, resolved_data = self._resolve_conflict(
                        change=change,
                        server_data=server_data,
                        server_timestamp=server_dt,
                        resolution_strategy=resolution_strategy,
                    )
                    
                    # Apply resolved data
                    await handler.update(user_id, entity_id, resolved_data)
                    
                    logger.info(
                        f"Resolved conflict for {change.entity_type.value} {entity_id} "
                        f"using {resolution_strategy.value}"
                    )
                    
                    return SyncChangeResult(
                        change_id=change.id,
                        success=True,
                        entity_id=change.entity_id,
                        conflict=conflict,
                    )
            
            # No conflict, apply update directly
            await handler.update(user_id, entity_id, change.data)
            
            logger.info(f"Updated {change.entity_type.value} {entity_id} for user {user_id}")
            
            return SyncChangeResult(
                change_id=change.id,
                success=True,
                entity_id=change.entity_id,
            )
            
        except Exception as e:
            logger.error(f"Failed to update {change.entity_type.value}: {e}")
            return SyncChangeResult(
                change_id=change.id,
                success=False,
                entity_id=change.entity_id,
                error=str(e),
            )
    
    async def _handle_delete(
        self,
        user_id: UUID,
        change: SyncChange,
        handler: "EntitySyncHandler",
    ) -> SyncChangeResult:
        """Handle a delete operation.
        
        Args:
            user_id: User's UUID
            change: The delete change
            handler: Entity-specific handler
            
        Returns:
            SyncChangeResult
        """
        try:
            entity_id = UUID(change.entity_id)
            deleted = await handler.delete(user_id, entity_id)
            
            if deleted:
                logger.info(f"Deleted {change.entity_type.value} {entity_id} for user {user_id}")
            else:
                logger.info(f"{change.entity_type.value} {entity_id} already deleted or not found")
            
            # Consider delete successful even if entity was already gone
            return SyncChangeResult(
                change_id=change.id,
                success=True,
                entity_id=change.entity_id,
            )
            
        except Exception as e:
            logger.error(f"Failed to delete {change.entity_type.value}: {e}")
            return SyncChangeResult(
                change_id=change.id,
                success=False,
                entity_id=change.entity_id,
                error=str(e),
            )
    
    def _resolve_conflict(
        self,
        change: SyncChange,
        server_data: dict[str, Any],
        server_timestamp: datetime,
        resolution_strategy: ConflictResolutionStrategy,
    ) -> tuple[SyncConflict, dict[str, Any]]:
        """Resolve a sync conflict using the specified strategy.
        
        Validates: Requirements 35.4 - Last-write-wins conflict resolution
        
        Args:
            change: The client change
            server_data: Current server data
            server_timestamp: Server modification timestamp
            resolution_strategy: Strategy to use
            
        Returns:
            Tuple of (SyncConflict, resolved_data)
        """
        client_dt = datetime.fromtimestamp(change.timestamp / 1000, tz=timezone.utc)
        
        if resolution_strategy == ConflictResolutionStrategy.LAST_WRITE_WINS:
            # Compare timestamps - most recent wins
            if client_dt > server_timestamp:
                resolved_data = change.data
            else:
                resolved_data = {k: v for k, v in server_data.items() 
                               if k not in ("id", "user_id", "created_at", "updated_at")}
        elif resolution_strategy == ConflictResolutionStrategy.SERVER_WINS:
            resolved_data = {k: v for k, v in server_data.items() 
                           if k not in ("id", "user_id", "created_at", "updated_at")}
        elif resolution_strategy == ConflictResolutionStrategy.CLIENT_WINS:
            resolved_data = change.data
        else:
            # Default to last-write-wins
            if client_dt > server_timestamp:
                resolved_data = change.data
            else:
                resolved_data = {k: v for k, v in server_data.items() 
                               if k not in ("id", "user_id", "created_at", "updated_at")}
        
        conflict = SyncConflict(
            change_id=change.id,
            entity_type=change.entity_type,
            entity_id=change.entity_id,
            client_data=change.data,
            server_data=server_data,
            client_timestamp=change.timestamp,
            server_timestamp=server_timestamp,
            resolution=resolution_strategy,
            resolved_data=resolved_data,
        )
        
        return conflict, resolved_data
    
    async def _notify_conflicts(
        self,
        user_id: UUID,
        conflicts: list[SyncConflict],
    ) -> None:
        """Notify user about sync conflicts.
        
        Validates: Requirements 35.4 - Notify users of sync conflicts
        
        Args:
            user_id: User's UUID
            conflicts: List of conflicts that occurred
        """
        if not conflicts:
            return
        
        try:
            if len(conflicts) == 1:
                conflict = conflicts[0]
                title = "Sync Conflict Resolved"
                body = (
                    f"A conflict was detected while syncing your {conflict.entity_type.value}. "
                    f"The conflict was automatically resolved using {conflict.resolution.value} strategy."
                )
            else:
                title = f"{len(conflicts)} Sync Conflicts Resolved"
                entity_types = set(c.entity_type.value for c in conflicts)
                body = (
                    f"Conflicts were detected while syncing your data "
                    f"({', '.join(entity_types)}). "
                    f"All conflicts were automatically resolved."
                )
            
            await self.notification_service.send_notification(
                user_id=user_id,
                title=title,
                body=body,
                channel=NotificationChannel.PUSH,
            )
            
            logger.info(f"Notified user {user_id} about {len(conflicts)} sync conflicts")
            
        except Exception as e:
            # Don't fail sync if notification fails
            logger.warning(f"Failed to notify user about sync conflicts: {e}")
    
    async def get_pending_changes(
        self,
        user_id: UUID,
        since: datetime,
    ) -> PendingChangesResponse:
        """Get changes from server since a given timestamp.
        
        Validates: Requirements 35.4
        
        Args:
            user_id: User's UUID
            since: Get changes after this timestamp
            
        Returns:
            PendingChangesResponse with list of changes
        """
        # This would query each entity type for changes since the given timestamp
        # For now, return empty list - full implementation would query all entity tables
        changes: list[PendingChange] = []
        
        # TODO: Query each entity type for changes since `since`
        # This would involve querying expenses, documents, health_records, etc.
        # and returning any that have updated_at > since
        
        logger.info(f"Retrieved {len(changes)} pending changes for user {user_id} since {since}")
        
        return PendingChangesResponse(
            changes=changes,
            server_timestamp=datetime.now(timezone.utc),
        )
    
    def _get_entity_handler(self, entity_type: SyncEntityType) -> "EntitySyncHandler":
        """Get the handler for a specific entity type.
        
        Args:
            entity_type: The entity type
            
        Returns:
            EntitySyncHandler for the entity type
        """
        handlers = {
            SyncEntityType.EXPENSE: ExpenseSyncHandler(self.db),
            SyncEntityType.DOCUMENT: DocumentSyncHandler(self.db),
            SyncEntityType.HEALTH_RECORD: HealthRecordSyncHandler(self.db),
            SyncEntityType.MEDICINE: MedicineSyncHandler(self.db),
            SyncEntityType.VITAL: VitalSyncHandler(self.db),
            SyncEntityType.WARDROBE_ITEM: WardrobeItemSyncHandler(self.db),
            SyncEntityType.SKILL: SkillSyncHandler(self.db),
            SyncEntityType.COURSE: CourseSyncHandler(self.db),
            SyncEntityType.JOB_APPLICATION: JobApplicationSyncHandler(self.db),
            SyncEntityType.ACHIEVEMENT: AchievementSyncHandler(self.db),
        }
        
        handler = handlers.get(entity_type)
        if handler is None:
            raise ValueError(f"No handler for entity type: {entity_type}")
        return handler


class EntitySyncHandler:
    """Base class for entity-specific sync handlers."""
    
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
    
    async def create(self, user_id: UUID, data: dict[str, Any]) -> UUID:
        """Create a new entity."""
        raise NotImplementedError
    
    async def get(self, user_id: UUID, entity_id: UUID) -> Optional[dict[str, Any]]:
        """Get an entity by ID."""
        raise NotImplementedError
    
    async def update(self, user_id: UUID, entity_id: UUID, data: dict[str, Any]) -> bool:
        """Update an entity."""
        raise NotImplementedError
    
    async def delete(self, user_id: UUID, entity_id: UUID) -> bool:
        """Delete an entity."""
        raise NotImplementedError


class ExpenseSyncHandler(EntitySyncHandler):
    """Sync handler for expenses."""
    
    async def create(self, user_id: UUID, data: dict[str, Any]) -> UUID:
        from app.schemas.expense import ExpenseCreate
        from app.services.expense import ExpenseService
        
        service = ExpenseService(self.db)
        expense_data = ExpenseCreate(**data)
        result = await service.create_expense(user_id, expense_data)
        return result.id
    
    async def get(self, user_id: UUID, entity_id: UUID) -> Optional[dict[str, Any]]:
        from app.services.expense import ExpenseService
        
        service = ExpenseService(self.db)
        expense = await service.get_expense(entity_id, user_id)
        if expense:
            return expense.model_dump()
        return None
    
    async def update(self, user_id: UUID, entity_id: UUID, data: dict[str, Any]) -> bool:
        from app.schemas.expense import ExpenseUpdate
        from app.services.expense import ExpenseService
        
        service = ExpenseService(self.db)
        update_data = ExpenseUpdate(**data)
        result = await service.update_expense(entity_id, user_id, update_data)
        return result is not None
    
    async def delete(self, user_id: UUID, entity_id: UUID) -> bool:
        from app.services.expense import ExpenseService
        
        service = ExpenseService(self.db)
        return await service.delete_expense(entity_id, user_id)


class DocumentSyncHandler(EntitySyncHandler):
    """Sync handler for documents."""
    
    async def create(self, user_id: UUID, data: dict[str, Any]) -> UUID:
        # Documents require file upload, so create is not supported via sync
        raise ValueError("Document creation requires file upload and cannot be synced offline")
    
    async def get(self, user_id: UUID, entity_id: UUID) -> Optional[dict[str, Any]]:
        from app.services.document import DocumentService
        
        service = DocumentService(self.db)
        doc = await service.get_document(entity_id, user_id)
        if doc:
            return doc.model_dump()
        return None
    
    async def update(self, user_id: UUID, entity_id: UUID, data: dict[str, Any]) -> bool:
        from app.schemas.document import DocumentUpdate
        from app.services.document import DocumentService
        
        service = DocumentService(self.db)
        update_data = DocumentUpdate(**data)
        result = await service.update_document(entity_id, user_id, update_data)
        return result is not None
    
    async def delete(self, user_id: UUID, entity_id: UUID) -> bool:
        from app.services.document import DocumentService
        
        service = DocumentService(self.db)
        return await service.delete_document(entity_id, user_id)


class HealthRecordSyncHandler(EntitySyncHandler):
    """Sync handler for health records."""
    
    async def create(self, user_id: UUID, data: dict[str, Any]) -> UUID:
        # Health records require file upload
        raise ValueError("Health record creation requires file upload and cannot be synced offline")
    
    async def get(self, user_id: UUID, entity_id: UUID) -> Optional[dict[str, Any]]:
        from app.services.health import HealthService
        
        service = HealthService(self.db)
        record = await service.get_health_record(entity_id, user_id)
        if record:
            return record.model_dump()
        return None
    
    async def update(self, user_id: UUID, entity_id: UUID, data: dict[str, Any]) -> bool:
        from app.schemas.health import HealthRecordUpdate
        from app.services.health import HealthService
        
        service = HealthService(self.db)
        update_data = HealthRecordUpdate(**data)
        result = await service.update_health_record(entity_id, user_id, update_data)
        return result is not None
    
    async def delete(self, user_id: UUID, entity_id: UUID) -> bool:
        from app.services.health import HealthService
        
        service = HealthService(self.db)
        return await service.delete_health_record(entity_id, user_id)


class MedicineSyncHandler(EntitySyncHandler):
    """Sync handler for medicines."""
    
    async def create(self, user_id: UUID, data: dict[str, Any]) -> UUID:
        from app.schemas.medicine import MedicineCreate
        from app.services.medicine import MedicineService
        
        service = MedicineService(self.db)
        medicine_data = MedicineCreate(**data)
        result = await service.create_medicine(user_id, medicine_data)
        return result.id
    
    async def get(self, user_id: UUID, entity_id: UUID) -> Optional[dict[str, Any]]:
        from app.services.medicine import MedicineService
        
        service = MedicineService(self.db)
        medicine = await service.get_medicine(entity_id, user_id)
        if medicine:
            return medicine.model_dump()
        return None
    
    async def update(self, user_id: UUID, entity_id: UUID, data: dict[str, Any]) -> bool:
        from app.schemas.medicine import MedicineUpdate
        from app.services.medicine import MedicineService
        
        service = MedicineService(self.db)
        update_data = MedicineUpdate(**data)
        result = await service.update_medicine(entity_id, user_id, update_data)
        return result is not None
    
    async def delete(self, user_id: UUID, entity_id: UUID) -> bool:
        from app.services.medicine import MedicineService
        
        service = MedicineService(self.db)
        return await service.delete_medicine(entity_id, user_id)


class VitalSyncHandler(EntitySyncHandler):
    """Sync handler for vitals."""
    
    async def create(self, user_id: UUID, data: dict[str, Any]) -> UUID:
        from app.schemas.vital import VitalCreate
        from app.services.vital import VitalService
        
        service = VitalService(self.db)
        vital_data = VitalCreate(**data)
        result = await service.log_vital(user_id, vital_data)
        return result.id
    
    async def get(self, user_id: UUID, entity_id: UUID) -> Optional[dict[str, Any]]:
        from app.services.vital import VitalService
        
        service = VitalService(self.db)
        vital = await service.get_vital(entity_id, user_id)
        if vital:
            return vital.model_dump()
        return None
    
    async def update(self, user_id: UUID, entity_id: UUID, data: dict[str, Any]) -> bool:
        from app.schemas.vital import VitalUpdate
        from app.services.vital import VitalService
        
        service = VitalService(self.db)
        update_data = VitalUpdate(**data)
        result = await service.update_vital(entity_id, user_id, update_data)
        return result is not None
    
    async def delete(self, user_id: UUID, entity_id: UUID) -> bool:
        from app.services.vital import VitalService
        
        service = VitalService(self.db)
        return await service.delete_vital(entity_id, user_id)


class WardrobeItemSyncHandler(EntitySyncHandler):
    """Sync handler for wardrobe items."""
    
    async def create(self, user_id: UUID, data: dict[str, Any]) -> UUID:
        # Wardrobe items require image upload
        raise ValueError("Wardrobe item creation requires image upload and cannot be synced offline")
    
    async def get(self, user_id: UUID, entity_id: UUID) -> Optional[dict[str, Any]]:
        from app.services.wardrobe import WardrobeService
        
        service = WardrobeService(self.db)
        item = await service.get_item(entity_id, user_id)
        if item:
            return item.model_dump()
        return None
    
    async def update(self, user_id: UUID, entity_id: UUID, data: dict[str, Any]) -> bool:
        from app.schemas.wardrobe import WardrobeItemUpdate
        from app.services.wardrobe import WardrobeService
        
        service = WardrobeService(self.db)
        update_data = WardrobeItemUpdate(**data)
        result = await service.update_item(entity_id, user_id, update_data)
        return result is not None
    
    async def delete(self, user_id: UUID, entity_id: UUID) -> bool:
        from app.services.wardrobe import WardrobeService
        
        service = WardrobeService(self.db)
        return await service.delete_item(entity_id, user_id)


class SkillSyncHandler(EntitySyncHandler):
    """Sync handler for skills."""
    
    async def create(self, user_id: UUID, data: dict[str, Any]) -> UUID:
        from app.schemas.skill import SkillCreate
        from app.services.skill import SkillService
        
        service = SkillService(self.db)
        skill_data = SkillCreate(**data)
        result = await service.create_skill(user_id, skill_data)
        return result.id
    
    async def get(self, user_id: UUID, entity_id: UUID) -> Optional[dict[str, Any]]:
        from app.services.skill import SkillService
        
        service = SkillService(self.db)
        skill = await service.get_skill(entity_id, user_id)
        if skill:
            return skill.model_dump()
        return None
    
    async def update(self, user_id: UUID, entity_id: UUID, data: dict[str, Any]) -> bool:
        from app.schemas.skill import SkillUpdate
        from app.services.skill import SkillService
        
        service = SkillService(self.db)
        update_data = SkillUpdate(**data)
        result = await service.update_skill(entity_id, user_id, update_data)
        return result is not None
    
    async def delete(self, user_id: UUID, entity_id: UUID) -> bool:
        from app.services.skill import SkillService
        
        service = SkillService(self.db)
        return await service.delete_skill(entity_id, user_id)


class CourseSyncHandler(EntitySyncHandler):
    """Sync handler for courses."""
    
    async def create(self, user_id: UUID, data: dict[str, Any]) -> UUID:
        from app.schemas.course import CourseCreate
        from app.services.course import CourseService
        
        service = CourseService(self.db)
        course_data = CourseCreate(**data)
        result = await service.create_course(user_id, course_data)
        return result.id
    
    async def get(self, user_id: UUID, entity_id: UUID) -> Optional[dict[str, Any]]:
        from app.services.course import CourseService
        
        service = CourseService(self.db)
        course = await service.get_course(entity_id, user_id)
        if course:
            return course.model_dump()
        return None
    
    async def update(self, user_id: UUID, entity_id: UUID, data: dict[str, Any]) -> bool:
        from app.schemas.course import CourseUpdate
        from app.services.course import CourseService
        
        service = CourseService(self.db)
        update_data = CourseUpdate(**data)
        result = await service.update_course(entity_id, user_id, update_data)
        return result is not None
    
    async def delete(self, user_id: UUID, entity_id: UUID) -> bool:
        from app.services.course import CourseService
        
        service = CourseService(self.db)
        return await service.delete_course(entity_id, user_id)


class JobApplicationSyncHandler(EntitySyncHandler):
    """Sync handler for job applications."""
    
    async def create(self, user_id: UUID, data: dict[str, Any]) -> UUID:
        from app.schemas.job_application import JobApplicationCreate
        from app.services.job_application import JobApplicationService
        
        service = JobApplicationService(self.db)
        app_data = JobApplicationCreate(**data)
        result = await service.create_application(user_id, app_data)
        return result.id
    
    async def get(self, user_id: UUID, entity_id: UUID) -> Optional[dict[str, Any]]:
        from app.services.job_application import JobApplicationService
        
        service = JobApplicationService(self.db)
        app = await service.get_application(entity_id, user_id)
        if app:
            return app.model_dump()
        return None
    
    async def update(self, user_id: UUID, entity_id: UUID, data: dict[str, Any]) -> bool:
        from app.schemas.job_application import JobApplicationUpdate
        from app.services.job_application import JobApplicationService
        
        service = JobApplicationService(self.db)
        update_data = JobApplicationUpdate(**data)
        result = await service.update_application(entity_id, user_id, update_data)
        return result is not None
    
    async def delete(self, user_id: UUID, entity_id: UUID) -> bool:
        from app.services.job_application import JobApplicationService
        
        service = JobApplicationService(self.db)
        return await service.delete_application(entity_id, user_id)


class AchievementSyncHandler(EntitySyncHandler):
    """Sync handler for achievements."""
    
    async def create(self, user_id: UUID, data: dict[str, Any]) -> UUID:
        from app.schemas.achievement import AchievementCreate
        from app.services.achievement import AchievementService
        
        service = AchievementService(self.db)
        achievement_data = AchievementCreate(**data)
        result = await service.create_achievement(user_id, achievement_data)
        return result.id
    
    async def get(self, user_id: UUID, entity_id: UUID) -> Optional[dict[str, Any]]:
        from app.services.achievement import AchievementService
        
        service = AchievementService(self.db)
        achievement = await service.get_achievement(entity_id, user_id)
        if achievement:
            return achievement.model_dump()
        return None
    
    async def update(self, user_id: UUID, entity_id: UUID, data: dict[str, Any]) -> bool:
        from app.schemas.achievement import AchievementUpdate
        from app.services.achievement import AchievementService
        
        service = AchievementService(self.db)
        update_data = AchievementUpdate(**data)
        result = await service.update_achievement(entity_id, user_id, update_data)
        return result is not None
    
    async def delete(self, user_id: UUID, entity_id: UUID) -> bool:
        from app.services.achievement import AchievementService
        
        service = AchievementService(self.db)
        return await service.delete_achievement(entity_id, user_id)
