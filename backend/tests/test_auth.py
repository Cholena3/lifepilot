"""Tests for authentication endpoints.

Validates: Requirements 1.1, 1.2, 1.8
"""

import pytest
from httpx import AsyncClient
from unittest.mock import AsyncMock, patch, MagicMock
from uuid import uuid4
from datetime import datetime, timezone


class TestPasswordHashing:
    """Tests for password hashing functions (Requirement 1.8).
    
    Note: These tests mock bcrypt to avoid environment-specific compatibility
    issues between passlib and bcrypt 4.x.
    """
    
    def test_hash_password_uses_bcrypt_context(self):
        """Password hashing should use bcrypt via passlib context."""
        from app.services.auth import pwd_context
        
        # Verify bcrypt is configured as the hashing scheme
        assert "bcrypt" in pwd_context.schemes()
    
    def test_hash_password_returns_hash(self):
        """Password hashing should return a hash string."""
        with patch("app.services.auth.pwd_context.hash") as mock_hash:
            mock_hash.return_value = "$2b$12$mockedhashvalue1234567890"
            
            from app.services.auth import hash_password
            result = hash_password("SecureP@ss123")
            
            mock_hash.assert_called_once_with("SecureP@ss123")
            assert result.startswith("$2b$")
    
    def test_verify_password_correct(self):
        """Correct password should verify successfully."""
        with patch("app.services.auth.pwd_context.verify") as mock_verify:
            mock_verify.return_value = True
            
            from app.services.auth import verify_password
            result = verify_password("SecureP@ss123", "$2b$12$somehash")
            
            mock_verify.assert_called_once_with("SecureP@ss123", "$2b$12$somehash")
            assert result is True
    
    def test_verify_password_incorrect(self):
        """Incorrect password should fail verification."""
        with patch("app.services.auth.pwd_context.verify") as mock_verify:
            mock_verify.return_value = False
            
            from app.services.auth import verify_password
            result = verify_password("WrongPassword1", "$2b$12$somehash")
            
            assert result is False


class TestUserRegistrationValidation:
    """Tests for registration input validation (Requirement 1.2)."""
    
    @pytest.mark.asyncio
    async def test_register_invalid_email_format(self, client: AsyncClient):
        """Invalid email format should return validation error."""
        response = await client.post(
            "/api/v1/auth/register",
            json={
                "email": "invalid-email",
                "password": "SecureP@ss123",
            },
        )
        
        assert response.status_code == 422
        data = response.json()
        assert "detail" in data
    
    @pytest.mark.asyncio
    async def test_register_email_missing_domain(self, client: AsyncClient):
        """Email without domain should return validation error."""
        response = await client.post(
            "/api/v1/auth/register",
            json={
                "email": "user@",
                "password": "SecureP@ss123",
            },
        )
        
        assert response.status_code == 422
    
    @pytest.mark.asyncio
    async def test_register_password_too_short(self, client: AsyncClient):
        """Password shorter than 8 characters should fail."""
        response = await client.post(
            "/api/v1/auth/register",
            json={
                "email": "user@example.com",
                "password": "Short1",
            },
        )
        
        assert response.status_code == 422
    
    @pytest.mark.asyncio
    async def test_register_password_no_uppercase(self, client: AsyncClient):
        """Password without uppercase should fail."""
        response = await client.post(
            "/api/v1/auth/register",
            json={
                "email": "user@example.com",
                "password": "lowercase123",
            },
        )
        
        assert response.status_code == 422
    
    @pytest.mark.asyncio
    async def test_register_password_no_lowercase(self, client: AsyncClient):
        """Password without lowercase should fail."""
        response = await client.post(
            "/api/v1/auth/register",
            json={
                "email": "user@example.com",
                "password": "UPPERCASE123",
            },
        )
        
        assert response.status_code == 422
    
    @pytest.mark.asyncio
    async def test_register_password_no_digit(self, client: AsyncClient):
        """Password without digit should fail."""
        response = await client.post(
            "/api/v1/auth/register",
            json={
                "email": "user@example.com",
                "password": "NoDigitsHere",
            },
        )
        
        assert response.status_code == 422


