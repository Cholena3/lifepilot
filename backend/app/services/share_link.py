"""Share link service for document sharing functionality.

Provides functionality for creating, accessing, and revoking share links
with password protection, QR code generation, and access logging.

Validates: Requirements 9.1, 9.2, 9.3, 9.4, 9.5, 9.6
"""

import base64
import io
import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional
from uuid import UUID

from passlib.context import CryptContext
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AuthenticationError, NotFoundError
from app.models.share_link import ShareLink
from app.repositories.document import DocumentRepository
from app.repositories.share_link import ShareLinkRepository
from app.schemas.share_link import (
    DocumentAccessResponse,
    QRCodeResponse,
    ShareLinkCreate,
    ShareLinkDetailResponse,
    ShareLinkListResponse,
    ShareLinkResponse,
    ShareLinkWithQRResponse,
    ShareLinkAccessLogResponse,
)

# Password hashing context using bcrypt
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Base URL for share links (should be configured via environment)
SHARE_LINK_BASE_URL = "https://lifepilot.app/share"


def generate_token(length: int = 32) -> str:
    """Generate a cryptographically secure random token.
    
    Validates: Requirements 9.1
    
    Args:
        length: Length of the token in bytes (will be hex encoded)
        
    Returns:
        Hex-encoded random token
    """
    return secrets.token_hex(length)


