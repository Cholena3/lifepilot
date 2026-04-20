"""Document expiry service for managing document expiry alerts.

Validates: Requirements 8.1, 8.2, 8.3, 8.4
"""

import logging
from datetime import datetime, timedelta, timezone
from typing import List, Optional
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.document import Document
from app.models.document_expiry import (
    DocumentExpiryAlert,
    DocumentExpiryAlertPreferences,
    ExpiryAlertType,
)
from app.models.notification import NotificationChannel
from app.repositories.document_expiry import (
    DocumentExpiryAlertPreferencesRepository,
    DocumentExpiryAlertRepository,
    DocumentExpiryRepository,
)
from app.schemas.document_expiry import (
    DocumentExpiryAlertPreferencesCreate,
    DocumentExpiryAlertPreferencesUpdate,
    DocumentExpiryCheckResult,
    ExpiringDocumentInfo,
)
from app.services.notification import NotificationService

logger = logging.getLogger(__name__)


# Mapping of days to alert types
DAYS_TO_ALERT_TYPE = {
    30: ExpiryAlertType.DAYS_30,
    14: ExpiryAlertType.DAYS_14,
    7: ExpiryAlertType.DAYS_7,
}

# Alert thresholds in days
ALERT_THRESHOLDS = [30, 14, 7]