class TestUserRegistrationEndpoint:
    """Tests for the registration endpoint (Requirement 1.1)."""
    
    @pytest.mark.asyncio
    async def test_register_success(self, client: AsyncClient):
        """Successful registration should return user and tokens."""
        mock_user = MagicMock()
        mock_user.id = uuid4()
        mock_user.email = "newuser@example.com"
        mock_user.created_at = datetime.now(timezone.utc)
        
        with patch("app.routers.auth.auth_service.register_user") as mock_register:
            from app.schemas.auth import AuthResponse, UserResponse, TokenResponse
            
            mock_register.return_value = AuthResponse(
                user=UserResponse(
                    id=mock_user.id,
                    email=mock_user.email,
                    created_at=mock_user.created_at,
                ),
                tokens=TokenResponse(
                    access_token="mock_access_token",
                    refresh_token="mock_refresh_token",
                    token_type="bearer",
                ),
            )
            
            response = await client.post(
                "/api/v1/auth/register",
                json={
                    "email": "newuser@example.com",
                    "password": "SecureP@ss123",
                },
            )
        
        assert response.status_code == 201
        data = response.json()
        
        assert "user" in data
        assert "tokens" in data
        assert data["user"]["email"] == "newuser@example.com"
        assert data["tokens"]["token_type"] == "bearer"
        assert "access_token" in data["tokens"]
        assert "refresh_token" in data["tokens"]
    
    @pytest.mark.asyncio
    async def test_register_duplicate_email(self, client: AsyncClient):
        """Registration with existing email should return 409."""
        from app.core.exceptions import ConflictError
        
        with patch("app.routers.auth.auth_service.register_user") as mock_register:
            mock_register.side_effect = ConflictError(
                detail="Email already registered",
                field_errors={"email": "This email is already in use"},
            )
            
            response = await client.post(
                "/api/v1/auth/register",
                json={
                    "email": "existing@example.com",
                    "password": "SecureP@ss123",
                },
            )
        
        assert response.status_code == 409


class TestUserLoginEndpoint:
    """Tests for the login endpoint (Requirements 1.1, 1.7, 1.9)."""
    
    @pytest.mark.asyncio
    async def test_login_success(self, client: AsyncClient):
        """Successful login should return user and tokens."""
        mock_user = MagicMock()
        mock_user.id = uuid4()
        mock_user.email = "user@example.com"
        mock_user.created_at = datetime.now(timezone.utc)
        
        with patch("app.routers.auth.auth_service.login_user") as mock_login:
            from app.schemas.auth import AuthResponse, UserResponse, TokenResponse
            
            mock_login.return_value = AuthResponse(
                user=UserResponse(
                    id=mock_user.id,
                    email=mock_user.email,
                    created_at=mock_user.created_at,
                ),
                tokens=TokenResponse(
                    access_token="mock_access_token",
                    refresh_token="mock_refresh_token",
                    token_type="bearer",
                ),
            )
            
            response = await client.post(
                "/api/v1/auth/login",
                json={
                    "email": "user@example.com",
                    "password": "SecureP@ss123",
                },
            )
        
        assert response.status_code == 200
        data = response.json()
        
        assert "user" in data
        assert "tokens" in data
        assert data["user"]["email"] == "user@example.com"
        assert data["tokens"]["token_type"] == "bearer"
        assert "access_token" in data["tokens"]
        assert "refresh_token" in data["tokens"]
    
    @pytest.mark.asyncio
    async def test_login_invalid_email(self, client: AsyncClient):
        """Login with non-existent email should return 401."""
        from app.core.exceptions import AuthenticationError
        
        with patch("app.routers.auth.auth_service.login_user") as mock_login:
            mock_login.side_effect = AuthenticationError(
                message="Invalid email or password"
            )
            
            response = await client.post(
                "/api/v1/auth/login",
                json={
                    "email": "nonexistent@example.com",
                    "password": "SecureP@ss123",
                },
            )
        
        assert response.status_code == 401
    
    @pytest.mark.asyncio
    async def test_login_invalid_password(self, client: AsyncClient):
        """Login with wrong password should return 401."""
        from app.core.exceptions import AuthenticationError
        
        with patch("app.routers.auth.auth_service.login_user") as mock_login:
            mock_login.side_effect = AuthenticationError(
                message="Invalid email or password"
            )
            
            response = await client.post(
                "/api/v1/auth/login",
                json={
                    "email": "user@example.com",
                    "password": "WrongPassword1",
                },
            )
        
        assert response.status_code == 401
    
    @pytest.mark.asyncio
    async def test_login_missing_email(self, client: AsyncClient):
        """Login without email should return validation error."""
        response = await client.post(
            "/api/v1/auth/login",
            json={
                "password": "SecureP@ss123",
            },
        )
        
        assert response.status_code == 422
    
    @pytest.mark.asyncio
    async def test_login_missing_password(self, client: AsyncClient):
        """Login without password should return validation error."""
        response = await client.post(
            "/api/v1/auth/login",
            json={
                "email": "user@example.com",
            },
        )
        
        assert response.status_code == 422


