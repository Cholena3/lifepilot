"""Application dependencies for dependency injection.

Validates: Requirements 1.7, 1.9, 38.1, 38.2, 38.3, 38.4
"""

from typing import Annotated
from uuid import UUID

from fastapi import Depends, Header
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.exceptions import AuthenticationError, AuthorizationError
from app.models.user import User
from app.repositories.user import UserRepository
from app.services.auth import decode_token

# HTTP Bearer security scheme
security = HTTPBearer()


async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(security)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> User:
    """Get the current authenticated user from JWT token.
    
    Validates: Requirements 1.7, 1.9
    
    Args:
        credentials: HTTP Bearer credentials with JWT token
        db: Database session
        
    Returns:
        Authenticated User model instance
        
    Raises:
        AuthenticationError: If token is invalid or user not found
    """
    token = credentials.credentials
    
    # Decode and validate token
    payload = decode_token(token)
    
    # Verify it's an access token
    if payload.get("type") != "access":
        raise AuthenticationError(message="Invalid token type")
    
    # Extract user ID from token
    user_id = payload.get("sub")
    if not user_id:
        raise AuthenticationError(message="Invalid token payload")
    
    # Get user from database
    user_repo = UserRepository(db)
    user = await user_repo.get_user_by_id(user_id)
    
    if not user:
        raise AuthenticationError(message="User not found")
    
    return user


async def get_admin_user(
    current_user: Annotated[User, Depends(get_current_user)],
) -> User:
    """Get the current authenticated admin user.
    
    Validates: Requirements 38.1, 38.2, 38.3, 38.4
    
    Args:
        current_user: Authenticated user from get_current_user
        
    Returns:
        Authenticated admin User model instance
        
    Raises:
        AuthorizationError: If user is not an admin
    """
    if not current_user.is_admin:
        raise AuthorizationError(message="Admin access required")
    
    return current_user


# Type alias for dependency injection
CurrentUser = Annotated[User, Depends(get_current_user)]
AdminUser = Annotated[User, Depends(get_admin_user)]
