"""Authentication schemas for user registration and login.

Validates: Requirements 1.1, 1.2, 1.8
"""

import re
from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field, field_validator


class UserRegister(BaseModel):
    """Schema for user registration request.
    
    Validates: Requirements 1.1, 1.2
    """
    
    email: EmailStr = Field(
        ...,
        description="User's email address",
        examples=["user@example.com"],
    )
    password: str = Field(
        ...,
        min_length=8,
        max_length=128,
        description="User's password (min 8 characters)",
        examples=["SecureP@ss123"],
    )
    
    @field_validator("email")
    @classmethod
    def validate_email_format(cls, v: str) -> str:
        """Additional email validation per Requirement 1.2.
        
        Rejects invalid email formats with specific field details.
        """
        # EmailStr already validates basic format, but we add extra checks
        email_pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
        if not re.match(email_pattern, v):
            raise ValueError("Invalid email format")
        
        # Check for common invalid patterns
        if ".." in v:
            raise ValueError("Email cannot contain consecutive dots")
        if v.startswith(".") or v.startswith("-"):
            raise ValueError("Email cannot start with a dot or hyphen")
        
        return v.lower()
    
    @field_validator("password")
    @classmethod
    def validate_password_strength(cls, v: str) -> str:
        """Validate password meets complexity requirements per Requirement 36.3.
        
        Password must contain:
        - At least 8 characters
        - At least one uppercase letter
        - At least one lowercase letter
        - At least one digit
        - At least one special character (!@#$%^&*()_+-=[]{}|;:,.<>?)
        """
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters long")
        if not re.search(r"[A-Z]", v):
            raise ValueError("Password must contain at least one uppercase letter")
        if not re.search(r"[a-z]", v):
            raise ValueError("Password must contain at least one lowercase letter")
        if not re.search(r"\d", v):
            raise ValueError("Password must contain at least one digit")
        if not re.search(r"[!@#$%^&*()_+\-=\[\]{}|;:,.<>?]", v):
            raise ValueError("Password must contain at least one special character (!@#$%^&*()_+-=[]{}|;:,.<>?)")
        return v


class TokenResponse(BaseModel):
    """Schema for JWT token response.
    
    Validates: Requirements 1.1, 1.7
    """
    
    access_token: str = Field(
        ...,
        description="JWT access token for API authentication",
    )
    refresh_token: str = Field(
        ...,
        description="JWT refresh token for obtaining new access tokens",
    )
    token_type: str = Field(
        default="bearer",
        description="Token type (always 'bearer')",
    )


class UserResponse(BaseModel):
    """Schema for user data in responses.
    
    Validates: Requirements 1.1
    """
    
    id: UUID = Field(..., description="User's unique identifier")
    email: str = Field(..., description="User's email address")
    created_at: datetime = Field(..., description="Account creation timestamp")
    
    model_config = {"from_attributes": True}


class AuthResponse(BaseModel):
    """Combined response for registration/login with user data and tokens."""
    
    user: UserResponse
    tokens: TokenResponse


class UserLogin(BaseModel):
    """Schema for user login request.
    
    Validates: Requirements 1.1, 1.9
    """
    
    email: EmailStr = Field(
        ...,
        description="User's email address",
        examples=["user@example.com"],
    )
    password: str = Field(
        ...,
        min_length=1,
        max_length=128,
        description="User's password",
        examples=["SecureP@ss123"],
    )


class TokenRefresh(BaseModel):
    """Schema for token refresh request.
    
    Validates: Requirements 1.7
    """
    
    refresh_token: str = Field(
        ...,
        description="JWT refresh token",
    )


class OAuthCallback(BaseModel):
    """Schema for OAuth callback parameters.
    
    Validates: Requirements 1.3
    """
    
    code: str = Field(
        ...,
        description="Authorization code from OAuth provider",
    )
    state: str | None = Field(
        default=None,
        description="State parameter for CSRF protection",
    )


class GoogleAuthUrl(BaseModel):
    """Schema for Google OAuth authorization URL response.
    
    Validates: Requirements 1.3
    """
    
    auth_url: str = Field(
        ...,
        description="Google OAuth authorization URL",
    )
    state: str = Field(
        ...,
        description="State parameter for CSRF protection",
    )


class OTPSendRequest(BaseModel):
    """Schema for OTP send request.
    
    Validates: Requirements 1.4
    """
    
    phone: str = Field(
        ...,
        min_length=10,
        max_length=15,
        description="Phone number to send OTP to",
        examples=["+1234567890"],
    )
    
    @field_validator("phone")
    @classmethod
    def validate_phone_format(cls, v: str) -> str:
        """Validate phone number format."""
        # Remove any spaces or dashes
        cleaned = re.sub(r"[\s\-]", "", v)
        
        # Check for valid phone format (digits, optionally starting with +)
        if not re.match(r"^\+?\d{10,15}$", cleaned):
            raise ValueError(
                "Invalid phone number format. Use digits only, optionally starting with +"
            )
        
        return cleaned


class OTPVerifyRequest(BaseModel):
    """Schema for OTP verification request.
    
    Validates: Requirements 1.5, 1.6
    """
    
    phone: str = Field(
        ...,
        min_length=10,
        max_length=15,
        description="Phone number to verify",
        examples=["+1234567890"],
    )
    otp: str = Field(
        ...,
        min_length=6,
        max_length=6,
        description="6-digit OTP code",
        examples=["123456"],
    )
    
    @field_validator("phone")
    @classmethod
    def validate_phone_format(cls, v: str) -> str:
        """Validate phone number format."""
        cleaned = re.sub(r"[\s\-]", "", v)
        if not re.match(r"^\+?\d{10,15}$", cleaned):
            raise ValueError(
                "Invalid phone number format. Use digits only, optionally starting with +"
            )
        return cleaned
    
    @field_validator("otp")
    @classmethod
    def validate_otp_format(cls, v: str) -> str:
        """Validate OTP is 6 digits."""
        if not re.match(r"^\d{6}$", v):
            raise ValueError("OTP must be exactly 6 digits")
        return v


class OTPResponse(BaseModel):
    """Schema for OTP send response.
    
    Validates: Requirements 1.4
    """
    
    message: str = Field(
        ...,
        description="Success message",
        examples=["OTP sent successfully"],
    )
    expires_in: int = Field(
        ...,
        description="OTP validity in seconds",
        examples=[300],
    )
    dev_otp: str | None = Field(
        default=None,
        description="OTP code (only returned in dev mode when SMS gateway is not configured)",
    )


class OTPVerifyResponse(BaseModel):
    """Schema for OTP verification response.
    
    Validates: Requirements 1.5
    """
    
    message: str = Field(
        ...,
        description="Success message",
        examples=["Phone number verified successfully"],
    )
    phone_verified: bool = Field(
        ...,
        description="Whether phone is now verified",
        examples=[True],
    )
