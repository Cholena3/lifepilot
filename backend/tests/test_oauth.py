"""Tests for Google OAuth authentication.

Validates: Requirements 1.3
"""

import pytest
from httpx import AsyncClient
from unittest.mock import AsyncMock, patch, MagicMock
from uuid import uuid4
from datetime import datetime, timezone


class TestGoogleOAuthUrl:
    """Tests for Google OAuth URL generation (Requirement 1.3)."""
    
    @pytest.mark.asyncio
    async def test_get_google_auth_url_success(self, client: AsyncClient):
        """GET /auth/google should return OAuth URL and state."""
        response = await client.get("/api/v1/auth/google")
        
        assert response.status_code == 200
        data = response.json()
        
        assert "auth_url" in data
        assert "state" in data
        assert "accounts.google.com" in data["auth_url"]
        assert len(data["state"]) > 0
    
    @pytest.mark.asyncio
    async def test_google_auth_url_contains_required_params(self, client: AsyncClient):
        """OAuth URL should contain required parameters."""
        response = await client.get("/api/v1/auth/google")
        
        assert response.status_code == 200
        data = response.json()
        auth_url = data["auth_url"]
        
        # Check required OAuth parameters are present
        assert "client_id=" in auth_url
        assert "redirect_uri=" in auth_url
        assert "response_type=code" in auth_url
        assert "scope=" in auth_url
        assert "state=" in auth_url


class TestGoogleOAuthCallback:
    """Tests for Google OAuth callback handling (Requirement 1.3)."""
    
    @pytest.mark.asyncio
    async def test_google_callback_success_new_user(self, client: AsyncClient):
        """Successful OAuth callback should create new user and return tokens."""
        mock_user = MagicMock()
        mock_user.id = uuid4()
        mock_user.email = "googleuser@gmail.com"
        mock_user.created_at = datetime.now(timezone.utc)
        
        with patch("app.routers.auth.oauth_service.exchange_google_code") as mock_exchange, \
             patch("app.routers.auth.oauth_service.get_google_user_info") as mock_user_info, \
             patch("app.routers.auth.oauth_service.oauth_login_or_create") as mock_login:
            
            mock_exchange.return_value = {"access_token": "google_access_token"}
            mock_user_info.return_value = {
                "id": "google_user_123",
                "email": "googleuser@gmail.com",
            }
            
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
            
            response = await client.get(
                "/api/v1/auth/google/callback",
                params={"code": "auth_code_123", "state": "state_123"},
            )
        
        assert response.status_code == 200
        data = response.json()
        
        assert "user" in data
        assert "tokens" in data
        assert data["user"]["email"] == "googleuser@gmail.com"
        assert data["tokens"]["token_type"] == "bearer"
    
    @pytest.mark.asyncio
    async def test_google_callback_invalid_code(self, client: AsyncClient):
        """Invalid authorization code should return 401."""
        from app.core.exceptions import AuthenticationError
        
        with patch("app.routers.auth.oauth_service.exchange_google_code") as mock_exchange:
            mock_exchange.side_effect = AuthenticationError(
                message="Failed to exchange authorization code"
            )
            
            response = await client.get(
                "/api/v1/auth/google/callback",
                params={"code": "invalid_code"},
            )
        
        assert response.status_code == 401
    
    @pytest.mark.asyncio
    async def test_google_callback_missing_code(self, client: AsyncClient):
        """Missing authorization code should return validation error."""
        response = await client.get("/api/v1/auth/google/callback")
        
        assert response.status_code == 422


