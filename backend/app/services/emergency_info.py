"""Emergency info service for managing emergency health information.

Provides functionality for emergency info CRUD operations, QR code generation,
and public access.

Validates: Requirements 17.1, 17.2, 17.3, 17.4, 17.5
"""

from io import BytesIO
from typing import Optional
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.emergency_info import EmergencyInfo, EmergencyInfoField, BloodType
from app.repositories.emergency_info import EmergencyInfoRepository
from app.schemas.emergency_info import (
    EmergencyInfoCreate,
    EmergencyInfoUpdate,
    EmergencyInfoResponse,
    PublicEmergencyInfoResponse,
    VisibilityUpdate,
    QRCodeResponse,
    EmergencyContact,
    EmergencyFieldInfo,
    AvailableFieldsResponse,
)


class EmergencyInfoService:
    """Service for managing emergency health information.
    
    Validates: Requirements 17.1, 17.2, 17.3, 17.4, 17.5
    """
    
    def __init__(self, db: AsyncSession) -> None:
        """Initialize the emergency info service.
        
        Args:
            db: Async database session
        """
        self.db = db
        self.repository = EmergencyInfoRepository(db)
    
    async def create_or_update(
        self,
        user_id: UUID,
        data: EmergencyInfoCreate,
    ) -> EmergencyInfoResponse:
        """Create or update emergency health information.
        
        Validates: Requirements 17.1
        
        If emergency info already exists for the user, it will be updated.
        Otherwise, a new record will be created.
        
        Args:
            user_id: User's UUID
            data: Emergency info creation data
            
        Returns:
            Created or updated emergency info response
        """
        existing = await self.repository.get_by_user_id(user_id)
        
        if existing:
            # Update existing record
            update_data = EmergencyInfoUpdate(
                blood_type=data.blood_type,
                allergies=data.allergies,
                medical_conditions=data.medical_conditions,
                emergency_contacts=data.emergency_contacts,
                current_medications=data.current_medications,
            )
            emergency_info = await self.repository.update(existing, update_data)
            
            # Update visibility if provided
            if data.visible_fields is not None:
                visibility_data = VisibilityUpdate(visible_fields=data.visible_fields)
                emergency_info = await self.repository.update_visibility(
                    emergency_info, visibility_data
                )
        else:
            # Create new record
            emergency_info = await self.repository.create(user_id, data)
        
        await self.db.commit()
        return self._to_response(emergency_info)
    
    async def get(self, user_id: UUID) -> Optional[EmergencyInfoResponse]:
        """Get emergency info for a user.
        
        Args:
            user_id: User's UUID
            
        Returns:
            Emergency info response if found, None otherwise
        """
        emergency_info = await self.repository.get_by_user_id(user_id)
        if emergency_info is None:
            return None
        return self._to_response(emergency_info)
    
    async def get_public(self, token: str) -> Optional[PublicEmergencyInfoResponse]:
        """Get public emergency info by token (no authentication required).
        
        Validates: Requirements 17.3, 17.4
        
        Returns only the fields configured as visible by the user.
        
        Args:
            token: Public access token
            
        Returns:
            Public emergency info response if found, None otherwise
        """
        emergency_info = await self.repository.get_by_public_token(token)
        if emergency_info is None:
            return None
        
        return self._to_public_response(emergency_info)
    
    async def update(
        self,
        user_id: UUID,
        data: EmergencyInfoUpdate,
    ) -> Optional[EmergencyInfoResponse]:
        """Update emergency health information.
        
        Validates: Requirements 17.1
        
        Args:
            user_id: User's UUID
            data: Emergency info update data
            
        Returns:
            Updated emergency info response if found, None otherwise
        """
        emergency_info = await self.repository.get_by_user_id(user_id)
        if emergency_info is None:
            return None
        
        updated = await self.repository.update(emergency_info, data)
        await self.db.commit()
        return self._to_response(updated)
    
    async def update_visibility(
        self,
        user_id: UUID,
        data: VisibilityUpdate,
    ) -> Optional[EmergencyInfoResponse]:
        """Update visible fields configuration.
        
        Validates: Requirements 17.5
        
        Args:
            user_id: User's UUID
            data: Visibility update data
            
        Returns:
            Updated emergency info response if found, None otherwise
        """
        emergency_info = await self.repository.get_by_user_id(user_id)
        if emergency_info is None:
            return None
        
        updated = await self.repository.update_visibility(emergency_info, data)
        await self.db.commit()
        return self._to_response(updated)
    
    async def generate_qr_code(
        self,
        user_id: UUID,
        base_url: str,
    ) -> Optional[QRCodeResponse]:
        """Generate QR code linking to public emergency page.
        
        Validates: Requirements 17.2
        
        Args:
            user_id: User's UUID
            base_url: Base URL for the public emergency page
            
        Returns:
            QR code response with URLs and token, None if not found
        """
        emergency_info = await self.repository.get_by_user_id(user_id)
        if emergency_info is None:
            return None
        
        # Build the public URL
        public_url = f"{base_url}/emergency/{emergency_info.public_token}"
        
        # Generate QR code image
        qr_code_bytes = self._generate_qr_code_image(public_url)
        
        # Store QR code (in production, this would upload to S3/storage)
        # For now, we'll use a placeholder path
        qr_code_path = f"qr_codes/emergency/{user_id}/{emergency_info.public_token}.png"
        await self.repository.update_qr_code_path(emergency_info, qr_code_path)
        await self.db.commit()
        
        return QRCodeResponse(
            qr_code_url=qr_code_path,
            public_url=public_url,
            public_token=emergency_info.public_token,
        )
    
    async def get_qr_code_image(self, user_id: UUID, base_url: str) -> Optional[bytes]:
        """Get QR code image as bytes.
        
        Validates: Requirements 17.2
        
        Args:
            user_id: User's UUID
            base_url: Base URL for the public emergency page
            
        Returns:
            QR code image as PNG bytes, None if not found
        """
        emergency_info = await self.repository.get_by_user_id(user_id)
        if emergency_info is None:
            return None
        
        # Build the public URL
        public_url = f"{base_url}/emergency/{emergency_info.public_token}"
        
        # Generate and return QR code image
        return self._generate_qr_code_image(public_url)
    
    async def regenerate_token(self, user_id: UUID) -> Optional[EmergencyInfoResponse]:
        """Regenerate the public access token.
        
        Validates: Requirements 17.5
        
        This invalidates the old QR code and requires generating a new one.
        
        Args:
            user_id: User's UUID
            
        Returns:
            Updated emergency info response with new token, None if not found
        """
        emergency_info = await self.repository.get_by_user_id(user_id)
        if emergency_info is None:
            return None
        
        updated = await self.repository.regenerate_token(emergency_info)
        await self.db.commit()
        return self._to_response(updated)
    
    async def delete(self, user_id: UUID) -> bool:
        """Delete emergency health information.
        
        Args:
            user_id: User's UUID
            
        Returns:
            True if deleted, False if not found
        """
        emergency_info = await self.repository.get_by_user_id(user_id)
        if emergency_info is None:
            return False
        
        await self.repository.delete(emergency_info)
        await self.db.commit()
        return True
    
    def get_available_fields(self) -> AvailableFieldsResponse:
        """Get available emergency info fields and blood types.
        
        Returns:
            Available fields and blood types
        """
        fields = [
            EmergencyFieldInfo(
                name=EmergencyInfoField.BLOOD_TYPE,
                display_name="Blood Type",
                description="Your blood type for emergency transfusions",
            ),
            EmergencyFieldInfo(
                name=EmergencyInfoField.ALLERGIES,
                display_name="Allergies",
                description="Known allergies to medications, foods, or substances",
            ),
            EmergencyFieldInfo(
                name=EmergencyInfoField.MEDICAL_CONDITIONS,
                display_name="Medical Conditions",
                description="Chronic conditions or important medical history",
            ),
            EmergencyFieldInfo(
                name=EmergencyInfoField.EMERGENCY_CONTACTS,
                display_name="Emergency Contacts",
                description="People to contact in case of emergency",
            ),
            EmergencyFieldInfo(
                name=EmergencyInfoField.CURRENT_MEDICATIONS,
                display_name="Current Medications",
                description="Medications you are currently taking",
            ),
        ]
        
        return AvailableFieldsResponse(
            fields=fields,
            blood_types=BloodType.ALL,
        )
    
    def _generate_qr_code_image(self, data: str) -> bytes:
        """Generate a QR code image.
        
        Validates: Requirements 17.2
        
        Args:
            data: Data to encode in the QR code
            
        Returns:
            QR code image as PNG bytes
        """
        import qrcode
        from qrcode.constants import ERROR_CORRECT_H
        
        # Create QR code with high error correction
        qr = qrcode.QRCode(
            version=1,
            error_correction=ERROR_CORRECT_H,
            box_size=10,
            border=4,
        )
        qr.add_data(data)
        qr.make(fit=True)
        
        # Create image
        img = qr.make_image(fill_color="black", back_color="white")
        
        # Convert to bytes
        buffer = BytesIO()
        img.save(buffer, format="PNG")
        return buffer.getvalue()
    
    def _to_response(self, emergency_info: EmergencyInfo) -> EmergencyInfoResponse:
        """Convert EmergencyInfo model to response schema.
        
        Args:
            emergency_info: EmergencyInfo model instance
            
        Returns:
            EmergencyInfoResponse schema
        """
        # Convert emergency contacts from dict to schema
        emergency_contacts = None
        if emergency_info.emergency_contacts:
            emergency_contacts = [
                EmergencyContact(**contact) if isinstance(contact, dict) else contact
                for contact in emergency_info.emergency_contacts
            ]
        
        return EmergencyInfoResponse(
            id=emergency_info.id,
            user_id=emergency_info.user_id,
            public_token=emergency_info.public_token,
            blood_type=emergency_info.blood_type,
            allergies=emergency_info.allergies,
            medical_conditions=emergency_info.medical_conditions,
            emergency_contacts=emergency_contacts,
            current_medications=emergency_info.current_medications,
            visible_fields=emergency_info.visible_fields,
            qr_code_path=emergency_info.qr_code_path,
            created_at=emergency_info.created_at,
            updated_at=emergency_info.updated_at,
        )
    
    def _to_public_response(
        self, 
        emergency_info: EmergencyInfo,
    ) -> PublicEmergencyInfoResponse:
        """Convert EmergencyInfo model to public response schema.
        
        Validates: Requirements 17.3
        
        Only includes fields that are configured as visible.
        
        Args:
            emergency_info: EmergencyInfo model instance
            
        Returns:
            PublicEmergencyInfoResponse schema with only visible fields
        """
        visible = emergency_info.visible_fields or []
        
        # Build response with only visible fields
        response_data = {}
        
        if EmergencyInfoField.BLOOD_TYPE in visible:
            response_data["blood_type"] = emergency_info.blood_type
        
        if EmergencyInfoField.ALLERGIES in visible:
            response_data["allergies"] = emergency_info.allergies
        
        if EmergencyInfoField.MEDICAL_CONDITIONS in visible:
            response_data["medical_conditions"] = emergency_info.medical_conditions
        
        if EmergencyInfoField.EMERGENCY_CONTACTS in visible:
            contacts = None
            if emergency_info.emergency_contacts:
                contacts = [
                    EmergencyContact(**contact) if isinstance(contact, dict) else contact
                    for contact in emergency_info.emergency_contacts
                ]
            response_data["emergency_contacts"] = contacts
        
        if EmergencyInfoField.CURRENT_MEDICATIONS in visible:
            response_data["current_medications"] = emergency_info.current_medications
        
        return PublicEmergencyInfoResponse(**response_data)
