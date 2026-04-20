"""Celery tasks for OCR document processing.

Validates: Requirements 7.1, 7.2, 7.3, 7.4, 7.5
"""

import asyncio
import logging
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
    name="app.tasks.ocr_tasks.process_document_ocr",
    bind=True,
    max_retries=2,
    default_retry_delay=30,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_backoff_max=120,
)
def process_document_ocr(
    self,
    document_id: str,
    user_id: str,
    file_path: str,
    category: str,
) -> dict:
    """Process a document for OCR text extraction asynchronously.
    
    Validates: Requirements 7.1, 7.2, 7.3, 7.4, 7.5
    
    This task:
    1. Retrieves the document file from storage
    2. Processes it through Google Cloud Vision API
    3. Extracts structured fields based on document category
    4. Stores OCR results for search indexing
    5. On failure, marks document for manual review and notifies user
    
    Args:
        document_id: UUID of the document to process
        user_id: UUID of the document owner
        file_path: Path to the document in storage
        category: Document category (Identity, Education, etc.)
        
    Returns:
        Dict with processing status and results
    """
    async def _process():
        from sqlalchemy import update
        from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
        from sqlalchemy.orm import sessionmaker
        
        from app.core.config import get_settings
        from app.models.document import Document
        from app.models.notification import NotificationChannel
        from app.services.notification import NotificationService
        from app.services.ocr import OCRProcessingError, OCRService, OCRStatus
        
        settings = get_settings()
        engine = create_async_engine(str(settings.database_url))
        async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
        
        async with async_session() as db:
            try:
                logger.info(f"Starting OCR processing for document {document_id}")
                
                # Initialize OCR service
                ocr_service = OCRService()
                
                # Retrieve file content from storage
                from app.core import storage
                try:
                    file_content = await storage.download_file(file_path)
                except Exception as e:
                    logger.error(f"Failed to download file {file_path}: {e}")
                    raise OCRProcessingError(f"Failed to retrieve file: {e}", UUID(document_id))
                
                # Process document through OCR
                result = await ocr_service.process_document(
                    doc_id=UUID(document_id),
                    file_content=file_content,
                    category=category,
                )
                
                # Update document with OCR results
                # Validates: Requirements 7.2
                stmt = (
                    update(Document)
                    .where(Document.id == UUID(document_id))
                    .values(
                        ocr_text=result.raw_text,
                    )
                )
                await db.execute(stmt)
                await db.commit()
                
                logger.info(f"OCR processing completed for document {document_id}")
                
                return {
                    "success": True,
                    "document_id": document_id,
                    "status": result.status.value,
                    "text_length": len(result.raw_text),
                    "confidence": result.confidence,
                    "extracted_fields": result.extracted_fields,
                }
                
            except OCRProcessingError as e:
                logger.error(f"OCR processing failed for document {document_id}: {e}")
                
                # Mark document for manual review
                # Validates: Requirements 7.5
                await _mark_for_manual_review(db, document_id, str(e))
                
                # Notify user of failure
                # Validates: Requirements 7.5
                await _notify_user_ocr_failure(db, user_id, document_id)
                
                await db.commit()
                
                return {
                    "success": False,
                    "document_id": document_id,
                    "status": OCRStatus.MANUAL_REVIEW.value,
                    "error": str(e),
                }
                
            except Exception as e:
                logger.exception(f"Unexpected error processing document {document_id}: {e}")
                
                # Check if we should retry
                if self.request.retries < self.max_retries:
                    raise self.retry(exc=e)
                
                # Max retries exceeded - mark for manual review
                # Validates: Requirements 7.5
                await _mark_for_manual_review(db, document_id, f"Max retries exceeded: {e}")
                await _notify_user_ocr_failure(db, user_id, document_id)
                await db.commit()
                
                return {
                    "success": False,
                    "document_id": document_id,
                    "status": OCRStatus.FAILED.value,
                    "error": str(e),
                }
    
    return run_async(_process())


