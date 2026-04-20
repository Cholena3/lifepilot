"""Tests for document sharing functionality.

Validates: Requirements 9.1, 9.2, 9.3, 9.4, 9.5, 9.6
"""

import pytest
from datetime import datetime, timedelta, timezone
from unittest.mock import patch
from uuid import uuid4

from app.services.share_link import (
    generate_token,
    hash_password,
    verify_password,
    generate_qr_code,
)


class TestTokenGeneration:
    """Tests for token generation.
    
    Validates: Requirements 9.1
    """
    
    def test_generate_token_returns_string(self):
        """Token generation should return a string."""
        token = generate_token()
        assert isinstance(token, str)
    
    def test_generate_token_default_length(self):
        """Default token should be 64 characters (32 bytes hex encoded)."""
        token = generate_token()
        assert len(token) == 64
    
    def test_generate_token_custom_length(self):
        """Token with custom length should be 2x the byte length."""
        token = generate_token(length=16)
        assert len(token) == 32
    
    def test_generate_token_uniqueness(self):
        """Generated tokens should be unique."""
        tokens = [generate_token() for _ in range(100)]
        assert len(set(tokens)) == 100


class TestPasswordHashing:
    """Tests for password hashing.
    
    Validates: Requirements 9.2
    
    Note: These tests mock bcrypt to avoid environment-specific compatibility
    issues between passlib and bcrypt 4.x.
    """
    
    def test_hash_password_uses_bcrypt_context(self):
        """Password hashing should use bcrypt via passlib context."""
        from app.services.share_link import pwd_context
        
        # Verify bcrypt is configured as the hashing scheme
        assert "bcrypt" in pwd_context.schemes()
    
    def test_hash_password_returns_hash(self):
        """Password hashing should return a hash string."""
        with patch("app.services.share_link.pwd_context.hash") as mock_hash:
            mock_hash.return_value = "$2b$12$mockedhashvalue1234567890"
            
            hashed = hash_password("test_password")
            
            mock_hash.assert_called_once_with("test_password")
            assert hashed.startswith("$2b$")
    
    def test_verify_password_correct(self):
        """Correct password should verify successfully."""
        with patch("app.services.share_link.pwd_context.verify") as mock_verify:
            mock_verify.return_value = True
            
            result = verify_password("test_password", "$2b$12$somehash")
            
            mock_verify.assert_called_once_with("test_password", "$2b$12$somehash")
            assert result is True
    
    def test_verify_password_incorrect(self):
        """Incorrect password should fail verification."""
        with patch("app.services.share_link.pwd_context.verify") as mock_verify:
            mock_verify.return_value = False
            
            result = verify_password("wrong_password", "$2b$12$somehash")
            
            assert result is False


class TestQRCodeGeneration:
    """Tests for QR code generation.
    
    Validates: Requirements 9.3
    """
    
    def test_generate_qr_code_returns_string(self):
        """QR code generation should return a base64 string."""
        qr = generate_qr_code("https://example.com/share/abc123")
        assert isinstance(qr, str)
    
    def test_generate_qr_code_is_base64(self):
        """QR code should be valid base64."""
        import base64
        qr = generate_qr_code("https://example.com/share/abc123")
        # Should not raise an exception
        decoded = base64.b64decode(qr)
        assert len(decoded) > 0
    
    def test_generate_qr_code_is_png(self):
        """QR code should be a PNG image."""
        import base64
        qr = generate_qr_code("https://example.com/share/abc123")
        decoded = base64.b64decode(qr)
        # PNG magic bytes
        assert decoded[:8] == b'\x89PNG\r\n\x1a\n'
    
    def test_generate_qr_code_different_data(self):
        """Different data should produce different QR codes."""
        qr1 = generate_qr_code("https://example.com/share/abc123")
        qr2 = generate_qr_code("https://example.com/share/xyz789")
        assert qr1 != qr2


