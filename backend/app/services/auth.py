"""Authentication service for user registration, login, and JWT management.

Validates: Requirements 1.1, 1.7, 1.8, 1.9
"""

import bcrypt
from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import UUID

from jose import jwt
from sqlalchemy.ext.asyncio import AsyncSession

from jose import JWTError

from app.core.config import get_settings
from app.core.exceptions import AuthenticationError, ConflictError, ValidationError
from app.repositories.user import UserRepository
from app.schemas.auth import AuthResponse, TokenResponse, UserResponse

settings = get_settings()


def hash_password(password: str) -> str:
    """Hash a password using bcrypt.
    
    Validates: Requirements 1.8
    
    Args:
        password: Plain text password to hash
        
    Returns:
        Bcrypt hashed password string
    """
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plain password against a bcrypt hash.
    
    Validates: Requirements 1.8
    
    Args:
        plain_password: Plain text password to verify
        hashed_password: Bcrypt hashed password to check against
        
    Returns:
        True if password matches, False otherwise
    """
    return bcrypt.checkpw(plain_password.encode('utf-8'), hashed_password.encode('utf-8'))


def create_access_token(
    data: dict[str, Any],
    expires_delta: timedelta | None = None,
) -> str:
    """Create a JWT access token.
    
    Validates: Requirements 1.7, 1.9
    
    Args:
        data: Payload data to encode in the token
        expires_delta: Optional custom expiration time
        
    Returns:
        Encoded JWT token string
    """
    to_encode = data.copy()
    
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(
            minutes=settings.access_token_expire_minutes
        )
    
    to_encode.update({
        "exp": expire,
        "iat": datetime.now(timezone.utc),
        "type": "access",
    })
    
    return jwt.encode(
        to_encode,
        settings.secret_key,
        algorithm=settings.algorithm,
    )


def create_refresh_token(data: dict[str, Any]) -> str:
    """Create a JWT refresh token with longer expiration.
    
    Validates: Requirements 1.7
    
    Args:
        data: Payload data to encode in the token
        
    Returns:
        Encoded JWT refresh token string
    """
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(
        days=settings.refresh_token_expire_days
    )
    
    to_encode.update({
        "exp": expire,
        "iat": datetime.now(timezone.utc),
        "type": "refresh",
    })
    
    return jwt.encode(
        to_encode,
        settings.secret_key,
        algorithm=settings.algorithm,
    )


def create_tokens(user_id: UUID, email: str) -> TokenResponse:
    """Create both access and refresh tokens for a user.
    
    Args:
        user_id: User's unique identifier
        email: User's email address
        
    Returns:
        TokenResponse with access and refresh tokens
    """
    token_data = {"sub": str(user_id), "email": email}
    
    access_token = create_access_token(token_data)
    refresh_token = create_refresh_token(token_data)
    
    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
    )


async def register_user(
    db: AsyncSession,
    email: str,
    password: str,
) -> AuthResponse:
    """Register a new user and return JWT tokens.
    
    Validates: Requirements 1.1, 1.2, 1.8
    
    Args:
        db: Database session
        email: User's email address
        password: User's plain text password
        
    Returns:
        AuthResponse with user data and JWT tokens
        
    Raises:
        ConflictError: If email is already registered
    """
    user_repo = UserRepository(db)
    
    # Check if email already exists
    existing_user = await user_repo.get_user_by_email(email)
    if existing_user:
        raise ConflictError(
            detail="Email already registered",
            field_errors={"email": "This email is already in use"},
        )
    
    # Hash password using bcrypt (Requirement 1.8)
    password_hash = hash_password(password)
    
    # Create user in database
    user = await user_repo.create_user(email=email, password_hash=password_hash)
    
    # Generate JWT tokens (Requirement 1.1)
    tokens = create_tokens(user.id, user.email)
    
    # Build response
    user_response = UserResponse(
        id=user.id,
        email=user.email,
        created_at=user.created_at,
    )
    
    return AuthResponse(user=user_response, tokens=tokens)


async def login_user(
    db: AsyncSession,
    email: str,
    password: str,
) -> AuthResponse:
    """Authenticate a user and return JWT tokens.
    
    Validates: Requirements 1.1, 1.7, 1.9
    
    Args:
        db: Database session
        email: User's email address
        password: User's plain text password
        
    Returns:
        AuthResponse with user data and JWT tokens
        
    Raises:
        AuthenticationError: If credentials are invalid
    """
    user_repo = UserRepository(db)
    
    # Find user by email
    user = await user_repo.get_user_by_email(email)
    if not user:
        raise AuthenticationError(message="Invalid email or password")
    
    # Verify password against stored hash
    if not user.password_hash or not verify_password(password, user.password_hash):
        raise AuthenticationError(message="Invalid email or password")
    
    # Generate JWT tokens (Requirement 1.1, 1.9)
    tokens = create_tokens(user.id, user.email)
    
    # Build response
    user_response = UserResponse(
        id=user.id,
        email=user.email,
        created_at=user.created_at,
    )
    
    return AuthResponse(user=user_response, tokens=tokens)


def decode_token(token: str) -> dict[str, Any]:
    """Decode and validate a JWT token.
    
    Validates: Requirements 1.7
    
    Args:
        token: JWT token string
        
    Returns:
        Decoded token payload
        
    Raises:
        AuthenticationError: If token is invalid or expired
    """
    try:
        payload = jwt.decode(
            token,
            settings.secret_key,
            algorithms=[settings.algorithm],
        )
        return payload
    except JWTError as e:
        raise AuthenticationError(message="Invalid or expired token")


async def refresh_access_token(
    db: AsyncSession,
    refresh_token: str,
) -> TokenResponse:
    """Generate a new access token using a refresh token.
    
    Validates: Requirements 1.7
    
    Args:
        db: Database session
        refresh_token: JWT refresh token
        
    Returns:
        TokenResponse with new access and refresh tokens
        
    Raises:
        AuthenticationError: If refresh token is invalid or expired
    """
    # Decode and validate refresh token
    payload = decode_token(refresh_token)
    
    # Verify it's a refresh token
    if payload.get("type") != "refresh":
        raise AuthenticationError(message="Invalid token type")
    
    # Extract user info from token
    user_id = payload.get("sub")
    email = payload.get("email")
    
    if not user_id or not email:
        raise AuthenticationError(message="Invalid token payload")
    
    # Verify user still exists
    user_repo = UserRepository(db)
    user = await user_repo.get_user_by_id(user_id)
    if not user:
        raise AuthenticationError(message="User not found")
    
    # Generate new tokens
    return create_tokens(user.id, user.email)
