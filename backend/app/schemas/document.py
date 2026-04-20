"""Pydantic schemas for document module.

Includes schemas for document creation, update, response, and search.

Validates: Requirements 6.7
"""

from datetime import datetime
from typing import Optional, List, Generic, TypeVar
from uuid import UUID

from pydantic import BaseModel, Field, field_validator


T = TypeVar("T")


class DocumentCategory:
    """Valid document categories."""
    IDENTITY = "Identity"
    EDUCATION = "Education"
    CAREER = "Career"
    FINANCE = "Finance"
    
    ALL = [IDENTITY, EDUCATION, CAREER, FINANCE]


class DocumentVersionResponse(BaseModel):
    """Response schema for document version."""
    
    id: UUID
    document_id: UUID
    version_number: int = Field(..., ge=1, description="Version number (1-indexed)")
    file_path: str
    file_size: int = Field(..., ge=0, description="File size in bytes")
    content_type: str
    created_at: datetime
    
    model_config = {"from_attributes": True}


class DocumentCreate(BaseModel):
    """Schema for creating a new document."""
    
    title: str = Field(..., min_length=1, max_length=255)
    category: str = Field(..., description="Document category")
    content_type: str = Field(..., description="MIME type of the document")
    file_size: int = Field(..., ge=0, description="File size in bytes")
    expiry_date: Optional[datetime] = None
    
    @field_validator("category")
    @classmethod
    def validate_category(cls, v: str) -> str:
        """Validate that category is one of the allowed values."""
        if v not in DocumentCategory.ALL:
            raise ValueError(f"Category must be one of: {', '.join(DocumentCategory.ALL)}")
        return v


class DocumentUpdate(BaseModel):
    """Schema for updating a document (creates new version)."""
    
    title: Optional[str] = Field(None, min_length=1, max_length=255)
    category: Optional[str] = None
    content_type: Optional[str] = None
    file_size: Optional[int] = Field(None, ge=0)
    expiry_date: Optional[datetime] = None
    
    @field_validator("category")
    @classmethod
    def validate_category(cls, v: Optional[str]) -> Optional[str]:
        """Validate that category is one of the allowed values."""
        if v is not None and v not in DocumentCategory.ALL:
            raise ValueError(f"Category must be one of: {', '.join(DocumentCategory.ALL)}")
        return v


class DocumentResponse(BaseModel):
    """Response schema for a document."""
    
    id: UUID
    user_id: UUID
    title: str
    category: str
    file_path: str
    content_type: str
    file_size: int
    expiry_date: Optional[datetime] = None
    is_expired: bool = False
    ocr_text: Optional[str] = None
    current_version: int
    created_at: datetime
    updated_at: datetime
    
    model_config = {"from_attributes": True}


class DocumentWithVersionsResponse(DocumentResponse):
    """Response schema for a document with its version history."""
    
    versions: List[DocumentVersionResponse] = []


class VersionHistoryResponse(BaseModel):
    """Response schema for document version history."""
    
    document_id: UUID
    total_versions: int
    versions: List[DocumentVersionResponse]


class DocumentSearchQuery(BaseModel):
    """Schema for document search query parameters.
    
    Validates: Requirements 6.7
    """
    
    query: str = Field(
        ...,
        min_length=1,
        max_length=500,
        description="Search query string"
    )
    category: Optional[str] = Field(
        None,
        description="Optional category filter"
    )
    page: int = Field(
        default=1,
        ge=1,
        description="Page number (1-indexed)"
    )
    page_size: int = Field(
        default=20,
        ge=1,
        le=100,
        description="Number of results per page"
    )
    
    @field_validator("category")
    @classmethod
    def validate_category(cls, v: Optional[str]) -> Optional[str]:
        """Validate that category is one of the allowed values."""
        if v is not None and v not in DocumentCategory.ALL:
            raise ValueError(f"Category must be one of: {', '.join(DocumentCategory.ALL)}")
        return v


class PaginatedResponse(BaseModel, Generic[T]):
    """Generic paginated response schema."""
    
    items: List[T]
    total: int = Field(..., ge=0, description="Total number of items")
    page: int = Field(..., ge=1, description="Current page number")
    page_size: int = Field(..., ge=1, description="Number of items per page")
    total_pages: int = Field(..., ge=0, description="Total number of pages")
    
    @classmethod
    def create(
        cls,
        items: List[T],
        total: int,
        page: int,
        page_size: int,
    ) -> "PaginatedResponse[T]":
        """Create a paginated response.
        
        Args:
            items: List of items for current page
            total: Total number of items
            page: Current page number
            page_size: Number of items per page
            
        Returns:
            PaginatedResponse instance
        """
        total_pages = (total + page_size - 1) // page_size if total > 0 else 0
        return cls(
            items=items,
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
        )


class DocumentSearchResponse(BaseModel):
    """Response schema for document search results.
    
    Validates: Requirements 6.7
    """
    
    id: UUID
    user_id: UUID
    title: str
    category: str
    content_type: str
    file_size: int
    expiry_date: Optional[datetime] = None
    is_expired: bool = False
    ocr_text: Optional[str] = None
    current_version: int
    created_at: datetime
    updated_at: datetime
    
    model_config = {"from_attributes": True}