async def _mark_for_manual_review(db, document_id: str, error_message: str) -> None:
    """Mark a document for manual review after OCR failure.
    
    Validates: Requirements 7.5
    
    Args:
        db: Database session
        document_id: UUID of the document
        error_message: Error message describing the failure
    """
    from sqlalchemy import update
    
    from app.models.document import Document
    
    # Update document to indicate manual review needed
    # We store the error in ocr_text field with a prefix
    stmt = (
        update(Document)
        .where(Document.id == UUID(document_id))
        .values(
            ocr_text=f"[MANUAL_REVIEW_REQUIRED] {error_message}",
        )
    )
    await db.execute(stmt)
    
    logger.info(f"Document {document_id} marked for manual review")


async def _notify_user_ocr_failure(db, user_id: str, document_id: str) -> None:
    """Notify user that OCR processing failed for their document.
    
    Validates: Requirements 7.5
    
    Args:
        db: Database session
        user_id: UUID of the document owner
        document_id: UUID of the document
    """
    from app.models.notification import NotificationChannel
    from app.services.notification import NotificationService
    
    try:
        notification_service = NotificationService(db)
        
        await notification_service.send_with_fallback(
            user_id=UUID(user_id),
            title="Document Processing Failed",
            body=(
                "We couldn't automatically process your document. "
                "It has been marked for manual review. "
                "You can still search and access the document, but extracted text may be limited."
            ),
            channels=[
                NotificationChannel.PUSH,
                NotificationChannel.EMAIL,
            ],
        )
        
        logger.info(f"Sent OCR failure notification to user {user_id}")
        
    except Exception as e:
        # Don't fail the task if notification fails
        logger.error(f"Failed to send OCR failure notification to user {user_id}: {e}")


@celery_app.task(
    name="app.tasks.ocr_tasks.reprocess_failed_documents",
)
def reprocess_failed_documents() -> dict:
    """Periodic task to retry OCR processing for failed documents.
    
    Validates: Requirements 7.5
    
    Returns:
        Dict with count of documents queued for reprocessing
    """
    async def _reprocess():
        from sqlalchemy import select
        from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
        from sqlalchemy.orm import sessionmaker
        
        from app.core.config import get_settings
        from app.models.document import Document
        
        settings = get_settings()
        engine = create_async_engine(str(settings.database_url))
        async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
        
        async with async_session() as db:
            try:
                # Find documents marked for manual review that haven't been processed
                stmt = (
                    select(Document)
                    .where(Document.ocr_text.like("[MANUAL_REVIEW_REQUIRED]%"))
                    .limit(10)  # Process in batches
                )
                result = await db.execute(stmt)
                documents = list(result.scalars().all())
                
                queued_count = 0
                for doc in documents:
                    # Queue for reprocessing
                    process_document_ocr.delay(
                        document_id=str(doc.id),
                        user_id=str(doc.user_id),
                        file_path=doc.file_path,
                        category=doc.category,
                    )
                    queued_count += 1
                
                return {
                    "success": True,
                    "documents_queued": queued_count,
                }
                
            except Exception as e:
                logger.exception(f"Error reprocessing failed documents: {e}")
                return {"success": False, "error": str(e)}
    
    return run_async(_reprocess())


@celery_app.task(
    name="app.tasks.ocr_tasks.extract_identity_fields",
    bind=True,
    max_retries=2,
)
def extract_identity_fields(
    self,
    document_id: str,
    ocr_text: str,
) -> dict:
    """Extract identity fields from OCR text.
    
    Validates: Requirements 7.3
    
    Args:
        document_id: UUID of the document
        ocr_text: Raw OCR text to extract fields from
        
    Returns:
        Dict with extracted identity fields
    """
    async def _extract():
        from app.services.ocr import OCRService
        
        try:
            ocr_service = OCRService()
            fields = await ocr_service.extract_identity_fields(ocr_text)
            
            return {
                "success": True,
                "document_id": document_id,
                "fields": {
                    "name": fields.name,
                    "document_number": fields.document_number,
                    "expiry_date": fields.expiry_date.isoformat() if fields.expiry_date else None,
                    "date_of_birth": fields.date_of_birth.isoformat() if fields.date_of_birth else None,
                    "document_type": fields.document_type,
                    "confidence": fields.confidence,
                },
            }
            
        except Exception as e:
            logger.exception(f"Error extracting identity fields for document {document_id}: {e}")
            return {
                "success": False,
                "document_id": document_id,
                "error": str(e),
            }
    
    return run_async(_extract())


