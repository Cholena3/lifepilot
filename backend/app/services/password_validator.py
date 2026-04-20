"""Password validation service for enforcing complexity requirements.

Validates: Requirements 36.3

Provides centralized password validation with configurable complexity rules.
"""

import re
from dataclasses import dataclass
from typing import List, Optional


@dataclass
class PasswordValidationResult:
    """Result of password validation."""
    
    is_valid: bool
    errors: List[str]
    
    @property
    def error_message(self) -> Optional[str]:
        """Get combined error message."""
        if self.errors:
            return "; ".join(self.errors)
        return None


class PasswordValidator:
    """Password validator with configurable complexity requirements.
    
    Validates: Requirements 36.3
    
    Default requirements:
    - Minimum 8 characters
    - At least one uppercase letter
    - At least one lowercase letter
    - At least one digit
    - At least one special character
    """
    
    DEFAULT_MIN_LENGTH = 8
    DEFAULT_MAX_LENGTH = 128
    DEFAULT_SPECIAL_CHARS = r"!@#$%^&*()_+\-=\[\]{}|;:,.<>?"
    
    def __init__(
        self,
        min_length: int = DEFAULT_MIN_LENGTH,
        max_length: int = DEFAULT_MAX_LENGTH,
        require_uppercase: bool = True,
        require_lowercase: bool = True,
        require_digit: bool = True,
        require_special: bool = True,
        special_chars: str = DEFAULT_SPECIAL_CHARS,
    ):
        """Initialize password validator with requirements.
        
        Args:
            min_length: Minimum password length
            max_length: Maximum password length
            require_uppercase: Require at least one uppercase letter
            require_lowercase: Require at least one lowercase letter
            require_digit: Require at least one digit
            require_special: Require at least one special character
            special_chars: Regex pattern for special characters
        """
        self.min_length = min_length
        self.max_length = max_length
        self.require_uppercase = require_uppercase
        self.require_lowercase = require_lowercase
        self.require_digit = require_digit
        self.require_special = require_special
        self.special_chars = special_chars
    
    def validate(self, password: str) -> PasswordValidationResult:
        """Validate password against complexity requirements.
        
        Validates: Requirements 36.3
        
        Args:
            password: Password to validate
            
        Returns:
            PasswordValidationResult with validation status and errors
        """
        errors: List[str] = []
        
        # Check length
        if len(password) < self.min_length:
            errors.append(
                f"Password must be at least {self.min_length} characters long"
            )
        
        if len(password) > self.max_length:
            errors.append(
                f"Password must be at most {self.max_length} characters long"
            )
        
        # Check uppercase
        if self.require_uppercase and not re.search(r"[A-Z]", password):
            errors.append("Password must contain at least one uppercase letter")
        
        # Check lowercase
        if self.require_lowercase and not re.search(r"[a-z]", password):
            errors.append("Password must contain at least one lowercase letter")
        
        # Check digit
        if self.require_digit and not re.search(r"\d", password):
            errors.append("Password must contain at least one digit")
        
        # Check special character
        if self.require_special and not re.search(
            f"[{re.escape(self.special_chars)}]", password
        ):
            errors.append(
                f"Password must contain at least one special character "
                f"({self.special_chars})"
            )
        
        return PasswordValidationResult(
            is_valid=len(errors) == 0,
            errors=errors,
        )
    
    def get_requirements_description(self) -> str:
        """Get human-readable description of password requirements.
        
        Returns:
            Description string of all requirements
        """
        requirements = [f"At least {self.min_length} characters"]
        
        if self.require_uppercase:
            requirements.append("At least one uppercase letter")
        if self.require_lowercase:
            requirements.append("At least one lowercase letter")
        if self.require_digit:
            requirements.append("At least one digit")
        if self.require_special:
            requirements.append(f"At least one special character ({self.special_chars})")
        
        return "; ".join(requirements)


# Default validator instance
default_validator = PasswordValidator()


def validate_password(password: str) -> PasswordValidationResult:
    """Validate password using default validator.
    
    Validates: Requirements 36.3
    
    Args:
        password: Password to validate
        
    Returns:
        PasswordValidationResult with validation status and errors
    """
    return default_validator.validate(password)


def is_password_valid(password: str) -> bool:
    """Check if password meets complexity requirements.
    
    Validates: Requirements 36.3
    
    Args:
        password: Password to check
        
    Returns:
        True if password is valid, False otherwise
    """
    return default_validator.validate(password).is_valid
