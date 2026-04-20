"""OAuth service for Google authentication.

Validates: Requirements 1.3
"""

import secrets
from typing import Any
from urllib.parse import urlencode

import httpx
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.exceptions import AuthenticationError
from app.repositories.user import UserRepository
from app.schemas.auth import AuthResponse, TokenResponse, UserResponse
from app.services.auth import create_tokens

settings = get_settings()

# Google OAuth endpoints
GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_USERINFO_URL = "https://www.googleapis.com/oauth2/v2/userinfo"


def get_google_auth_url(state: str | None = None) -> str:
    """Generate Google OAuth authorization URL.
    
    Validates: Requirements 1.3
    
    Args:
        state: Optional state parameter for CSRF protection
        
    Returns:
        Google OAuth authorization URL
    """
    if state is None:
        state = secrets.token_urlsafe(32)
    
    params = {
        "client_id": settings.google_client_id,
        "redirect_uri": settings.google_redirect_uri,
        "response_type": "code",
        "scope": "openid email profile",
        "access_type": "offline",
        "state": state,
        "prompt": "consent",
    }
    
    return f"{GOOGLE_AUTH_URL}?{urlencode(params)}"


async def exchange_google_code(code: str) -> dict[str, Any]:
    """Exchange authorization code for tokens.
    
    Validates: Requirements 1.3
    
    Args:
        code: Authorization code from Google OAuth callback
        
    Returns:
        Token response containing access_token, refresh_token, etc.
        
    Raises:
        AuthenticationError: If token exchange fails
    """
    async with httpx.AsyncClient() as client:
        response = await client.post(
            GOOGLE_TOKEN_URL,
            data={
                "client_id": settings.google_client_id,
                "client_secret": settings.google_client_secret,
                "code": code,
                "grant_type": "authorization_code",
                "redirect_uri": settings.google_redirect_uri,
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        
        if response.status_code != 200:
            raise AuthenticationError(message="Failed to exchange authorization code")
        
        return response.json()


async def get_google_user_info(access_token: str) -> dict[str, Any]:
    """Get user info from Google using access token.
    
    Validates: Requirements 1.3
    
    Args:
        access_token: Google OAuth access token
        
    Returns:
        User info containing id, email, name, picture, etc.
        
    Raises:
        AuthenticationError: If fetching user info fails
    """
    async with httpx.AsyncClient() as client:
        response = await client.get(
            GOOGLE_USERINFO_URL,
            headers={"Authorization": f"Bearer {access_token}"},
        )
        
        if response.status_code != 200:
            raise AuthenticationError(message="Failed to fetch user info from Google")
        
        return response.json()


async def oauth_login_or_create(
    db: AsyncSession,
    provider: str,
    oauth_id: str,
    email: str,
) -> AuthResponse:
    """Create or link account for OAuth user.
    
    Validates: Requirements 1.3
    
    This function handles both new user creation and linking existing accounts:
    - If user exists with same email, link OAuth provider to existing account
    - If user exists with same OAuth ID, return existing user
    - Otherwise, create new user with OAuth credentials
    
    Args:
        db: Database session
        provider: OAuth provider name (e.g., 'google')
        oauth_id: OAuth provider user ID
        email: User's email from OAuth provider
        
    Returns:
        AuthResponse with user data and JWT tokens
    """
    user_repo = UserRepository(db)
    
    # Check if user exists with this OAuth ID
    user = await user_repo.get_user_by_oauth(provider, oauth_id)
    
    if user is None:
        # Check if user exists with this email
        user = await user_repo.get_user_by_email(email)
        
        if user is not None:
            # Link OAuth to existing account
            user = await user_repo.link_oauth(user.id, provider, oauth_id)
        else:
            # Create new OAuth user
            user = await user_repo.create_oauth_user(
                email=email,
                oauth_provider=provider,
                oauth_id=oauth_id,
            )
    
    # Generate JWT tokens
    tokens = create_tokens(user.id, user.email)
    
    # Build response
    user_response = UserResponse(
        id=user.id,
        email=user.email,
        created_at=user.created_at,
    )
    
    return AuthResponse(user=user_response, tokens=tokens)