class DocumentExpiryService:
    """Service for managing document expiry alerts.
    
    Validates: Requirements 8.1, 8.2, 8.3, 8.4
    """

    def __init__(self, db: AsyncSession) -> None:
        """Initialize document expiry service.
        
        Args:
            db: Async database session
        """
        self.db = db
        self.preferences_repo = DocumentExpiryAlertPreferencesRepository(db)
        self.alert_repo = DocumentExpiryAlertRepository(db)
        self.expiry_repo = DocumentExpiryRepository(db)
        self.notification_service = NotificationService(db)

    # ==================== Preferences Management ====================

    async def get_preferences(
        self,
        user_id: UUID,
        category: str,
    ) -> DocumentExpiryAlertPreferences:
        """Get expiry alert preferences for a user and category.
        
        Validates: Requirements 8.4
        
        Args:
            user_id: User's UUID
            category: Document category
            
        Returns:
            DocumentExpiryAlertPreferences model instance
        """
        return await self.preferences_repo.get_or_create_preferences(user_id, category)

    async def get_all_preferences(
        self,
        user_id: UUID,
    ) -> List[DocumentExpiryAlertPreferences]:
        """Get all expiry alert preferences for a user.
        
        Validates: Requirements 8.4
        
        Args:
            user_id: User's UUID
            
        Returns:
            List of DocumentExpiryAlertPreferences model instances
        """
        return await self.preferences_repo.get_all_preferences_by_user(user_id)

    async def update_preferences(
        self,
        user_id: UUID,
        category: str,
        data: DocumentExpiryAlertPreferencesUpdate,
    ) -> DocumentExpiryAlertPreferences:
        """Update expiry alert preferences.
        
        Validates: Requirements 8.4
        
        Args:
            user_id: User's UUID
            category: Document category
            data: Update data
            
        Returns:
            Updated DocumentExpiryAlertPreferences model instance
        """
        # Ensure preferences exist
        await self.preferences_repo.get_or_create_preferences(user_id, category)
        
        # Update preferences
        update_data = data.model_dump(exclude_unset=True)
        preferences = await self.preferences_repo.update_preferences(
            user_id, category, **update_data
        )
        
        if preferences is None:
            return await self.preferences_repo.get_or_create_preferences(user_id, category)
        
        return preferences

    async def create_preferences(
        self,
        user_id: UUID,
        data: DocumentExpiryAlertPreferencesCreate,
    ) -> DocumentExpiryAlertPreferences:
        """Create expiry alert preferences.
        
        Validates: Requirements 8.4
        
        Args:
            user_id: User's UUID
            data: Creation data
            
        Returns:
            Created DocumentExpiryAlertPreferences model instance
        """
        return await self.preferences_repo.create_preferences(
            user_id=user_id,
            category=data.category,
            alerts_enabled=data.alerts_enabled,
            alert_30_days=data.alert_30_days,
            alert_14_days=data.alert_14_days,
            alert_7_days=data.alert_7_days,
        )

    # ==================== Alert Checking ====================

    async def should_send_alert(
        self,
        user_id: UUID,
        document: Document,
        days_before_expiry: int,
    ) -> bool:
        """Check if an alert should be sent for a document.
        
        Validates: Requirements 8.1, 8.4
        
        Args:
            user_id: User's UUID
            document: Document model instance
            days_before_expiry: Number of days before expiry
            
        Returns:
            True if alert should be sent, False otherwise
        """
        if document.expiry_date is None:
            return False
        
        if document.is_expired:
            return False
        
        # Get alert type
        alert_type = DAYS_TO_ALERT_TYPE.get(days_before_expiry)
        if alert_type is None:
            return False
        
        # Check if alert has already been sent
        if await self.alert_repo.has_alert_been_sent(document.id, alert_type):
            return False
        
        # Check user preferences
        preferences = await self.preferences_repo.get_preferences_by_user_and_category(
            user_id, document.category
        )
        
        if preferences is None:
            # Default: send alerts
            return True
        
        if not preferences.alerts_enabled:
            return False
        
        # Check specific alert preference
        if days_before_expiry == 30:
            return preferences.alert_30_days
        elif days_before_expiry == 14:
            return preferences.alert_14_days
        elif days_before_expiry == 7:
            return preferences.alert_7_days
        
        return False

    async def get_documents_needing_alerts(
        self,
        days_before_expiry: int,
    ) -> List[Document]:
        """Get documents that need expiry alerts.
        
        Validates: Requirements 8.1
        
        Args:
            days_before_expiry: Number of days before expiry
            
        Returns:
            List of Document model instances
        """
        return await self.expiry_repo.get_documents_needing_alerts(days_before_expiry)

    # ==================== Alert Sending ====================

    async def send_expiry_alert(
        self,
        document: Document,
        days_before_expiry: int,
    ) -> Optional[DocumentExpiryAlert]:
        """Send an expiry alert for a document.
        
        Validates: Requirements 8.1
        
        Args:
            document: Document model instance
            days_before_expiry: Number of days before expiry
            
        Returns:
            Created DocumentExpiryAlert if sent, None otherwise
        """
        if not await self.should_send_alert(document.user_id, document, days_before_expiry):
            return None
        
        alert_type = DAYS_TO_ALERT_TYPE.get(days_before_expiry)
        if alert_type is None:
            return None
        
        # Format expiry date for notification
        expiry_date_str = document.expiry_date.strftime("%B %d, %Y") if document.expiry_date else "Unknown"
        
        # Create notification
        title = f"Document Expiring in {days_before_expiry} Days"
        body = (
            f"Your document '{document.title}' ({document.category}) "
            f"will expire on {expiry_date_str}. "
            f"Please renew it before the expiry date."
        )
        
        try:
            # Send notification via preferred channel (default to push)
            result = await self.notification_service.send_notification(
                user_id=document.user_id,
                title=title,
                body=body,
                channel=NotificationChannel.PUSH,
            )
            
            notification_id = result.notification_id if result.success else None
            
            # Record the alert
            alert = await self.alert_repo.create_alert(
                document_id=document.id,
                user_id=document.user_id,
                alert_type=alert_type,
                notification_id=notification_id,
            )
            
            logger.info(
                f"Sent {days_before_expiry}-day expiry alert for document {document.id} "
                f"to user {document.user_id}"
            )
            
            return alert
            
        except Exception as e:
            logger.exception(f"Error sending expiry alert for document {document.id}: {e}")
            return None

    # ==================== Expiry Processing ====================

    async def mark_expired_documents(self) -> List[Document]:
        """Mark all expired documents.
        
        Validates: Requirements 8.2
        
        Returns:
            List of documents that were marked as expired
        """
        expired_docs = await self.expiry_repo.get_expired_documents()
        marked_docs = []
        
        for doc in expired_docs:
            updated_doc = await self.expiry_repo.mark_document_expired(doc.id)
            if updated_doc:
                marked_docs.append(updated_doc)
                logger.info(f"Marked document {doc.id} as expired")
        
        return marked_docs

    async def check_and_send_expiry_alerts(self) -> DocumentExpiryCheckResult:
        """Check all documents and send expiry alerts as needed.
        
        Validates: Requirements 8.1, 8.2
        
        This is the main method called by the Celery Beat scheduled task.
        
        Returns:
            DocumentExpiryCheckResult with statistics
        """
        documents_checked = 0
        alerts_sent = 0
        documents_marked_expired = 0
        errors: List[str] = []
        
        # First, mark expired documents
        try:
            marked_docs = await self.mark_expired_documents()
            documents_marked_expired = len(marked_docs)
        except Exception as e:
            error_msg = f"Error marking expired documents: {str(e)}"
            logger.exception(error_msg)
            errors.append(error_msg)
        
        # Then, send alerts for each threshold
        for days in ALERT_THRESHOLDS:
            try:
                documents = await self.get_documents_needing_alerts(days)
                documents_checked += len(documents)
                
                for doc in documents:
                    try:
                        alert = await self.send_expiry_alert(doc, days)
                        if alert:
                            alerts_sent += 1
                    except Exception as e:
                        error_msg = f"Error sending alert for document {doc.id}: {str(e)}"
                        logger.exception(error_msg)
                        errors.append(error_msg)
                        
            except Exception as e:
                error_msg = f"Error getting documents for {days}-day alert: {str(e)}"
                logger.exception(error_msg)
                errors.append(error_msg)
        
        return DocumentExpiryCheckResult(
            documents_checked=documents_checked,
            alerts_sent=alerts_sent,
            documents_marked_expired=documents_marked_expired,
            errors=errors,
        )

    # ==================== Rescheduling ====================

    async def reschedule_alerts_for_document(
        self,
        document_id: UUID,
    ) -> int:
        """Reschedule expiry alerts when a document's expiry date is updated.
        
        Validates: Requirements 8.3
        
        Deletes all existing alerts for the document so new alerts can be sent
        based on the new expiry date.
        
        Args:
            document_id: Document's UUID
            
        Returns:
            Number of alerts deleted
        """
        deleted_count = await self.alert_repo.delete_alerts_by_document(document_id)
        
        if deleted_count > 0:
            logger.info(
                f"Rescheduled alerts for document {document_id}: "
                f"deleted {deleted_count} existing alerts"
            )
        
        return deleted_count

    # ==================== Utility Methods ====================

    async def get_expiring_documents_info(
        self,
        user_id: UUID,
        days: int = 30,
    ) -> List[ExpiringDocumentInfo]:
        """Get information about documents expiring within a certain number of days.
        
        Args:
            user_id: User's UUID
            days: Number of days to look ahead
            
        Returns:
            List of ExpiringDocumentInfo
        """
        from sqlalchemy import and_, select
        
        now = datetime.now(timezone.utc)
        target_date = now + timedelta(days=days)
        
        stmt = select(Document).where(
            and_(
                Document.user_id == user_id,
                Document.expiry_date.isnot(None),
                Document.expiry_date <= target_date,
            )
        ).order_by(Document.expiry_date.asc())
        
        result = await self.db.execute(stmt)
        documents = list(result.scalars().all())
        
        expiring_docs = []
        for doc in documents:
            if doc.expiry_date:
                days_until = (doc.expiry_date - now).days
                expiring_docs.append(ExpiringDocumentInfo(
                    document_id=doc.id,
                    user_id=doc.user_id,
                    title=doc.title,
                    category=doc.category,
                    expiry_date=doc.expiry_date,
                    days_until_expiry=days_until,
                    is_expired=doc.is_expired or days_until < 0,
                ))
        
        return expiring_docs

    async def get_alerts_for_document(
        self,
        document_id: UUID,
    ) -> List[DocumentExpiryAlert]:
        """Get all expiry alerts for a document.
        
        Args:
            document_id: Document's UUID
            
        Returns:
            List of DocumentExpiryAlert model instances
        """
        return await self.alert_repo.get_alerts_by_document(document_id)
