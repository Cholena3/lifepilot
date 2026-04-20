"""Celery tasks for document expiry processing.

Validates: Requirements 8.1, 8.2, 8.3
"""

import asyncio
import logging
from datetime import datetime, timezone
from typing import Optional
from uuid import UUID

from app.tasks import celery_app

logger = logging.getLogger(__name__)


def run_async(coro):
    """Helper to run async code in sync context."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


@celery_app.task(
    name="app.tasks.document_expiry_tasks.check_document_expiry",
)
def check_document_expiry() -> dict:
    """Periodic task to check documents for expiry and send alerts.
    
    Validates: Requirements 8.1, 8.2
    
    This task:
    1. Marks documents as expired if their expiry date has passed
    2. Sends alerts at 30, 14, and 7 days before expiry
    
    Returns:
        Dict with success status and statistics
    """
    async def _check():
        from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
        from sqlalchemy.orm import sessionmaker
        
        from app.core.config import get_settings
        from app.services.document_expiry import DocumentExpiryService
        
        settings = get_settings()
        engine = create_async_engine(str(settings.database_url))
        async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
        
        async with async_session() as db:
            try:
                service = DocumentExpiryService(db)
                result = await service.check_and_send_expiry_alerts()
                
                await db.commit()
                
                logger.info(
                    f"Document expiry check completed: "
                    f"checked={result.documents_checked}, "
                    f"alerts_sent={result.alerts_sent}, "
                    f"marked_expired={result.documents_marked_expired}"
                )
                
                return {
                    "success": True,
                    "documents_checked": result.documents_checked,
                    "alerts_sent": result.alerts_sent,
                    "documents_marked_expired": result.documents_marked_expired,
                    "errors": result.errors,
                }
                
            except Exception as e:
                logger.exception(f"Error checking document expiry: {e}")
                await db.rollback()
                return {"success": False, "error": str(e)}
    
    return run_async(_check())


@celery_app.task(
    name="app.tasks.document_expiry_tasks.send_expiry_alert_for_document",
    bind=True,
    max_retries=3,
    default_retry_delay=60,
)
def send_expiry_alert_for_document(
    self,
    document_id: str,
    days_before_expiry: int,
) -> dict:
    """Send an expiry alert for a specific document.
    
    Validates: Requirements 8.1
    
    Args:
        document_id: UUID of the document
        days_before_expiry: Number of days before expiry (30, 14, or 7)
        
    Returns:
        Dict with success status and details
    """
    async def _send():
        from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
        from sqlalchemy.orm import sessionmaker
        
        from app.core.config import get_settings
        from app.repositories.document import DocumentRepository
        from app.services.document_expiry import DocumentExpiryService
        
        settings = get_settings()
        engine = create_async_engine(str(settings.database_url))
        async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
        
        async with async_session() as db:
            try:
                doc_repo = DocumentRepository(db)
                document = await doc_repo.get_document_by_id(UUID(document_id))
                
                if document is None:
                    logger.error(f"Document {document_id} not found")
                    return {"success": False, "error": "Document not found"}
                
                service = DocumentExpiryService(db)
                alert = await service.send_expiry_alert(document, days_before_expiry)
                
                await db.commit()
                
                if alert:
                    return {
                        "success": True,
                        "alert_id": str(alert.id),
                        "document_id": document_id,
                        "days_before_expiry": days_before_expiry,
                    }
                else:
                    return {
                        "success": False,
                        "message": "Alert not sent (already sent or disabled)",
                        "document_id": document_id,
                    }
                
            except Exception as e:
                logger.exception(f"Error sending expiry alert for document {document_id}: {e}")
                await db.rollback()
                raise self.retry(exc=e)
    
    return run_async(_send())


@celery_app.task(
    name="app.tasks.document_expiry_tasks.reschedule_document_alerts",
    bind=True,
    max_retries=3,
    default_retry_delay=60,
)
def reschedule_document_alerts(
    self,
    document_id: str,
) -> dict:
    """Reschedule expiry alerts when a document's expiry date is updated.
    
    Validates: Requirements 8.3
    
    Args:
        document_id: UUID of the document
        
    Returns:
        Dict with success status and details
    """
    async def _reschedule():
        from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
        from sqlalchemy.orm import sessionmaker
        
        from app.core.config import get_settings
        from app.services.document_expiry import DocumentExpiryService
        
        settings = get_settings()
        engine = create_async_engine(str(settings.database_url))
        async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
        
        async with async_session() as db:
            try:
                service = DocumentExpiryService(db)
                deleted_count = await service.reschedule_alerts_for_document(UUID(document_id))
                
                await db.commit()
                
                logger.info(
                    f"Rescheduled alerts for document {document_id}: "
                    f"deleted {deleted_count} existing alerts"
                )
                
                return {
                    "success": True,
                    "document_id": document_id,
                    "alerts_deleted": deleted_count,
                }
                
            except Exception as e:
                logger.exception(f"Error rescheduling alerts for document {document_id}: {e}")
                await db.rollback()
                raise self.retry(exc=e)
    
    return run_async(_reschedule())


@celery_app.task(
    name="app.tasks.document_expiry_tasks.mark_expired_documents",
)
def mark_expired_documents() -> dict:
    """Mark all expired documents.
    
    Validates: Requirements 8.2
    
    Returns:
        Dict with success status and count of marked documents
    """
    async def _mark():
        from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
        from sqlalchemy.orm import sessionmaker
        
        from app.core.config import get_settings
        from app.services.document_expiry import DocumentExpiryService
        
        settings = get_settings()
        engine = create_async_engine(str(settings.database_url))
        async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
        
        async with async_session() as db:
            try:
                service = DocumentExpiryService(db)
                marked_docs = await service.mark_expired_documents()
                
                await db.commit()
                
                logger.info(f"Marked {len(marked_docs)} documents as expired")
                
                return {
                    "success": True,
                    "documents_marked": len(marked_docs),
                    "document_ids": [str(doc.id) for doc in marked_docs],
                }
                
            except Exception as e:
                logger.exception(f"Error marking expired documents: {e}")
                await db.rollback()
                return {"success": False, "error": str(e)}
    
    return run_async(_mark())
