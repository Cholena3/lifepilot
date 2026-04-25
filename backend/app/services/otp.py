"""OTP service for phone verification.

Validates: Requirements 1.4, 1.5, 1.6
"""

import logging
import secrets
from typing import Optional

import httpx

from app.core.config import get_settings
from app.core.exceptions import ValidationError
from app.core.redis import get_redis

logger = logging.getLogger(__name__)

settings = get_settings()

# Redis key prefix for OTP storage
OTP_KEY_PREFIX = "otp:phone:"
OTP_TTL_SECONDS = settings.otp_validity_seconds  # 5 minutes (300 seconds)


def generate_otp() -> str:
    """Generate a cryptographically secure 6-digit OTP.
    
    Validates: Requirements 1.4
    
    Returns:
        A 6-digit OTP string.
    """
    # Generate a random 6-digit number (100000-999999)
    otp = secrets.randbelow(900000) + 100000
    return str(otp)


async def store_otp(phone: str, otp: str) -> None:
    """Store OTP in Redis with 5-minute TTL.
    
    Validates: Requirements 1.4
    
    Args:
        phone: Phone number to associate with OTP.
        otp: The 6-digit OTP to store.
    """
    redis = get_redis()
    key = f"{OTP_KEY_PREFIX}{phone}"
    
    # Store OTP with TTL
    await redis.setex(key, OTP_TTL_SECONDS, otp)
    logger.info(f"OTP stored for phone {phone[:4]}***")


async def verify_otp(phone: str, otp: str) -> bool:
    """Verify OTP against stored value.
    
    Validates: Requirements 1.5, 1.6
    
    Args:
        phone: Phone number to verify.
        otp: The OTP submitted by user.
        
    Returns:
        True if OTP is valid and not expired.
        
    Raises:
        ValidationError: If OTP is expired or invalid.
    """
    redis = get_redis()
    key = f"{OTP_KEY_PREFIX}{phone}"
    
    # Get stored OTP
    stored_otp = await redis.get(key)
    
    if stored_otp is None:
        # OTP expired or never existed (Requirement 1.6)
        raise ValidationError(
            message="OTP has expired or is invalid",
            field_errors={"otp": "OTP has expired. Please request a new one."},
        )
    
    if stored_otp != otp:
        raise ValidationError(
            message="Invalid OTP",
            field_errors={"otp": "The OTP you entered is incorrect."},
        )
    
    # Delete OTP after successful verification (one-time use)
    await redis.delete(key)
    logger.info(f"OTP verified successfully for phone {phone[:4]}***")
    
    return True


async def send_otp_sms(phone: str, otp: str) -> bool:
    """Send OTP via SMS gateway.
    
    Validates: Requirements 1.4
    
    Args:
        phone: Phone number to send OTP to.
        otp: The 6-digit OTP to send.
        
    Returns:
        True if SMS was sent successfully.
        
    Raises:
        ValidationError: If SMS sending fails.
    """
    if not settings.sms_gateway_url or not settings.sms_api_key:
        # In development/testing, log the OTP instead of sending
        logger.warning(
            f"SMS gateway not configured. OTP for {phone[:4]}***: {otp}"
        )
        return True
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                settings.sms_gateway_url,
                headers={
                    "Authorization": f"Bearer {settings.sms_api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "to": phone,
                    "message": f"Your LifePilot verification code is: {otp}. Valid for 5 minutes.",
                },
                timeout=10.0,
            )
            
            if response.status_code >= 400:
                logger.error(
                    f"SMS gateway error: {response.status_code} - {response.text}"
                )
                raise ValidationError(
                    message="Failed to send OTP",
                    field_errors={"phone": "Unable to send SMS. Please try again."},
                )
            
            logger.info(f"OTP SMS sent successfully to {phone[:4]}***")
            return True
            
    except httpx.RequestError as e:
        logger.error(f"SMS gateway request failed: {e}")
        raise ValidationError(
            message="Failed to send OTP",
            field_errors={"phone": "Unable to send SMS. Please try again."},
        )


async def send_otp(phone: str) -> tuple[int, str | None]:
    """Generate, store, and send OTP to phone number.
    
    Validates: Requirements 1.4
    
    Args:
        phone: Phone number to send OTP to.
        
    Returns:
        Tuple of (TTL in seconds, OTP string if in dev mode else None).
    """
    otp = generate_otp()
    await store_otp(phone, otp)
    await send_otp_sms(phone, otp)
    
    # In dev mode (no SMS gateway), return the OTP so the frontend can show it
    if not settings.sms_gateway_url or not settings.sms_api_key:
        return OTP_TTL_SECONDS, otp
    
    return OTP_TTL_SECONDS, None
