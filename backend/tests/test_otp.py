"""Tests for OTP service and endpoints.

Validates: Requirements 1.4, 1.5, 1.6
"""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock

from app.services.otp import (
    generate_otp,
    store_otp,
    verify_otp,
    send_otp_sms,
    send_otp,
    OTP_TTL_SECONDS,
)
from app.core.exceptions import ValidationError


class TestGenerateOTP:
    """Tests for OTP generation."""
    
    def test_generate_otp_returns_6_digits(self):
        """OTP should be exactly 6 digits."""
        otp = generate_otp()
        assert len(otp) == 6
        assert otp.isdigit()
    
    def test_generate_otp_is_in_valid_range(self):
        """OTP should be between 100000 and 999999."""
        for _ in range(100):
            otp = generate_otp()
            otp_int = int(otp)
            assert 100000 <= otp_int <= 999999
    
    def test_generate_otp_is_random(self):
        """Multiple OTPs should be different (with high probability)."""
        otps = [generate_otp() for _ in range(10)]
        # At least some should be different
        assert len(set(otps)) > 1


class TestStoreOTP:
    """Tests for OTP storage in Redis."""
    
    @pytest.mark.asyncio
    async def test_store_otp_calls_redis_setex(self):
        """store_otp should store OTP in Redis with TTL."""
        mock_redis = AsyncMock()
        
        with patch("app.services.otp.get_redis", return_value=mock_redis):
            await store_otp("+1234567890", "123456")
            
            mock_redis.setex.assert_called_once_with(
                "otp:phone:+1234567890",
                OTP_TTL_SECONDS,
                "123456",
            )


class TestVerifyOTP:
    """Tests for OTP verification."""
    
    @pytest.mark.asyncio
    async def test_verify_otp_success(self):
        """Correct OTP should verify successfully."""
        mock_redis = AsyncMock()
        mock_redis.get.return_value = "123456"
        
        with patch("app.services.otp.get_redis", return_value=mock_redis):
            result = await verify_otp("+1234567890", "123456")
            
            assert result is True
            mock_redis.delete.assert_called_once_with("otp:phone:+1234567890")
    
    @pytest.mark.asyncio
    async def test_verify_otp_expired(self):
        """Expired OTP should raise ValidationError (Requirement 1.6)."""
        mock_redis = AsyncMock()
        mock_redis.get.return_value = None  # OTP expired/not found
        
        with patch("app.services.otp.get_redis", return_value=mock_redis):
            with pytest.raises(ValidationError) as exc_info:
                await verify_otp("+1234567890", "123456")
            
            assert "expired" in exc_info.value.message.lower()
    
    @pytest.mark.asyncio
    async def test_verify_otp_incorrect(self):
        """Incorrect OTP should raise ValidationError."""
        mock_redis = AsyncMock()
        mock_redis.get.return_value = "654321"  # Different OTP stored
        
        with patch("app.services.otp.get_redis", return_value=mock_redis):
            with pytest.raises(ValidationError) as exc_info:
                await verify_otp("+1234567890", "123456")
            
            assert "invalid" in exc_info.value.message.lower()


class TestSendOTPSMS:
    """Tests for SMS sending."""
    
    @pytest.mark.asyncio
    async def test_send_otp_sms_no_gateway_configured(self):
        """When SMS gateway not configured, should log and return True."""
        with patch("app.services.otp.settings") as mock_settings:
            mock_settings.sms_gateway_url = ""
            mock_settings.sms_api_key = ""
            
            result = await send_otp_sms("+1234567890", "123456")
            assert result is True


class TestSendOTP:
    """Tests for the complete OTP send flow."""
    
    @pytest.mark.asyncio
    async def test_send_otp_returns_ttl(self):
        """send_otp should return the TTL in seconds."""
        with patch("app.services.otp.generate_otp", return_value="123456"):
            with patch("app.services.otp.store_otp", new_callable=AsyncMock):
                with patch("app.services.otp.send_otp_sms", new_callable=AsyncMock, return_value=True):
                    result = await send_otp("+1234567890")
                    
                    assert result == OTP_TTL_SECONDS


class TestOTPSchemas:
    """Tests for OTP request/response schemas."""
    
    def test_otp_send_request_valid_phone(self):
        """Valid phone numbers should be accepted."""
        from app.schemas.auth import OTPSendRequest
        
        # Various valid formats
        valid_phones = [
            "+1234567890",
            "1234567890",
            "+12345678901234",
        ]
        
        for phone in valid_phones:
            request = OTPSendRequest(phone=phone)
            assert request.phone is not None
    
    def test_otp_send_request_invalid_phone(self):
        """Invalid phone numbers should be rejected."""
        from app.schemas.auth import OTPSendRequest
        from pydantic import ValidationError as PydanticValidationError
        
        invalid_phones = [
            "123",  # Too short
            "abcdefghij",  # Not digits
            "++1234567890",  # Double plus
        ]
        
        for phone in invalid_phones:
            with pytest.raises(PydanticValidationError):
                OTPSendRequest(phone=phone)
    
    def test_otp_verify_request_valid(self):
        """Valid OTP verify request should be accepted."""
        from app.schemas.auth import OTPVerifyRequest
        
        request = OTPVerifyRequest(phone="+1234567890", otp="123456")
        assert request.phone == "+1234567890"
        assert request.otp == "123456"
    
    def test_otp_verify_request_invalid_otp_format(self):
        """Invalid OTP format should be rejected."""
        from app.schemas.auth import OTPVerifyRequest
        from pydantic import ValidationError as PydanticValidationError
        
        invalid_otps = [
            "12345",  # Too short
            "1234567",  # Too long
            "abcdef",  # Not digits
        ]
        
        for otp in invalid_otps:
            with pytest.raises(PydanticValidationError):
                OTPVerifyRequest(phone="+1234567890", otp=otp)