class TestOAuthService:
    """Tests for OAuth service functions (Requirement 1.3)."""
    
    def test_get_google_auth_url_generates_valid_url(self):
        """get_google_auth_url should generate valid OAuth URL."""
        from app.services.oauth import get_google_auth_url
        
        url = get_google_auth_url(state="test_state")
        
        assert "accounts.google.com" in url
        assert "client_id=" in url
        assert "state=test_state" in url
        assert "response_type=code" in url
    
    def test_get_google_auth_url_generates_state_if_not_provided(self):
        """get_google_auth_url should generate state if not provided."""
        from app.services.oauth import get_google_auth_url
        
        url = get_google_auth_url()
        
        assert "state=" in url
    
    @pytest.mark.asyncio
    async def test_exchange_google_code_success(self):
        """exchange_google_code should return tokens on success."""
        from app.services.oauth import exchange_google_code
        
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "access_token": "google_access_token",
            "refresh_token": "google_refresh_token",
            "expires_in": 3600,
        }
        
        with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = mock_response
            
            result = await exchange_google_code("auth_code_123")
        
        assert result["access_token"] == "google_access_token"
    
    @pytest.mark.asyncio
    async def test_exchange_google_code_failure(self):
        """exchange_google_code should raise AuthenticationError on failure."""
        from app.services.oauth import exchange_google_code
        from app.core.exceptions import AuthenticationError
        
        mock_response = MagicMock()
        mock_response.status_code = 400
        
        with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = mock_response
            
            with pytest.raises(AuthenticationError):
                await exchange_google_code("invalid_code")
    
    @pytest.mark.asyncio
    async def test_get_google_user_info_success(self):
        """get_google_user_info should return user info on success."""
        from app.services.oauth import get_google_user_info
        
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "id": "google_user_123",
            "email": "user@gmail.com",
            "name": "Test User",
        }
        
        with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = mock_response
            
            result = await get_google_user_info("access_token")
        
        assert result["id"] == "google_user_123"
        assert result["email"] == "user@gmail.com"
    
    @pytest.mark.asyncio
    async def test_get_google_user_info_failure(self):
        """get_google_user_info should raise AuthenticationError on failure."""
        from app.services.oauth import get_google_user_info
        from app.core.exceptions import AuthenticationError
        
        mock_response = MagicMock()
        mock_response.status_code = 401
        
        with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = mock_response
            
            with pytest.raises(AuthenticationError):
                await get_google_user_info("invalid_token")


class TestOAuthLoginOrCreate:
    """Tests for OAuth login/create functionality (Requirement 1.3)."""
    
    @pytest.mark.asyncio
    async def test_oauth_login_existing_oauth_user(self):
        """oauth_login_or_create should return existing OAuth user."""
        from app.services.oauth import oauth_login_or_create
        
        mock_user = MagicMock()
        mock_user.id = uuid4()
        mock_user.email = "existing@gmail.com"
        mock_user.created_at = datetime.now(timezone.utc)
        
        mock_db = AsyncMock()
        mock_repo = MagicMock()
        mock_repo.get_user_by_oauth = AsyncMock(return_value=mock_user)
        
        with patch("app.services.oauth.UserRepository", return_value=mock_repo):
            result = await oauth_login_or_create(
                db=mock_db,
                provider="google",
                oauth_id="google_123",
                email="existing@gmail.com",
            )
        
        assert result.user.email == "existing@gmail.com"
        assert result.tokens.token_type == "bearer"
        mock_repo.get_user_by_oauth.assert_called_once_with("google", "google_123")
    
    @pytest.mark.asyncio
    async def test_oauth_login_link_existing_email_user(self):
        """oauth_login_or_create should link OAuth to existing email user."""
        from app.services.oauth import oauth_login_or_create
        
        mock_user = MagicMock()
        mock_user.id = uuid4()
        mock_user.email = "existing@gmail.com"
        mock_user.created_at = datetime.now(timezone.utc)
        
        mock_db = AsyncMock()
        mock_repo = MagicMock()
        mock_repo.get_user_by_oauth = AsyncMock(return_value=None)
        mock_repo.get_user_by_email = AsyncMock(return_value=mock_user)
        mock_repo.link_oauth = AsyncMock(return_value=mock_user)
        
        with patch("app.services.oauth.UserRepository", return_value=mock_repo):
            result = await oauth_login_or_create(
                db=mock_db,
                provider="google",
                oauth_id="google_123",
                email="existing@gmail.com",
            )
        
        assert result.user.email == "existing@gmail.com"
        mock_repo.link_oauth.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_oauth_login_create_new_user(self):
        """oauth_login_or_create should create new user if not exists."""
        from app.services.oauth import oauth_login_or_create
        
        mock_user = MagicMock()
        mock_user.id = uuid4()
        mock_user.email = "newuser@gmail.com"
        mock_user.created_at = datetime.now(timezone.utc)
        
        mock_db = AsyncMock()
        mock_repo = MagicMock()
        mock_repo.get_user_by_oauth = AsyncMock(return_value=None)
        mock_repo.get_user_by_email = AsyncMock(return_value=None)
        mock_repo.create_oauth_user = AsyncMock(return_value=mock_user)
        
        with patch("app.services.oauth.UserRepository", return_value=mock_repo):
            result = await oauth_login_or_create(
                db=mock_db,
                provider="google",
                oauth_id="google_123",
                email="newuser@gmail.com",
            )
        
        assert result.user.email == "newuser@gmail.com"
        mock_repo.create_oauth_user.assert_called_once_with(
            email="newuser@gmail.com",
            oauth_provider="google",
            oauth_id="google_123",
        )
