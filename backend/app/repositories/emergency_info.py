"""Emergency info repository for database operations.

Validates: Requirements 17.1, 17.2, 17.3, 17.4, 17.5
"""

from typing import Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.emergency_info import EmergencyInfo
from app.schemas.emergency_info import (
    EmergencyInfoCreate,
    EmergencyInfoUpdate,
    VisibilityUpdate,
    EmergencyContact,
)


class EmergencyInfoRepository:
    """Repository for EmergencyInfo database operations.
    
    Validates: Requirements 17.1, 17.2, 17.3, 17.4, 17.5
    """
    
    def __init__(self, db: AsyncSession) -> None:
        """Initialize repository with database session.
        
        Args:
            db: Async database session
        """
        self.db = db
    
    async def create(
        self,
        user_id: UUID,
        data: EmergencyInfoCreate,
    ) -> EmergencyInfo:
        """Create emergency health information.
        
        Validates: Requirements 17.1
        
        Args:
            user_id: User's UUID
            data: Emergency info creation data
            
        Returns:
            Created EmergencyInfo model instance
        """
        # Convert emergency contacts to dict format for JSON storage
        emergency_contacts = None
        if data.emergency_contacts:
            emergency_contacts = [
                contact.model_dump() for contact in data.emergency_contacts
            ]
        
        emergency_info = EmergencyInfo(
            user_id=user_id,
            blood_type=data.blood_type,
            allergies=data.allergies or [],
            medical_conditions=data.medical_conditions or [],
            emergency_contacts=emergency_contacts or [],
            current_medications=data.current_medications or [],
            visible_fields=data.visible_fields,
        )
        self.db.add(emergency_info)
        await self.db.flush()
        await self.db.refresh(emergency_info)
        return emergency_info
    
    async def get_by_user_id(self, user_id: UUID) -> Optional[EmergencyInfo]:
        """Get emergency info by user ID.
        
        Args:
            user_id: User's UUID
            
        Returns:
            EmergencyInfo if found, None otherwise
        """
        stmt = select(EmergencyInfo).where(EmergencyInfo.user_id == user_id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()
    
    async def get_by_public_token(self, token: str) -> Optional[EmergencyInfo]:
        """Get emergency info by public access token.
        
        Validates: Requirements 17.4
        
        Args:
            token: Public access token
            
        Returns:
            EmergencyInfo if found, None otherwise
        """
        stmt = select(EmergencyInfo).where(EmergencyInfo.public_token == token)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()
    
    async def update(
        self,
        emergency_info: EmergencyInfo,
        data: EmergencyInfoUpdate,
    ) -> EmergencyInfo:
        """Update emergency health information.
        
        Validates: Requirements 17.1
        
        Args:
            emergency_info: Existing EmergencyInfo model instance
            data: Emergency info update data
            
        Returns:
            Updated EmergencyInfo model instance
        """
        update_data = data.model_dump(exclude_unset=True)
        
        # Handle emergency_contacts conversion
        if "emergency_contacts" in update_data and update_data["emergency_contacts"] is not None:
            update_data["emergency_contacts"] = [
                contact.model_dump() if isinstance(contact, EmergencyContact) else contact
                for contact in update_data["emergency_contacts"]
            ]
        
        for field, value in update_data.items():
            setattr(emergency_info, field, value)
        
        await self.db.flush()
        await self.db.refresh(emergency_info)
        return emergency_info
    
    async def update_visibility(
        self,
        emergency_info: EmergencyInfo,
        data: VisibilityUpdate,
    ) -> EmergencyInfo:
        """Update visible fields configuration.
        
        Validates: Requirements 17.5
        
        Args:
            emergency_info: Existing EmergencyInfo model instance
            data: Visibility update data
            
        Returns:
            Updated EmergencyInfo model instance
        """
        emergency_info.visible_fields = data.visible_fields
        await self.db.flush()
        await self.db.refresh(emergency_info)
        return emergency_info
    
    async def update_qr_code_path(
        self,
        emergency_info: EmergencyInfo,
        qr_code_path: str,
    ) -> EmergencyInfo:
        """Update the QR code path.
        
        Validates: Requirements 17.2
        
        Args:
            emergency_info: EmergencyInfo model instance
            qr_code_path: Path to the QR code image
            
        Returns:
            Updated EmergencyInfo model instance
        """
        emergency_info.qr_code_path = qr_code_path
        await self.db.flush()
        await self.db.refresh(emergency_info)
        return emergency_info
    
    async def regenerate_token(self, emergency_info: EmergencyInfo) -> EmergencyInfo:
        """Regenerate the public access token.
        
        Validates: Requirements 17.5
        
        Args:
            emergency_info: EmergencyInfo model instance
            
        Returns:
            Updated EmergencyInfo model instance with new token
        """
        emergency_info.public_token = EmergencyInfo.generate_public_token()
        # Clear old QR code since token changed
        emergency_info.qr_code_path = None
        await self.db.flush()
        await self.db.refresh(emergency_info)
        return emergency_info
    
    async def delete(self, emergency_info: EmergencyInfo) -> None:
        """Delete emergency health information.
        
        Args:
            emergency_info: EmergencyInfo model instance to delete
        """
        await self.db.delete(emergency_info)
        await self.db.flush()