@celery_app.task(
    name="app.tasks.ocr_tasks.extract_education_fields",
    bind=True,
    max_retries=2,
)
def extract_education_fields(
    self,
    document_id: str,
    ocr_text: str,
) -> dict:
    """Extract education fields from OCR text.
    
    Validates: Requirements 7.4
    
    Args:
        document_id: UUID of the document
        ocr_text: Raw OCR text to extract fields from
        
    Returns:
        Dict with extracted education fields
    """
    async def _extract():
        from app.services.ocr import OCRService
        
        try:
            ocr_service = OCRService()
            fields = await ocr_service.extract_education_fields(ocr_text)
            
            return {
                "success": True,
                "document_id": document_id,
                "fields": {
                    "institution_name": fields.institution_name,
                    "degree": fields.degree,
                    "field_of_study": fields.field_of_study,
                    "start_date": fields.start_date.isoformat() if fields.start_date else None,
                    "end_date": fields.end_date.isoformat() if fields.end_date else None,
                    "grade": fields.grade,
                    "confidence": fields.confidence,
                },
            }
            
        except Exception as e:
            logger.exception(f"Error extracting education fields for document {document_id}: {e}")
            return {
                "success": False,
                "document_id": document_id,
                "error": str(e),
            }
    
    return run_async(_extract())


@celery_app.task(
    name="app.tasks.ocr_tasks.process_receipt_ocr",
    bind=True,
    max_retries=2,
    default_retry_delay=30,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_backoff_max=120,
)
def process_receipt_ocr(
    self,
    expense_id: str,
    user_id: str,
    receipt_path: str,
) -> dict:
    """Process a receipt image for OCR and extract expense details.
    
    Validates: Requirements 10.2, 10.3
    
    This task:
    1. Retrieves the receipt image from storage
    2. Processes it through Google Cloud Vision API
    3. Extracts merchant name, amount, and date
    4. Updates the expense with OCR data for pre-filling
    
    Args:
        expense_id: UUID of the expense
        user_id: UUID of the expense owner
        receipt_path: Path to the receipt in storage
        
    Returns:
        Dict with processing status and extracted fields
    """
    async def _process():
        from sqlalchemy import update
        from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
        from sqlalchemy.orm import sessionmaker
        
        from app.core.config import get_settings
        from app.models.expense import Expense
        from app.services.ocr import OCRProcessingError, OCRService
        
        settings = get_settings()
        engine = create_async_engine(str(settings.database_url))
        async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
        
        async with async_session() as db:
            try:
                logger.info(f"Starting receipt OCR processing for expense {expense_id}")
                
                # Initialize OCR service
                ocr_service = OCRService()
                
                # Retrieve receipt from storage
                from app.core import storage
                try:
                    file_content = await storage.download_file(receipt_path)
                except Exception as e:
                    logger.error(f"Failed to download receipt {receipt_path}: {e}")
                    raise OCRProcessingError(f"Failed to retrieve receipt: {e}")
                
                # Process receipt through OCR
                fields = await ocr_service.process_receipt(file_content)
                
                # Prepare OCR data for storage
                ocr_data = {
                    "merchant_name": fields.merchant_name,
                    "amount": float(fields.amount) if fields.amount else None,
                    "transaction_date": fields.transaction_date.isoformat() if fields.transaction_date else None,
                    "currency": fields.currency,
                    "items": fields.items,
                    "confidence": fields.confidence,
                }
                
                # Update expense with OCR data
                # Validates: Requirements 10.3
                stmt = (
                    update(Expense)
                    .where(Expense.id == UUID(expense_id))
                    .values(ocr_data=ocr_data)
                )
                await db.execute(stmt)
                await db.commit()
                
                logger.info(f"Receipt OCR completed for expense {expense_id}")
                
                return {
                    "success": True,
                    "expense_id": expense_id,
                    "extracted_fields": ocr_data,
                }
                
            except OCRProcessingError as e:
                logger.error(f"Receipt OCR failed for expense {expense_id}: {e}")
                return {
                    "success": False,
                    "expense_id": expense_id,
                    "error": str(e),
                }
                
            except Exception as e:
                logger.exception(f"Unexpected error processing receipt for expense {expense_id}: {e}")
                
                # Check if we should retry
                if self.request.retries < self.max_retries:
                    raise self.retry(exc=e)
                
                return {
                    "success": False,
                    "expense_id": expense_id,
                    "error": str(e),
                }
    
    return run_async(_process())


