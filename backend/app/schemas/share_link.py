"""Pydantic schemas for document sharing module.

Includes schemas for share link creation, access, and response.

Validates: Requirements 9.1, 9.2, 9.3, 9.4, 9.5, 9.6
"""

from datetime import datetime
from typing import Optional, List
from uuid import UUID

from pydantic import BaseModel, Field, field_validator


class ShareLinkCreate(BaseModel):
    """Schema for creating a new share link.
    
    Validates: Requirements 9.1, 9.2
    """
    
    document_id: UUID = Field(..., description="ID of the document to share")
    expires_in_hours: int = Field(
        default=24,
        ge=1,
        le=720,  # Max 30 days
        description="Number of hours until the link expires (1-720)"
    )
    password: Optional[str] = Field(
        None,
        min_length=4,
        max_length=128,
        description="Optional password to protect the share link"
    )


class ShareLinkResponse(BaseModel):
    """Response schema for a share link.
    
    Validates: Requirements 9.1, 9.2, 9.4, 9.5
    """
    
    id: UUID
    document_id: UUID
    token: str
    share_url: str = Field(..., description="Full URL for accessing the shared document")
    has_password: bool = Field(..., description="Whether the link is password protected")
    expires_at: datetime
    is_revoked: bool
    created_at: datetime
    
    model_config = {"from_attributes": True}


class ShareLinkWithQRResponse(ShareLinkResponse):
    """Response schema for a share link with QR code.
    
    Validates: Requirements 9.3
    """
    
    qr_code_base64: str = Field(..., description="Base64 encoded PNG QR code image")


class ShareLinkAccessRequest(BaseModel):
    """Schema for accessing a share link.
    
    Validates: Requirements 9.2
    """
    
    password: Optional[str] = Field(
        None,
        description="Password if the share link is protected"
    )


class ShareLinkAccessLogResponse(BaseModel):
    """Response schema for share link access log entry.
    
    Validates: Requirements 9.6
    """
    
    id: UUID
    share_link_id: UUID
    ip_address: str
    user_agent: Optional[str] = None
    accessed_at: datetime
    
    model_config = {"from_attributes": True}


class ShareLinkDetailResponse(ShareLinkResponse):
    """Detailed response schema for a share link with access logs.
    
    Validates: Requirements 9.6
    """
    
    access_count: int = Field(..., description="Total number of accesses")
    accesses: List[ShareLinkAccessLogResponse] = Field(
        default_factory=list,
        description="List of access log entries"
    )


class ShareLinkListResponse(BaseModel):
    """Response schema for listing share links for a document."""
    
    document_id: UUID
    share_links: List[ShareLinkResponse]
    total: int


class DocumentAccessResponse(BaseModel):
    """Response schema for accessing a shared document.
    
    Contains document metadata and download information.
    """
    
    document_id: UUID
    title: str
    category: str
    content_type: str
    file_size: int
    download_url: str = Field(..., description="URL to download the document")


class QRCodeResponse(BaseModel):
    """Response schema for QR code generation.
    
    Validates: Requirements 9.3
    """
    
    share_link_id: UUID
    qr_code_base64: str = Field(..., description="Base64 encoded PNG QR code image")
    share_url: str
