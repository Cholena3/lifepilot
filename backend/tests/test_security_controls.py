"""Tests for security controls implementation.

Validates: Requirements 36.3, 36.4, 36.7
"""

import pytest
from pydantic import ValidationError

from app.schemas.auth import UserRegister
from app.services.password_validator import (
    PasswordValidator,
    PasswordValidationResult,
    validate_password,
    is_password_valid,
)


class TestPasswordComplexityRequirements:
    """Test password complexity validation per Requirement 36.3."""

    def test_valid_password_with_all_requirements(self):
        """Password with all requirements should be accepted."""
        result = validate_password("SecureP@ss123")
        assert result.is_valid is True
        assert result.errors == []

    def test_password_too_short(self):
        """Password shorter than 8 characters should be rejected."""
        result = validate_password("Sh@rt1")
        assert result.is_valid is False
        assert any("8 characters" in error for error in result.errors)

    def test_password_without_uppercase(self):
        """Password without uppercase letter should be rejected."""
        result = validate_password("securepass@123")
        assert result.is_valid is False
        assert any("uppercase" in error for error in result.errors)

    def test_password_without_lowercase(self):
        """Password without lowercase letter should be rejected."""
        result = validate_password("SECUREPASS@123")
        assert result.is_valid is False
        assert any("lowercase" in error for error in result.errors)

    def test_password_without_digit(self):
        """Password without digit should be rejected."""
        result = validate_password("SecurePass@abc")
        assert result.is_valid is False
        assert any("digit" in error for error in result.errors)

    def test_password_without_special_char(self):
        """Password without special character should be rejected."""
        result = validate_password("SecurePass123")
        assert result.is_valid is False
        assert any("special character" in error for error in result.errors)

    def test_password_with_various_special_chars(self):
        """Password with various special characters should be accepted."""
        special_chars = ["!", "@", "#", "$", "%", "^", "&", "*", "(", ")", "_", "+", "-", "=", "[", "]", "{", "}", "|", ";", ":", ",", ".", "<", ">", "?"]
        for char in special_chars:
            password = f"SecurePass123{char}"
            result = validate_password(password)
            assert result.is_valid is True, f"Password with '{char}' should be valid"

    def test_is_password_valid_helper(self):
        """Test the is_password_valid helper function."""
        assert is_password_valid("SecureP@ss123") is True
        assert is_password_valid("weak") is False


class TestPasswordValidatorConfiguration:
    """Test configurable password validator."""

    def test_custom_min_length(self):
        """Validator with custom min length should enforce it."""
        validator = PasswordValidator(min_length=12)
        result = validator.validate("SecureP@ss1")  # 11 chars
        assert result.is_valid is False
        assert any("12 characters" in error for error in result.errors)

    def test_disable_special_char_requirement(self):
        """Validator without special char requirement should accept passwords without them."""
        validator = PasswordValidator(require_special=False)
        result = validator.validate("SecurePass123")
        assert result.is_valid is True

    def test_requirements_description(self):
        """Validator should provide human-readable requirements description."""
        validator = PasswordValidator()
        description = validator.get_requirements_description()
        assert "8 characters" in description
        assert "uppercase" in description
        assert "lowercase" in description
        assert "digit" in description
        assert "special character" in description


class TestUserRegisterSchemaPasswordValidation:
    """Test password validation in UserRegister schema."""

    def test_valid_registration_password(self):
        """Valid password should be accepted in registration."""
        user = UserRegister(email="test@example.com", password="SecureP@ss123")
        assert user.password == "SecureP@ss123"

    def test_registration_password_without_special_char(self):
        """Registration should fail without special character."""
        with pytest.raises(ValidationError) as exc_info:
            UserRegister(email="test@example.com", password="SecurePass123")
        
        errors = exc_info.value.errors()
        assert any("special character" in str(e) for e in errors)

    def test_registration_password_too_short(self):
        """Registration should fail with short password."""
        with pytest.raises(ValidationError) as exc_info:
            UserRegister(email="test@example.com", password="Sh@rt1")
        
        errors = exc_info.value.errors()
        assert any("8 characters" in str(e) for e in errors)

    def test_registration_password_without_uppercase(self):
        """Registration should fail without uppercase letter."""
        with pytest.raises(ValidationError) as exc_info:
            UserRegister(email="test@example.com", password="securepass@123")
        
        errors = exc_info.value.errors()
        assert any("uppercase" in str(e) for e in errors)

    def test_registration_password_without_lowercase(self):
        """Registration should fail without lowercase letter."""
        with pytest.raises(ValidationError) as exc_info:
            UserRegister(email="test@example.com", password="SECUREPASS@123")
        
        errors = exc_info.value.errors()
        assert any("lowercase" in str(e) for e in errors)

    def test_registration_password_without_digit(self):
        """Registration should fail without digit."""
        with pytest.raises(ValidationError) as exc_info:
            UserRegister(email="test@example.com", password="SecurePass@abc")
        
        errors = exc_info.value.errors()
        assert any("digit" in str(e) for e in errors)


class TestRateLimitMiddleware:
    """Test rate limiting middleware configuration."""

    def test_rate_limit_middleware_import(self):
        """Rate limit middleware should be importable."""
        from app.middleware import RateLimitMiddleware
        assert RateLimitMiddleware is not None

    def test_rate_limit_middleware_initialization(self):
        """Rate limit middleware should initialize with default settings."""
        from app.middleware import RateLimitMiddleware
        from app.core.config import get_settings
        
        settings = get_settings()
        
        # Create a mock app
        class MockApp:
            pass
        
        middleware = RateLimitMiddleware(MockApp())
        assert middleware.requests_limit == settings.rate_limit_requests
        assert middleware.window_seconds == settings.rate_limit_window_seconds

    def test_rate_limit_middleware_custom_limits(self):
        """Rate limit middleware should accept custom limits."""
        from app.middleware import RateLimitMiddleware
        
        class MockApp:
            pass
        
        middleware = RateLimitMiddleware(MockApp(), requests_limit=50, window_seconds=30)
        assert middleware.requests_limit == 50
        assert middleware.window_seconds == 30


class TestAuditLogMiddleware:
    """Test audit logging middleware configuration."""

    def test_audit_log_middleware_import(self):
        """Audit log middleware should be importable."""
        from app.middleware import AuditLogMiddleware
        assert AuditLogMiddleware is not None

    def test_audit_log_model_import(self):
        """Audit log model should be importable."""
        from app.models.audit_log import AuditLog
        assert AuditLog is not None

    def test_audit_log_model_fields(self):
        """Audit log model should have required fields."""
        from app.models.audit_log import AuditLog
        
        # Check that the model has the expected columns
        columns = AuditLog.__table__.columns.keys()
        expected_columns = [
            "id", "user_id", "action", "entity_type", "entity_id",
            "http_method", "request_path", "ip_address", "user_agent",
            "status_code", "old_data", "new_data", "extra_data", "created_at"
        ]
        for col in expected_columns:
            assert col in columns, f"Missing column: {col}"