@celery_app.task(
    name="app.tasks.ocr_tasks.extract_receipt_fields",
    bind=True,
    max_retries=2,
)
def extract_receipt_fields(
    self,
    ocr_text: str,
) -> dict:
    """Extract receipt fields from OCR text.
    
    Validates: Requirements 10.2
    
    Args:
        ocr_text: Raw OCR text to extract fields from
        
    Returns:
        Dict with extracted receipt fields
    """
    async def _extract():
        from app.services.ocr import OCRService
        
        try:
            ocr_service = OCRService()
            fields = await ocr_service.extract_receipt_fields(ocr_text)
            
            return {
                "success": True,
                "fields": {
                    "merchant_name": fields.merchant_name,
                    "amount": float(fields.amount) if fields.amount else None,
                    "transaction_date": fields.transaction_date.isoformat() if fields.transaction_date else None,
                    "currency": fields.currency,
                    "items": fields.items,
                    "confidence": fields.confidence,
                },
            }
            
        except Exception as e:
            logger.exception(f"Error extracting receipt fields: {e}")
            return {
                "success": False,
                "error": str(e),
            }
    
    return run_async(_extract())


@celery_app.task(
    name="app.tasks.ocr_tasks.process_prescription_ocr",
    bind=True,
    max_retries=2,
    default_retry_delay=30,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_backoff_max=120,
)
def process_prescription_ocr(
    self,
    health_record_id: str,
    user_id: str,
    file_path: str,
) -> dict:
    """Process a prescription image for OCR and extract medicine details.
    
    Validates: Requirements 14.3, 14.4
    
    This task:
    1. Retrieves the prescription image from storage
    2. Processes it through Google Cloud Vision API
    3. Extracts doctor name, medicines, dosage, and frequency
    4. Updates the health record with OCR data
    5. Prepares medicine data for tracker integration (task 11.5)
    
    Args:
        health_record_id: UUID of the health record
        user_id: UUID of the health record owner
        file_path: Path to the prescription in storage
        
    Returns:
        Dict with processing status and extracted fields
    """
    async def _process():
        from sqlalchemy import update
        from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
        from sqlalchemy.orm import sessionmaker
        
        from app.core.config import get_settings
        from app.models.health import HealthRecord
        from app.services.ocr import OCRProcessingError, OCRService
        
        settings = get_settings()
        engine = create_async_engine(str(settings.database_url))
        async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
        
        async with async_session() as db:
            try:
                logger.info(f"Starting prescription OCR processing for health record {health_record_id}")
                
                # Initialize OCR service
                ocr_service = OCRService()
                
                # Retrieve prescription from storage
                from app.core import storage
                try:
                    file_content = await storage.download_file(file_path)
                except Exception as e:
                    logger.error(f"Failed to download prescription {file_path}: {e}")
                    raise OCRProcessingError(f"Failed to retrieve prescription: {e}")
                
                # Process prescription through OCR
                fields = await ocr_service.process_prescription(file_content)
                
                # Prepare extracted data for storage
                medicines_data = []
                for med in fields.medicines:
                    medicines_data.append({
                        "name": med.name,
                        "dosage": med.dosage,
                        "frequency": med.frequency,
                        "duration": med.duration,
                        "instructions": med.instructions,
                        "confidence": med.confidence,
                    })
                
                extracted_data = {
                    "doctor_name": fields.doctor_name,
                    "hospital_name": fields.hospital_name,
                    "patient_name": fields.patient_name,
                    "prescription_date": fields.prescription_date.isoformat() if fields.prescription_date else None,
                    "diagnosis": fields.diagnosis,
                    "medicines": medicines_data,
                    "confidence": fields.confidence,
                }
                
                # Get raw text for search indexing
                raw_text, _ = await ocr_service.vision_client.detect_text(file_content)
                
                # Update health record with OCR data
                stmt = (
                    update(HealthRecord)
                    .where(HealthRecord.id == UUID(health_record_id))
                    .values(
                        ocr_text=raw_text,
                        extracted_data=extracted_data,
                        doctor_name=fields.doctor_name,
                    )
                )
                await db.execute(stmt)
                await db.commit()
                
                logger.info(
                    f"Prescription OCR completed for health record {health_record_id}: "
                    f"doctor={fields.doctor_name}, medicines_count={len(medicines_data)}"
                )
                
                return {
                    "success": True,
                    "health_record_id": health_record_id,
                    "extracted_fields": extracted_data,
                    "medicines_count": len(medicines_data),
                }
                
            except OCRProcessingError as e:
                logger.error(f"Prescription OCR failed for health record {health_record_id}: {e}")
                
                # Mark for manual review
                await _mark_health_record_for_review(db, health_record_id, str(e))
                await db.commit()
                
                return {
                    "success": False,
                    "health_record_id": health_record_id,
                    "error": str(e),
                }
                
            except Exception as e:
                logger.exception(f"Unexpected error processing prescription for health record {health_record_id}: {e}")
                
                # Check if we should retry
                if self.request.retries < self.max_retries:
                    raise self.retry(exc=e)
                
                # Max retries exceeded - mark for manual review
                await _mark_health_record_for_review(db, health_record_id, f"Max retries exceeded: {e}")
                await db.commit()
                
                return {
                    "success": False,
                    "health_record_id": health_record_id,
                    "error": str(e),
                }
    
    return run_async(_process())


