"""Pydantic schemas for OCR processing.

Validates: Requirements 7.1, 7.2, 7.3, 7.4, 7.5, 14.3, 14.4
"""

from datetime import date
from typing import Optional, List
from uuid import UUID

from pydantic import BaseModel, Field


class IdentityFieldsResponse(BaseModel):
    """Response schema for extracted identity document fields.
    
    Validates: Requirements 7.3
    """
    name: Optional[str] = Field(None, description="Extracted name from document")
    document_number: Optional[str] = Field(None, description="Document number (passport, Aadhaar, PAN, etc.)")
    expiry_date: Optional[date] = Field(None, description="Document expiry date")
    date_of_birth: Optional[date] = Field(None, description="Date of birth if present")
    document_type: Optional[str] = Field(None, description="Type of identity document detected")
    confidence: float = Field(0.0, ge=0.0, le=1.0, description="Extraction confidence score")


class EducationFieldsResponse(BaseModel):
    """Response schema for extracted education document fields.
    
    Validates: Requirements 7.4
    """
    institution_name: Optional[str] = Field(None, description="Name of educational institution")
    degree: Optional[str] = Field(None, description="Degree or qualification")
    field_of_study: Optional[str] = Field(None, description="Field or major of study")
    start_date: Optional[date] = Field(None, description="Start date of education")
    end_date: Optional[date] = Field(None, description="End/graduation date")
    grade: Optional[str] = Field(None, description="Grade, GPA, or classification")
    confidence: float = Field(0.0, ge=0.0, le=1.0, description="Extraction confidence score")


class OCRResultResponse(BaseModel):
    """Response schema for OCR processing result.
    
    Validates: Requirements 7.1, 7.2
    """
    document_id: UUID
    status: str = Field(..., description="OCR processing status")
    raw_text: Optional[str] = Field(None, description="Raw extracted text")
    text_length: int = Field(0, ge=0, description="Length of extracted text")
    confidence: float = Field(0.0, ge=0.0, le=1.0, description="Overall OCR confidence")
    identity_fields: Optional[IdentityFieldsResponse] = None
    education_fields: Optional[EducationFieldsResponse] = None
    extracted_fields: dict = Field(default_factory=dict, description="All extracted fields as dict")
    error_message: Optional[str] = Field(None, description="Error message if processing failed")


class OCRTaskResponse(BaseModel):
    """Response schema for OCR task submission.
    
    Validates: Requirements 7.1
    """
    task_id: str = Field(..., description="Celery task ID for tracking")
    document_id: UUID
    status: str = Field("queued", description="Task status")
    message: str = Field("OCR processing queued", description="Status message")


class OCRStatusResponse(BaseModel):
    """Response schema for OCR task status check."""
    task_id: str
    status: str = Field(..., description="Task status (pending, processing, completed, failed)")
    result: Optional[OCRResultResponse] = None
    error: Optional[str] = None


# ============================================================================
# Prescription OCR Schemas
# ============================================================================

class MedicineInfoResponse(BaseModel):
    """Response schema for extracted medicine information.
    
    Validates: Requirements 14.3, 14.4
    """
    name: str = Field(..., description="Medicine name")
    dosage: Optional[str] = Field(None, description="Dosage (e.g., 500mg)")
    frequency: Optional[str] = Field(None, description="Frequency (e.g., twice daily)")
    duration: Optional[str] = Field(None, description="Duration (e.g., 5 days)")
    instructions: Optional[str] = Field(None, description="Additional instructions")
    confidence: float = Field(0.0, ge=0.0, le=1.0, description="Extraction confidence score")


class PrescriptionFieldsResponse(BaseModel):
    """Response schema for extracted prescription fields.
    
    Validates: Requirements 14.3, 14.4
    """
    doctor_name: Optional[str] = Field(None, description="Doctor's name")
    hospital_name: Optional[str] = Field(None, description="Hospital/clinic name")
    patient_name: Optional[str] = Field(None, description="Patient's name")
    prescription_date: Optional[date] = Field(None, description="Prescription date")
    diagnosis: Optional[str] = Field(None, description="Diagnosis or condition")
    medicines: List[MedicineInfoResponse] = Field(default_factory=list, description="List of medicines")
    confidence: float = Field(0.0, ge=0.0, le=1.0, description="Overall extraction confidence")


class PrescriptionOCRResultResponse(BaseModel):
    """Response schema for prescription OCR processing result.
    
    Validates: Requirements 14.3, 14.4
    """
    health_record_id: UUID
    status: str = Field(..., description="OCR processing status")
    raw_text: Optional[str] = Field(None, description="Raw extracted text")
    prescription_fields: Optional[PrescriptionFieldsResponse] = None
    medicines_count: int = Field(0, ge=0, description="Number of medicines extracted")
    error_message: Optional[str] = Field(None, description="Error message if processing failed")


class PrescriptionOCRTaskResponse(BaseModel):
    """Response schema for prescription OCR task submission.
    
    Validates: Requirements 14.3
    """
    task_id: str = Field(..., description="Celery task ID for tracking")
    health_record_id: UUID
    status: str = Field("queued", description="Task status")
    message: str = Field("Prescription OCR processing queued", description="Status message")


class MedicineTrackerEntryCreate(BaseModel):
    """Schema for creating medicine tracker entries from OCR data.
    
    Validates: Requirements 14.4
    
    This schema is used to auto-create medicine tracker entries
    from extracted prescription data.
    """
    name: str = Field(..., min_length=1, max_length=255, description="Medicine name")
    dosage: Optional[str] = Field(None, max_length=100, description="Dosage")
    frequency: Optional[str] = Field(None, max_length=100, description="Frequency")
    duration_days: Optional[int] = Field(None, ge=1, description="Duration in days")
    instructions: Optional[str] = Field(None, max_length=500, description="Instructions")
    health_record_id: Optional[UUID] = Field(None, description="Source health record ID")
