"""Document expiry repository for database operations.

Validates: Requirements 8.1, 8.2, 8.3, 8.4
"""

from datetime import datetime, timezone
from typing import List, Optional
from uuid import UUID

from sqlalchemy import and_, delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.document import Document
from app.models.document_expiry import (
    DocumentExpiryAlert,
    DocumentExpiryAlertPreferences,
    ExpiryAlertType,
)
from app.schemas.document import DocumentCategory


class DocumentExpiryAlertPreferencesRepository:
    """Repository for DocumentExpiryAlertPreferences database operations.
    
    Validates: Requirements 8.4
    """

    def __init__(self, db: AsyncSession) -> None:
        """Initialize repository with database session.
        
        Args:
            db: Async database session
        """
        self.db = db

    async def create_preferences(
        self,
        user_id: UUID,
        category: str,
        alerts_enabled: bool = True,
        alert_30_days: bool = True,
        alert_14_days: bool = True,
        alert_7_days: bool = True,
    ) -> DocumentExpiryAlertPreferences:
        """Create expiry alert preferences for a user and category.
        
        Validates: Requirements 8.4
        
        Args:
            user_id: User's UUID
            category: Document category
            alerts_enabled: Enable alerts for this category
            alert_30_days: Enable 30-day alert
            alert_14_days: Enable 14-day alert
            alert_7_days: Enable 7-day alert
            
        Returns:
            Created DocumentExpiryAlertPreferences model instance
        """
        preferences = DocumentExpiryAlertPreferences(
            user_id=user_id,
            category=category,
            alerts_enabled=alerts_enabled,
            alert_30_days=alert_30_days,
            alert_14_days=alert_14_days,
            alert_7_days=alert_7_days,
        )
        self.db.add(preferences)
        await self.db.flush()
        await self.db.refresh(preferences)
        return preferences

    async def get_preferences_by_user_and_category(
        self,
        user_id: UUID,
        category: str,
    ) -> Optional[DocumentExpiryAlertPreferences]:
        """Get expiry alert preferences for a user and category.
        
        Args:
            user_id: User's UUID
            category: Document category
            
        Returns:
            DocumentExpiryAlertPreferences if found, None otherwise
        """
        stmt = select(DocumentExpiryAlertPreferences).where(
            and_(
                DocumentExpiryAlertPreferences.user_id == user_id,
                DocumentExpiryAlertPreferences.category == category,
            )
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_all_preferences_by_user(
        self,
        user_id: UUID,
    ) -> List[DocumentExpiryAlertPreferences]:
        """Get all expiry alert preferences for a user.
        
        Args:
            user_id: User's UUID
            
        Returns:
            List of DocumentExpiryAlertPreferences model instances
        """
        stmt = select(DocumentExpiryAlertPreferences).where(
            DocumentExpiryAlertPreferences.user_id == user_id
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def update_preferences(
        self,
        user_id: UUID,
        category: str,
        **kwargs,
    ) -> Optional[DocumentExpiryAlertPreferences]:
        """Update expiry alert preferences.
        
        Validates: Requirements 8.4
        
        Args:
            user_id: User's UUID
            category: Document category
            **kwargs: Fields to update
            
        Returns:
            Updated DocumentExpiryAlertPreferences if found, None otherwise
        """
        update_data = {k: v for k, v in kwargs.items() if v is not None}
        
        if not update_data:
            return await self.get_preferences_by_user_and_category(user_id, category)

        stmt = (
            update(DocumentExpiryAlertPreferences)
            .where(
                and_(
                    DocumentExpiryAlertPreferences.user_id == user_id,
                    DocumentExpiryAlertPreferences.category == category,
                )
            )
            .values(**update_data)
            .returning(DocumentExpiryAlertPreferences)
        )
        result = await self.db.execute(stmt)
        await self.db.flush()
        return result.scalar_one_or_none()

    async def get_or_create_preferences(
        self,
        user_id: UUID,
        category: str,
    ) -> DocumentExpiryAlertPreferences:
        """Get or create expiry alert preferences for a user and category.
        
        Args:
            user_id: User's UUID
            category: Document category
            
        Returns:
            DocumentExpiryAlertPreferences model instance
        """
        preferences = await self.get_preferences_by_user_and_category(user_id, category)
        if preferences is None:
            preferences = await self.create_preferences(user_id, category)
        return preferences

    async def delete_preferences(
        self,
        user_id: UUID,
        category: str,
    ) -> bool:
        """Delete expiry alert preferences.
        
        Args:
            user_id: User's UUID
            category: Document category
            
        Returns:
            True if deleted, False if not found
        """
        stmt = delete(DocumentExpiryAlertPreferences).where(
            and_(
                DocumentExpiryAlertPreferences.user_id == user_id,
                DocumentExpiryAlertPreferences.category == category,
            )
        )
        result = await self.db.execute(stmt)
        await self.db.flush()
        return result.rowcount > 0


class DocumentExpiryAlertRepository:
    """Repository for DocumentExpiryAlert database operations.
    
    Validates: Requirements 8.1, 8.3
    """

    def __init__(self, db: AsyncSession) -> None:
        """Initialize repository with database session.
        
        Args:
            db: Async database session
        """
        self.db = db

    async def create_alert(
        self,
        document_id: UUID,
        user_id: UUID,
        alert_type: ExpiryAlertType,
        notification_id: Optional[UUID] = None,
    ) -> DocumentExpiryAlert:
        """Create an expiry alert record.
        
        Validates: Requirements 8.1
        
        Args:
            document_id: Document's UUID
            user_id: User's UUID
            alert_type: Type of alert
            notification_id: Optional notification reference
            
        Returns:
            Created DocumentExpiryAlert model instance
        """
        alert = DocumentExpiryAlert(
            document_id=document_id,
            user_id=user_id,
            alert_type=alert_type,
            sent_at=datetime.now(timezone.utc),
            notification_id=notification_id,
        )
        self.db.add(alert)
        await self.db.flush()
        await self.db.refresh(alert)
        return alert

    async def get_alert_by_document_and_type(
        self,
        document_id: UUID,
        alert_type: ExpiryAlertType,
    ) -> Optional[DocumentExpiryAlert]:
        """Get an expiry alert by document and type.
        
        Args:
            document_id: Document's UUID
            alert_type: Type of alert
            
        Returns:
            DocumentExpiryAlert if found, None otherwise
        """
        stmt = select(DocumentExpiryAlert).where(
            and_(
                DocumentExpiryAlert.document_id == document_id,
                DocumentExpiryAlert.alert_type == alert_type,
            )
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_alerts_by_document(
        self,
        document_id: UUID,
    ) -> List[DocumentExpiryAlert]:
        """Get all expiry alerts for a document.
        
        Args:
            document_id: Document's UUID
            
        Returns:
            List of DocumentExpiryAlert model instances
        """
        stmt = select(DocumentExpiryAlert).where(
            DocumentExpiryAlert.document_id == document_id
        ).order_by(DocumentExpiryAlert.sent_at.desc())
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def delete_alerts_by_document(
        self,
        document_id: UUID,
    ) -> int:
        """Delete all expiry alerts for a document.
        
        Validates: Requirements 8.3
        
        Used when rescheduling alerts after expiry date update.
        
        Args:
            document_id: Document's UUID
            
        Returns:
            Number of alerts deleted
        """
        stmt = delete(DocumentExpiryAlert).where(
            DocumentExpiryAlert.document_id == document_id
        )
        result = await self.db.execute(stmt)
        await self.db.flush()
        return result.rowcount

    async def has_alert_been_sent(
        self,
        document_id: UUID,
        alert_type: ExpiryAlertType,
    ) -> bool:
        """Check if an alert has already been sent.
        
        Args:
            document_id: Document's UUID
            alert_type: Type of alert
            
        Returns:
            True if alert has been sent, False otherwise
        """
        alert = await self.get_alert_by_document_and_type(document_id, alert_type)
        return alert is not None


class DocumentExpiryRepository:
    """Repository for document expiry-related queries.
    
    Validates: Requirements 8.1, 8.2
    """

    def __init__(self, db: AsyncSession) -> None:
        """Initialize repository with database session.
        
        Args:
            db: Async database session
        """
        self.db = db

    async def get_documents_expiring_in_days(
        self,
        days: int,
        include_expired: bool = False,
    ) -> List[Document]:
        """Get documents expiring within a certain number of days.
        
        Validates: Requirements 8.1
        
        Args:
            days: Number of days from now
            include_expired: Whether to include already expired documents
            
        Returns:
            List of Document model instances
        """
        from datetime import timedelta
        
        now = datetime.now(timezone.utc)
        target_date = now + timedelta(days=days)
        
        conditions = [
            Document.expiry_date.isnot(None),
            Document.expiry_date <= target_date,
        ]
        
        if not include_expired:
            conditions.append(Document.expiry_date > now)
            conditions.append(Document.is_expired == False)
        
        stmt = select(Document).where(and_(*conditions))
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def get_expired_documents(self) -> List[Document]:
        """Get all documents that have expired but not yet marked.
        
        Validates: Requirements 8.2
        
        Returns:
            List of expired Document model instances
        """
        now = datetime.now(timezone.utc)
        
        stmt = select(Document).where(
            and_(
                Document.expiry_date.isnot(None),
                Document.expiry_date <= now,
                Document.is_expired == False,
            )
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def mark_document_expired(
        self,
        document_id: UUID,
    ) -> Optional[Document]:
        """Mark a document as expired.
        
        Validates: Requirements 8.2
        
        Args:
            document_id: Document's UUID
            
        Returns:
            Updated Document if found, None otherwise
        """
        stmt = (
            update(Document)
            .where(Document.id == document_id)
            .values(is_expired=True)
            .returning(Document)
        )
        result = await self.db.execute(stmt)
        await self.db.flush()
        return result.scalar_one_or_none()

    async def get_documents_needing_alerts(
        self,
        days_before_expiry: int,
    ) -> List[Document]:
        """Get documents that need expiry alerts for a specific day threshold.
        
        Validates: Requirements 8.1
        
        Args:
            days_before_expiry: Number of days before expiry (30, 14, or 7)
            
        Returns:
            List of Document model instances needing alerts
        """
        from datetime import timedelta
        
        now = datetime.now(timezone.utc)
        # Get documents expiring exactly on the target day (within a 24-hour window)
        target_start = now + timedelta(days=days_before_expiry)
        target_end = now + timedelta(days=days_before_expiry + 1)
        
        stmt = select(Document).where(
            and_(
                Document.expiry_date.isnot(None),
                Document.expiry_date >= target_start,
                Document.expiry_date < target_end,
                Document.is_expired == False,
            )
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())