class TestTokenRefreshEndpoint:
    """Tests for the token refresh endpoint (Requirement 1.7)."""
    
    @pytest.mark.asyncio
    async def test_refresh_token_success(self, client: AsyncClient):
        """Successful token refresh should return new tokens."""
        with patch("app.routers.auth.auth_service.refresh_access_token") as mock_refresh:
            from app.schemas.auth import TokenResponse
            
            mock_refresh.return_value = TokenResponse(
                access_token="new_access_token",
                refresh_token="new_refresh_token",
                token_type="bearer",
            )
            
            response = await client.post(
                "/api/v1/auth/refresh",
                json={
                    "refresh_token": "valid_refresh_token",
                },
            )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["token_type"] == "bearer"
        assert "access_token" in data
        assert "refresh_token" in data
    
    @pytest.mark.asyncio
    async def test_refresh_token_invalid(self, client: AsyncClient):
        """Invalid refresh token should return 401."""
        from app.core.exceptions import AuthenticationError
        
        with patch("app.routers.auth.auth_service.refresh_access_token") as mock_refresh:
            mock_refresh.side_effect = AuthenticationError(
                message="Invalid or expired token"
            )
            
            response = await client.post(
                "/api/v1/auth/refresh",
                json={
                    "refresh_token": "invalid_token",
                },
            )
        
        assert response.status_code == 401
    
    @pytest.mark.asyncio
    async def test_refresh_token_expired(self, client: AsyncClient):
        """Expired refresh token should return 401."""
        from app.core.exceptions import AuthenticationError
        
        with patch("app.routers.auth.auth_service.refresh_access_token") as mock_refresh:
            mock_refresh.side_effect = AuthenticationError(
                message="Invalid or expired token"
            )
            
            response = await client.post(
                "/api/v1/auth/refresh",
                json={
                    "refresh_token": "expired_token",
                },
            )
        
        assert response.status_code == 401
    
    @pytest.mark.asyncio
    async def test_refresh_token_missing(self, client: AsyncClient):
        """Missing refresh token should return validation error."""
        response = await client.post(
            "/api/v1/auth/refresh",
            json={},
        )
        
        assert response.status_code == 422


class TestLoginServiceFunctions:
    """Tests for login service functions."""
    
    def test_verify_password_with_valid_credentials(self):
        """Verify password should return True for correct password."""
        with patch("app.services.auth.pwd_context.verify") as mock_verify:
            mock_verify.return_value = True
            
            from app.services.auth import verify_password
            result = verify_password("SecureP@ss123", "$2b$12$validhash")
            
            assert result is True
    
    def test_verify_password_with_invalid_credentials(self):
        """Verify password should return False for incorrect password."""
        with patch("app.services.auth.pwd_context.verify") as mock_verify:
            mock_verify.return_value = False
            
            from app.services.auth import verify_password
            result = verify_password("WrongPassword1", "$2b$12$validhash")
            
            assert result is False
    
    def test_create_tokens_returns_both_tokens(self):
        """Create tokens should return both access and refresh tokens."""
        from app.services.auth import create_tokens
        
        user_id = uuid4()
        email = "test@example.com"
        
        tokens = create_tokens(user_id, email)
        
        assert tokens.access_token is not None
        assert tokens.refresh_token is not None
        assert tokens.token_type == "bearer"
        assert len(tokens.access_token) > 0
        assert len(tokens.refresh_token) > 0
    
    def test_decode_token_valid(self):
        """Decode token should return payload for valid token."""
        from app.services.auth import create_access_token, decode_token
        
        user_id = uuid4()
        token = create_access_token({"sub": str(user_id), "email": "test@example.com"})
        
        payload = decode_token(token)
        
        assert payload["sub"] == str(user_id)
        assert payload["email"] == "test@example.com"
        assert payload["type"] == "access"
    
    def test_decode_token_invalid(self):
        """Decode token should raise AuthenticationError for invalid token."""
        from app.services.auth import decode_token
        from app.core.exceptions import AuthenticationError
        
        with pytest.raises(AuthenticationError):
            decode_token("invalid_token")