def hash_password(password: str) -> str:
    """Hash a password using bcrypt.
    
    Validates: Requirements 9.2
    
    Args:
        password: Plain text password
        
    Returns:
        Bcrypt hash of the password
    """
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash.
    
    Validates: Requirements 9.2
    
    Args:
        plain_password: Plain text password to verify
        hashed_password: Bcrypt hash to verify against
        
    Returns:
        True if password matches, False otherwise
    """
    return pwd_context.verify(plain_password, hashed_password)


def generate_qr_code(data: str) -> str:
    """Generate a QR code as base64 encoded PNG.
    
    Validates: Requirements 9.3
    
    Args:
        data: Data to encode in the QR code
        
    Returns:
        Base64 encoded PNG image
    """
    try:
        import qrcode
        from qrcode.image.pil import PilImage
    except ImportError:
        # Fallback: return empty string if qrcode not installed
        return ""
    
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=4,
    )
    qr.add_data(data)
    qr.make(fit=True)
    
    img = qr.make_image(fill_color="black", back_color="white")
    
    # Convert to base64
    buffer = io.BytesIO()
    img.save(buffer, format="PNG")
    buffer.seek(0)
    
    return base64.b64encode(buffer.getvalue()).decode("utf-8")


class ShareLinkService:
    """Service for managing document share links.
    
    Validates: Requirements 9.1, 9.2, 9.3, 9.4, 9.5, 9.6
    """
    
    def __init__(
        self,
        db: AsyncSession,
        base_url: str = SHARE_LINK_BASE_URL,
    ) -> None:
        """Initialize service with database session.
        
        Args:
            db: Async database session
            base_url: Base URL for share links
        """
        self.db = db
        self.base_url = base_url
        self.repo = ShareLinkRepository(db)
        self.doc_repo = DocumentRepository(db)
    
    def _build_share_url(self, token: str) -> str:
        """Build the full share URL for a token.
        
        Args:
            token: Share link token
            
        Returns:
            Full share URL
        """
        return f"{self.base_url}/{token}"
    
    async def _generate_unique_token(self) -> str:
        """Generate a unique token that doesn't exist in the database.
        
        Validates: Requirements 9.1
        
        Returns:
            Unique token string
        """
        max_attempts = 10
        for _ in range(max_attempts):
            token = generate_token()
            if not await self.repo.token_exists(token):
                return token
        # Extremely unlikely to reach here
        raise RuntimeError("Failed to generate unique token")
    
    async def create_share_link(
        self,
        user_id: UUID,
        data: ShareLinkCreate,
        include_qr: bool = False,
    ) -> ShareLinkResponse | ShareLinkWithQRResponse:
        """Create a new share link for a document.
        
        Validates: Requirements 9.1, 9.2, 9.3
        
        Args:
            user_id: User's UUID
            data: Share link creation data
            include_qr: Whether to include QR code in response
            
        Returns:
            ShareLinkResponse or ShareLinkWithQRResponse
            
        Raises:
            NotFoundError: If document not found or not owned by user
        """
        # Verify document exists and belongs to user
        document = await self.doc_repo.get_document_by_id(data.document_id, user_id)
        if not document:
            raise NotFoundError(resource="Document", identifier=str(data.document_id))
        
        # Generate unique token
        token = await self._generate_unique_token()
        
        # Calculate expiration time
        expires_at = datetime.now(timezone.utc) + timedelta(hours=data.expires_in_hours)
        
        # Hash password if provided
        password_hash = None
        if data.password:
            password_hash = hash_password(data.password)
        
        # Create share link
        share_link = await self.repo.create_share_link(
            document_id=data.document_id,
            user_id=user_id,
            token=token,
            expires_at=expires_at,
            password_hash=password_hash,
        )
        
        share_url = self._build_share_url(token)
        
        response_data = {
            "id": share_link.id,
            "document_id": share_link.document_id,
            "token": share_link.token,
            "share_url": share_url,
            "has_password": share_link.password_hash is not None,
            "expires_at": share_link.expires_at,
            "is_revoked": share_link.is_revoked,
            "created_at": share_link.created_at,
        }
        
        if include_qr:
            qr_code = generate_qr_code(share_url)
            return ShareLinkWithQRResponse(
                **response_data,
                qr_code_base64=qr_code,
            )
        
        return ShareLinkResponse(**response_data)
    
    async def access_share_link(
        self,
        token: str,
        password: Optional[str],
        ip_address: str,
        user_agent: Optional[str] = None,
    ) -> DocumentAccessResponse:
        """Access a shared document via share link.
        
        Validates: Requirements 9.2, 9.4, 9.5, 9.6
        
        Args:
            token: Share link token
            password: Password if link is protected
            ip_address: IP address of the accessor
            user_agent: User agent string
            
        Returns:
            DocumentAccessResponse with document info
            
        Raises:
            NotFoundError: If share link not found, expired, or revoked
            AuthenticationError: If password is required but not provided or incorrect
        """
        # Get share link
        share_link = await self.repo.get_share_link_by_token(token)
        
        if not share_link:
            raise NotFoundError(resource="Share link", identifier=token)
        
        # Check if revoked (Requirement 9.5)
        if share_link.is_revoked:
            raise NotFoundError(resource="Share link", identifier=token)
        
        # Check if expired (Requirement 9.4)
        if datetime.now(timezone.utc) > share_link.expires_at:
            raise NotFoundError(resource="Share link", identifier=token)
        
        # Verify password if required (Requirement 9.2)
        if share_link.password_hash:
            if not password:
                raise AuthenticationError("Password required to access this document")
            if not verify_password(password, share_link.password_hash):
                raise AuthenticationError("Invalid password")
        
        # Log access (Requirement 9.6)
        await self.repo.log_access(
            share_link_id=share_link.id,
            ip_address=ip_address,
            user_agent=user_agent,
        )
        
        # Get document
        document = share_link.document
        
        # Build download URL (in production, this would be a signed URL)
        download_url = f"/api/documents/{document.id}/download?share_token={token}"
        
        return DocumentAccessResponse(
            document_id=document.id,
            title=document.title,
            category=document.category,
            content_type=document.content_type,
            file_size=document.file_size,
            download_url=download_url,
        )
    
    async def revoke_share_link(
        self,
        user_id: UUID,
        share_link_id: UUID,
    ) -> ShareLinkResponse:
        """Revoke a share link.
        
        Validates: Requirements 9.5
        
        Args:
            user_id: User's UUID
            share_link_id: ShareLink's UUID
            
        Returns:
            Updated ShareLinkResponse
            
        Raises:
            NotFoundError: If share link not found or not owned by user
        """
        share_link = await self.repo.get_share_link_by_id(share_link_id, user_id)
        
        if not share_link:
            raise NotFoundError(resource="Share link", identifier=str(share_link_id))
        
        share_link = await self.repo.revoke_share_link(share_link)
        
        return ShareLinkResponse(
            id=share_link.id,
            document_id=share_link.document_id,
            token=share_link.token,
            share_url=self._build_share_url(share_link.token),
            has_password=share_link.password_hash is not None,
            expires_at=share_link.expires_at,
            is_revoked=share_link.is_revoked,
            created_at=share_link.created_at,
        )
    
    async def get_share_link(
        self,
        user_id: UUID,
        share_link_id: UUID,
        include_accesses: bool = False,
    ) -> ShareLinkResponse | ShareLinkDetailResponse:
        """Get a share link by ID.
        
        Args:
            user_id: User's UUID
            share_link_id: ShareLink's UUID
            include_accesses: Whether to include access logs
            
        Returns:
            ShareLinkResponse or ShareLinkDetailResponse
            
        Raises:
            NotFoundError: If share link not found or not owned by user
        """
        share_link = await self.repo.get_share_link_by_id(share_link_id, user_id)
        
        if not share_link:
            raise NotFoundError(resource="Share link", identifier=str(share_link_id))
        
        response_data = {
            "id": share_link.id,
            "document_id": share_link.document_id,
            "token": share_link.token,
            "share_url": self._build_share_url(share_link.token),
            "has_password": share_link.password_hash is not None,
            "expires_at": share_link.expires_at,
            "is_revoked": share_link.is_revoked,
            "created_at": share_link.created_at,
        }
        
        if include_accesses:
            accesses = await self.repo.get_access_logs(share_link_id)
            access_count = await self.repo.count_accesses(share_link_id)
            
            return ShareLinkDetailResponse(
                **response_data,
                access_count=access_count,
                accesses=[
                    ShareLinkAccessLogResponse(
                        id=a.id,
                        share_link_id=a.share_link_id,
                        ip_address=a.ip_address,
                        user_agent=a.user_agent,
                        accessed_at=a.accessed_at,
                    )
                    for a in accesses
                ],
            )
        
        return ShareLinkResponse(**response_data)
    
    async def list_share_links(
        self,
        user_id: UUID,
        document_id: UUID,
        include_revoked: bool = False,
    ) -> ShareLinkListResponse:
        """List all share links for a document.
        
        Args:
            user_id: User's UUID
            document_id: Document's UUID
            include_revoked: Whether to include revoked links
            
        Returns:
            ShareLinkListResponse with list of share links
            
        Raises:
            NotFoundError: If document not found or not owned by user
        """
        # Verify document exists and belongs to user
        document = await self.doc_repo.get_document_by_id(document_id, user_id)
        if not document:
            raise NotFoundError(resource="Document", identifier=str(document_id))
        
        share_links = await self.repo.get_share_links_by_document(
            document_id=document_id,
            user_id=user_id,
            include_revoked=include_revoked,
        )
        
        return ShareLinkListResponse(
            document_id=document_id,
            share_links=[
                ShareLinkResponse(
                    id=sl.id,
                    document_id=sl.document_id,
                    token=sl.token,
                    share_url=self._build_share_url(sl.token),
                    has_password=sl.password_hash is not None,
                    expires_at=sl.expires_at,
                    is_revoked=sl.is_revoked,
                    created_at=sl.created_at,
                )
                for sl in share_links
            ],
            total=len(share_links),
        )
    
    async def generate_qr_code(
        self,
        user_id: UUID,
        share_link_id: UUID,
    ) -> QRCodeResponse:
        """Generate a QR code for a share link.
        
        Validates: Requirements 9.3
        
        Args:
            user_id: User's UUID
            share_link_id: ShareLink's UUID
            
        Returns:
            QRCodeResponse with base64 encoded QR code
            
        Raises:
            NotFoundError: If share link not found or not owned by user
        """
        share_link = await self.repo.get_share_link_by_id(share_link_id, user_id)
        
        if not share_link:
            raise NotFoundError(resource="Share link", identifier=str(share_link_id))
        
        share_url = self._build_share_url(share_link.token)
        qr_code = generate_qr_code(share_url)
        
        return QRCodeResponse(
            share_link_id=share_link.id,
            qr_code_base64=qr_code,
            share_url=share_url,
        )
    
    async def delete_share_link(
        self,
        user_id: UUID,
        share_link_id: UUID,
    ) -> None:
        """Delete a share link.
        
        Args:
            user_id: User's UUID
            share_link_id: ShareLink's UUID
            
        Raises:
            NotFoundError: If share link not found or not owned by user
        """
        share_link = await self.repo.get_share_link_by_id(share_link_id, user_id)
        
        if not share_link:
            raise NotFoundError(resource="Share link", identifier=str(share_link_id))
        
        await self.repo.delete_share_link(share_link)