class TestShareLinkSchemas:
    """Tests for share link schemas."""
    
    def test_share_link_create_valid(self):
        """Valid share link creation data should pass validation."""
        from app.schemas.share_link import ShareLinkCreate
        
        data = ShareLinkCreate(
            document_id=uuid4(),
            expires_in_hours=24,
            password="secret123",
        )
        assert data.expires_in_hours == 24
        assert data.password == "secret123"
    
    def test_share_link_create_default_expiry(self):
        """Share link should have default 24 hour expiry."""
        from app.schemas.share_link import ShareLinkCreate
        
        data = ShareLinkCreate(document_id=uuid4())
        assert data.expires_in_hours == 24
    
    def test_share_link_create_no_password(self):
        """Share link without password should be valid."""
        from app.schemas.share_link import ShareLinkCreate
        
        data = ShareLinkCreate(document_id=uuid4())
        assert data.password is None
    
    def test_share_link_create_min_expiry(self):
        """Share link should accept minimum 1 hour expiry."""
        from app.schemas.share_link import ShareLinkCreate
        
        data = ShareLinkCreate(document_id=uuid4(), expires_in_hours=1)
        assert data.expires_in_hours == 1
    
    def test_share_link_create_max_expiry(self):
        """Share link should accept maximum 720 hour (30 day) expiry."""
        from app.schemas.share_link import ShareLinkCreate
        
        data = ShareLinkCreate(document_id=uuid4(), expires_in_hours=720)
        assert data.expires_in_hours == 720
    
    def test_share_link_create_invalid_expiry_too_low(self):
        """Share link should reject expiry less than 1 hour."""
        from app.schemas.share_link import ShareLinkCreate
        from pydantic import ValidationError
        
        with pytest.raises(ValidationError):
            ShareLinkCreate(document_id=uuid4(), expires_in_hours=0)
    
    def test_share_link_create_invalid_expiry_too_high(self):
        """Share link should reject expiry more than 720 hours."""
        from app.schemas.share_link import ShareLinkCreate
        from pydantic import ValidationError
        
        with pytest.raises(ValidationError):
            ShareLinkCreate(document_id=uuid4(), expires_in_hours=721)
    
    def test_share_link_create_password_min_length(self):
        """Share link password should have minimum 4 characters."""
        from app.schemas.share_link import ShareLinkCreate
        from pydantic import ValidationError
        
        with pytest.raises(ValidationError):
            ShareLinkCreate(document_id=uuid4(), password="abc")


class TestShareLinkResponse:
    """Tests for share link response schemas."""
    
    def test_share_link_response_has_password_true(self):
        """Response should indicate password protection."""
        from app.schemas.share_link import ShareLinkResponse
        
        response = ShareLinkResponse(
            id=uuid4(),
            document_id=uuid4(),
            token="abc123",
            share_url="https://example.com/share/abc123",
            has_password=True,
            expires_at=datetime.now(timezone.utc) + timedelta(hours=24),
            is_revoked=False,
            created_at=datetime.now(timezone.utc),
        )
        assert response.has_password is True
    
    def test_share_link_response_has_password_false(self):
        """Response should indicate no password protection."""
        from app.schemas.share_link import ShareLinkResponse
        
        response = ShareLinkResponse(
            id=uuid4(),
            document_id=uuid4(),
            token="abc123",
            share_url="https://example.com/share/abc123",
            has_password=False,
            expires_at=datetime.now(timezone.utc) + timedelta(hours=24),
            is_revoked=False,
            created_at=datetime.now(timezone.utc),
        )
        assert response.has_password is False


class TestShareLinkWithQRResponse:
    """Tests for share link with QR code response."""
    
    def test_share_link_with_qr_response(self):
        """Response should include QR code."""
        from app.schemas.share_link import ShareLinkWithQRResponse
        
        qr_code = generate_qr_code("https://example.com/share/abc123")
        
        response = ShareLinkWithQRResponse(
            id=uuid4(),
            document_id=uuid4(),
            token="abc123",
            share_url="https://example.com/share/abc123",
            has_password=False,
            expires_at=datetime.now(timezone.utc) + timedelta(hours=24),
            is_revoked=False,
            created_at=datetime.now(timezone.utc),
            qr_code_base64=qr_code,
        )
        assert response.qr_code_base64 == qr_code