async def _mark_health_record_for_review(db, health_record_id: str, error_message: str) -> None:
    """Mark a health record for manual review after OCR failure.
    
    Validates: Requirements 14.3
    
    Args:
        db: Database session
        health_record_id: UUID of the health record
        error_message: Error message describing the failure
    """
    from sqlalchemy import update
    
    from app.models.health import HealthRecord
    
    stmt = (
        update(HealthRecord)
        .where(HealthRecord.id == UUID(health_record_id))
        .values(
            ocr_text=f"[MANUAL_REVIEW_REQUIRED] {error_message}",
        )
    )
    await db.execute(stmt)
    
    logger.info(f"Health record {health_record_id} marked for manual review")


@celery_app.task(
    name="app.tasks.ocr_tasks.extract_prescription_fields",
    bind=True,
    max_retries=2,
)
def extract_prescription_fields(
    self,
    ocr_text: str,
) -> dict:
    """Extract prescription fields from OCR text.
    
    Validates: Requirements 14.3, 14.4
    
    Args:
        ocr_text: Raw OCR text to extract fields from
        
    Returns:
        Dict with extracted prescription fields
    """
    async def _extract():
        from app.services.ocr import OCRService
        
        try:
            ocr_service = OCRService()
            fields = await ocr_service.extract_prescription_fields(ocr_text)
            
            medicines_data = []
            for med in fields.medicines:
                medicines_data.append({
                    "name": med.name,
                    "dosage": med.dosage,
                    "frequency": med.frequency,
                    "duration": med.duration,
                    "instructions": med.instructions,
                    "confidence": med.confidence,
                })
            
            return {
                "success": True,
                "fields": {
                    "doctor_name": fields.doctor_name,
                    "hospital_name": fields.hospital_name,
                    "patient_name": fields.patient_name,
                    "prescription_date": fields.prescription_date.isoformat() if fields.prescription_date else None,
                    "diagnosis": fields.diagnosis,
                    "medicines": medicines_data,
                    "confidence": fields.confidence,
                },
            }
            
        except Exception as e:
            logger.exception(f"Error extracting prescription fields: {e}")
            return {
                "success": False,
                "error": str(e),
            }
    
    return run_async(_extract())
