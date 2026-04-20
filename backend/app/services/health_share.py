"""Health record share service for sharing records with doctors.

Provides functionality for creating share links, accessing shared records,
and managing share access logs.

Validates: Requirements 18.1, 18.2, 18.3, 18.4, 18.5
"""

from datetime import datetime, timedelta, timezone
from typing import List, Optional
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.health_share import HealthRecordShare
from app.repositories.health_share import HealthShareRepository
from app.repositories.health import HealthRepository
from app.schemas.health_share import (
    HealthRecordShareCreate,
    HealthRecordShareUpdate,
    HealthRecordShareResponse,
    HealthRecordShareDetailResponse,
    PublicHealthShareResponse,
    SharedHealthRecordInfo,
    HealthShareAccessLogResponse,
    PaginatedHealthRecordShareResponse,
)


class HealthShareService:
    """Service for managing health record sharing with doctors.
    
    Validates: Requirements 18.1, 18.2, 18.3, 18.4, 18.5
    """
    
    def __init__(self, db: AsyncSession) -> None:
        """Initialize the health share service.
        
        Args:
            db: Async database session
        """
        self.db = db
        self.repository = HealthShareRepository(db)
        self.health_repository = HealthRepository(db)
    
    async def create_share(
        self,
        user_id: UUID,
        data: HealthRecordShareCreate,
    ) -> HealthRecordShareResponse:
        """Create a new health record share link.
        
        Validates: Requirements 18.1, 18.2
        
        Args:
            user_id: User's UUID
            data: Share creation data
            
        Returns:
            Created share response
            
        Raises:
            ValueError: If any record IDs don't belong to the user
        """
        # Validate all record IDs belong to the user
        for record_id in data.record_ids:
            record = await self.health_repository.get_health_record_by_id(
                record_id, user_id
            )
            if record is None:
                raise ValueError(f"Health record {record_id} not found or doesn't belong to user")
        
        # Calculate expiration time
        expires_at = datetime.now(timezone.utc) + timedelta(hours=data.expires_in_hours)
        
        share = await self.repository.create(user_id, data, expires_at)
        await self.db.commit()
        
        return self._to_response(share)
    
    async def get_share(
        self,
        user_id: UUID,
        share_id: UUID,
    ) -> Optional[HealthRecordShareResponse]:
        """Get a health record share by ID.
        
        Args:
            user_id: User's UUID
            share_id: Share's UUID
            
        Returns:
            Share response if found, None otherwise
        """
        share = await self.repository.get_by_id(share_id, user_id)
        if share is None:
            return None
        return self._to_response(share)
    
    async def get_share_with_logs(
        self,
        user_id: UUID,
        share_id: UUID,
    ) -> Optional[HealthRecordShareDetailResponse]:
        """Get a health record share with access logs.
        
        Validates: Requirements 18.5
        
        Args:
            user_id: User's UUID
            share_id: Share's UUID
            
        Returns:
            Detailed share response with access logs if found, None otherwise
        """
        share = await self.repository.get_by_id(share_id, user_id)
        if share is None:
            return None
        
        # Get access logs
        access_logs = await self.repository.get_access_logs(share_id)
        
        return self._to_detail_response(share, access_logs)
    
    async def list_shares(
        self,
        user_id: UUID,
        include_expired: bool = False,
        include_revoked: bool = False,
        page: int = 1,
        page_size: int = 20,
    ) -> PaginatedHealthRecordShareResponse:
        """List all health record shares for a user.
        
        Validates: Requirements 18.1
        
        Args:
            user_id: User's UUID
            include_expired: Whether to include expired shares
            include_revoked: Whether to include revoked shares
            page: Page number (1-indexed)
            page_size: Number of results per page
            
        Returns:
            Paginated share response
        """
        offset = (page - 1) * page_size
        
        shares = await self.repository.get_by_user(
            user_id,
            include_expired=include_expired,
            include_revoked=include_revoked,
            limit=page_size,
            offset=offset,
        )
        total = await self.repository.count_by_user(
            user_id,
            include_expired=include_expired,
            include_revoked=include_revoked,
        )
        
        items = [self._to_response(share) for share in shares]
        return PaginatedHealthRecordShareResponse.create(items, total, page, page_size)
    
    async def get_public_share(
        self,
        token: str,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> Optional[PublicHealthShareResponse]:
        """Get public shared health records by token (no authentication).
        
        Validates: Requirements 18.3, 18.4, 18.5
        
        This endpoint is accessible without authentication and returns
        read-only health record information.
        
        Args:
            token: Public access token
            ip_address: IP address of the accessor (for logging)
            user_agent: User agent string (for logging)
            
        Returns:
            Public share response if valid, None otherwise
        """
        share = await self.repository.get_by_token(token)
        if share is None:
            return None
        
        # Check if share is valid (not expired and not revoked)
        if not share.is_valid:
            return None
        
        # Log the access
        await self.repository.create_access_log(share.id, ip_address, user_agent)
        await self.repository.increment_access_count(share)
        await self.db.commit()
        
        # Fetch the actual health records
        records = []
        for record_id_str in share.record_ids:
            record_id = UUID(record_id_str)
            record = await self.health_repository.get_health_record_with_family_member(
                record_id, share.user_id
            )
            if record is not None:
                family_member_name = None
                if record.family_member is not None:
                    family_member_name = record.family_member.name
                
                records.append(SharedHealthRecordInfo(
                    id=record.id,
                    category=record.category,
                    title=record.title,
                    record_date=record.record_date,
                    doctor_name=record.doctor_name,
                    hospital_name=record.hospital_name,
                    notes=record.notes,
                    family_member_name=family_member_name,
                ))
        
        return PublicHealthShareResponse(
            share_id=share.id,
            doctor_name=share.doctor_name,
            purpose=share.purpose,
            notes=share.notes,
            records=records,
            expires_at=share.expires_at,
            shared_by_notes=share.notes,
        )
    
    async def update_share(
        self,
        user_id: UUID,
        share_id: UUID,
        data: HealthRecordShareUpdate,
    ) -> Optional[HealthRecordShareResponse]:
        """Update a health record share.
        
        Args:
            user_id: User's UUID
            share_id: Share's UUID
            data: Share update data
            
        Returns:
            Updated share response if found, None otherwise
        """
        share = await self.repository.get_by_id(share_id, user_id)
        if share is None:
            return None
        
        updated = await self.repository.update(share, data)
        await self.db.commit()
        return self._to_response(updated)
    
    async def revoke_share(
        self,
        user_id: UUID,
        share_id: UUID,
    ) -> Optional[HealthRecordShareResponse]:
        """Revoke a health record share.
        
        Validates: Requirements 18.4
        
        Args:
            user_id: User's UUID
            share_id: Share's UUID
            
        Returns:
            Revoked share response if found, None otherwise
        """
        share = await self.repository.get_by_id(share_id, user_id)
        if share is None:
            return None
        
        revoked = await self.repository.revoke(share)
        await self.db.commit()
        return self._to_response(revoked)
    
    async def delete_share(
        self,
        user_id: UUID,
        share_id: UUID,
    ) -> bool:
        """Delete a health record share.
        
        Args:
            user_id: User's UUID
            share_id: Share's UUID
            
        Returns:
            True if deleted, False if not found
        """
        share = await self.repository.get_by_id(share_id, user_id)
        if share is None:
            return False
        
        await self.repository.delete(share)
        await self.db.commit()
        return True
    
    def _to_response(self, share: HealthRecordShare) -> HealthRecordShareResponse:
        """Convert HealthRecordShare model to response schema.
        
        Args:
            share: HealthRecordShare model instance
            
        Returns:
            HealthRecordShareResponse schema
        """
        # Convert string record IDs back to UUIDs
        record_ids = [UUID(rid) for rid in share.record_ids]
        
        return HealthRecordShareResponse(
            id=share.id,
            user_id=share.user_id,
            public_token=share.public_token,
            doctor_name=share.doctor_name,
            doctor_email=share.doctor_email,
            purpose=share.purpose,
            record_ids=record_ids,
            expires_at=share.expires_at,
            is_revoked=share.is_revoked,
            is_expired=share.is_expired,
            is_valid=share.is_valid,
            access_count=share.access_count,
            last_accessed_at=share.last_accessed_at,
            notes=share.notes,
            created_at=share.created_at,
            updated_at=share.updated_at,
        )
    
    def _to_detail_response(
        self,
        share: HealthRecordShare,
        access_logs: list,
    ) -> HealthRecordShareDetailResponse:
        """Convert HealthRecordShare model to detailed response with logs.
        
        Args:
            share: HealthRecordShare model instance
            access_logs: List of HealthShareAccessLog instances
            
        Returns:
            HealthRecordShareDetailResponse schema
        """
        # Convert string record IDs back to UUIDs
        record_ids = [UUID(rid) for rid in share.record_ids]
        
        # Convert access logs to response schemas
        log_responses = [
            HealthShareAccessLogResponse(
                id=log.id,
                share_id=log.share_id,
                ip_address=log.ip_address,
                user_agent=log.user_agent,
                accessed_at=log.accessed_at,
            )
            for log in access_logs
        ]
        
        return HealthRecordShareDetailResponse(
            id=share.id,
            user_id=share.user_id,
            public_token=share.public_token,
            doctor_name=share.doctor_name,
            doctor_email=share.doctor_email,
            purpose=share.purpose,
            record_ids=record_ids,
            expires_at=share.expires_at,
            is_revoked=share.is_revoked,
            is_expired=share.is_expired,
            is_valid=share.is_valid,
            access_count=share.access_count,
            last_accessed_at=share.last_accessed_at,
            notes=share.notes,
            created_at=share.created_at,
            updated_at=share.updated_at,
            access_logs=log_responses,
        )
