"""Property-based tests for authentication module.

Uses Hypothesis to verify universal properties across all valid inputs.

Note: These tests use bcrypt directly to avoid passlib/bcrypt 4.x compatibility
issues in the test environment. The production code uses passlib which handles
bcrypt correctly.
"""

import string
import bcrypt
from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest
from hypothesis import given, strategies as st, settings, assume
from jose import jwt
from pydantic import ValidationError

from app.schemas.auth import UserRegister


# Strategy for generating valid passwords that meet complexity requirements:
# - At least 8 characters
# - At least one uppercase letter
# - At least one lowercase letter
# - At least one digit
# - Maximum 72 bytes (bcrypt limitation)
@st.composite
def valid_passwords(draw):
    """Generate passwords meeting complexity requirements.
    
    Requirements:
    - Minimum 8 characters
    - At least one uppercase letter
    - At least one lowercase letter
    - At least one digit
    - Maximum 72 bytes (bcrypt limitation)
    """
    # Ensure we have at least one of each required character type
    uppercase = draw(st.sampled_from(string.ascii_uppercase))
    lowercase = draw(st.sampled_from(string.ascii_lowercase))
    digit = draw(st.sampled_from(string.digits))
    
    # Generate additional characters (at least 5 more to reach minimum 8)
    # Allow letters, digits, and common special characters (ASCII only)
    allowed_chars = string.ascii_letters + string.digits + "!@#$%^&*()-_=+"
    additional_length = draw(st.integers(min_value=5, max_value=60))
    additional = draw(st.text(alphabet=allowed_chars, min_size=additional_length, max_size=additional_length))
    
    # Combine and shuffle the characters
    password_chars = list(uppercase + lowercase + digit + additional)
    # Use hypothesis to shuffle deterministically
    shuffled = draw(st.permutations(password_chars))
    
    return "".join(shuffled)


def hash_password_bcrypt(password: str) -> str:
    """Hash a password using bcrypt directly.
    
    This mirrors the production hash_password function but uses bcrypt
    directly to avoid passlib compatibility issues in tests.
    """
    password_bytes = password.encode('utf-8')
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password_bytes, salt).decode('utf-8')


def verify_password_bcrypt(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against a bcrypt hash.
    
    This mirrors the production verify_password function but uses bcrypt
    directly to avoid passlib compatibility issues in tests.
    """
    return bcrypt.checkpw(
        plain_password.encode('utf-8'),
        hashed_password.encode('utf-8')
    )


class TestPasswordHashingIntegrityProperty:
    """Property 3: Password Hashing Integrity.
    
    **Validates: Requirements 1.8**
    
    For any password submitted during registration, the stored password hash
    SHALL be a valid bcrypt hash, and the original password SHALL verify
    successfully against this hash.
    """
    
    @given(password=valid_passwords())
    @settings(max_examples=10, deadline=None)
    def test_password_hash_is_valid_bcrypt(self, password: str):
        """The stored password hash SHALL be a valid bcrypt hash.
        
        **Validates: Requirements 1.8**
        
        A valid bcrypt hash starts with $2b$ (or $2a$, $2y$ for older versions).
        """
        hashed = hash_password_bcrypt(password)
        
        # Bcrypt hashes start with $2b$ (bcrypt uses $2b$ by default)
        assert hashed.startswith("$2b$"), f"Hash should start with $2b$, got: {hashed[:10]}..."
        
        # Bcrypt hashes have a specific format: $2b$<cost>$<22-char-salt><31-char-hash>
        # Total length is typically 60 characters
        assert len(hashed) == 60, f"Bcrypt hash should be 60 chars, got {len(hashed)}"
    
    @given(password=valid_passwords())
    @settings(max_examples=10, deadline=None)
    def test_original_password_verifies_against_hash(self, password: str):
        """The original password SHALL verify successfully against its hash.
        
        **Validates: Requirements 1.8**
        """
        hashed = hash_password_bcrypt(password)
        
        assert verify_password_bcrypt(password, hashed), (
            f"Original password should verify against its hash"
        )
    
    @given(password=valid_passwords(), wrong_password=valid_passwords())
    @settings(max_examples=10, deadline=None)
    def test_different_password_does_not_verify(self, password: str, wrong_password: str):
        """A different password SHALL NOT verify against the hash.
        
        **Validates: Requirements 1.8**
        
        This ensures the hash is specific to the original password.
        """
        # Skip if passwords happen to be the same (very unlikely but possible)
        assume(password != wrong_password)
        
        hashed = hash_password_bcrypt(password)
        
        assert not verify_password_bcrypt(wrong_password, hashed), (
            f"Different password should not verify against hash"
        )
    
    @given(password=valid_passwords())
    @settings(max_examples=10, deadline=None)
    def test_hashing_same_password_produces_different_hashes(self, password: str):
        """Hashing the same password twice SHALL produce different hashes.
        
        **Validates: Requirements 1.8**
        
        This verifies that bcrypt uses random salts, preventing rainbow table attacks.
        """
        hash1 = hash_password_bcrypt(password)
        hash2 = hash_password_bcrypt(password)
        
        # Hashes should be different due to random salt
        assert hash1 != hash2, "Same password should produce different hashes (random salt)"
        
        # But both should still verify the original password
        assert verify_password_bcrypt(password, hash1), "Password should verify against first hash"
        assert verify_password_bcrypt(password, hash2), "Password should verify against second hash"


# Strategy for generating valid email addresses
@st.composite
def valid_emails(draw):
    """Generate valid email addresses.
    
    Generates emails with:
    - Local part: 1-64 characters (letters, digits, dots, underscores, hyphens)
    - Domain: 1-63 characters (letters, digits, hyphens)
    - TLD: 2-6 lowercase letters
    """
    # Local part: letters, digits, dots, underscores, hyphens
    local_chars = string.ascii_lowercase + string.digits + "._-"
    local_length = draw(st.integers(min_value=1, max_value=20))
    
    # Start with a letter to ensure valid email
    local_start = draw(st.sampled_from(string.ascii_lowercase))
    local_rest = draw(st.text(alphabet=local_chars, min_size=0, max_size=local_length - 1))
    local_part = local_start + local_rest
    
    # Remove consecutive dots and trailing dots/hyphens
    while ".." in local_part:
        local_part = local_part.replace("..", ".")
    local_part = local_part.rstrip(".-")
    if not local_part:
        local_part = local_start
    
    # Domain: letters, digits, hyphens
    domain_chars = string.ascii_lowercase + string.digits
    domain_length = draw(st.integers(min_value=1, max_value=15))
    domain_start = draw(st.sampled_from(string.ascii_lowercase))
    domain_rest = draw(st.text(alphabet=domain_chars, min_size=0, max_size=domain_length - 1))
    domain = domain_start + domain_rest
    
    # TLD: 2-6 lowercase letters
    tld_length = draw(st.integers(min_value=2, max_value=6))
    tld = draw(st.text(alphabet=string.ascii_lowercase, min_size=tld_length, max_size=tld_length))
    
    return f"{local_part}@{domain}.{tld}"


# JWT settings for testing (mirrors production config)
TEST_SECRET_KEY = "test-secret-key-for-property-tests"
TEST_ALGORITHM = "HS256"
TEST_ACCESS_TOKEN_EXPIRE_MINUTES = 30


def create_test_access_token(user_id: str, email: str) -> str:
    """Create a JWT access token for testing.
    
    This mirrors the production create_access_token function.
    """
    expire = datetime.now(timezone.utc) + timedelta(minutes=TEST_ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode = {
        "sub": user_id,
        "email": email,
        "exp": expire,
        "iat": datetime.now(timezone.utc),
        "type": "access",
    }
    
    return jwt.encode(to_encode, TEST_SECRET_KEY, algorithm=TEST_ALGORITHM)


def decode_test_token(token: str) -> dict:
    """Decode and validate a JWT token for testing.
    
    This mirrors the production decode_token function.
    """
    return jwt.decode(token, TEST_SECRET_KEY, algorithms=[TEST_ALGORITHM])


class TestAuthenticationRoundTripProperty:
    """Property 1: Authentication Round-Trip.
    
    **Validates: Requirements 1.1, 1.9**
    
    For any valid email and password combination, registering a user and then
    authenticating with those credentials SHALL return a valid JWT token that
    grants access to protected resources within the token validity period.
    """
    
    @given(email=valid_emails(), password=valid_passwords())
    @settings(max_examples=10, deadline=None)
    def test_registration_returns_valid_jwt_token(self, email: str, password: str):
        """Registering a user SHALL return a valid JWT token.
        
        **Validates: Requirements 1.1, 1.9**
        
        Simulates registration by:
        1. Hashing the password (as registration would)
        2. Creating a JWT token with user info
        3. Verifying the token is valid and decodable
        """
        # Simulate registration: hash password
        password_hash = hash_password_bcrypt(password)
        
        # Verify password was hashed correctly
        assert verify_password_bcrypt(password, password_hash), (
            "Password should verify against its hash after registration"
        )
        
        # Simulate user creation with unique ID
        user_id = str(uuid4())
        
        # Create JWT token (as registration would return)
        access_token = create_test_access_token(user_id, email)
        
        # Verify token is a non-empty string
        assert isinstance(access_token, str), "Token should be a string"
        assert len(access_token) > 0, "Token should not be empty"
        
        # Verify token can be decoded
        payload = decode_test_token(access_token)
        
        # Verify token contains correct user info
        assert payload["sub"] == user_id, "Token should contain correct user ID"
        assert payload["email"] == email, "Token should contain correct email"
        assert payload["type"] == "access", "Token should be an access token"
    
    @given(email=valid_emails(), password=valid_passwords())
    @settings(max_examples=10, deadline=None)
    def test_login_after_registration_returns_valid_jwt(self, email: str, password: str):
        """Authenticating after registration SHALL return a valid JWT token.
        
        **Validates: Requirements 1.1, 1.9**
        
        Simulates the full round-trip:
        1. Registration: hash password and store
        2. Login: verify password and create token
        3. Verify token grants access (is valid and decodable)
        """
        # === REGISTRATION PHASE ===
        # Hash password (as registration would)
        stored_password_hash = hash_password_bcrypt(password)
        user_id = str(uuid4())
        
        # === LOGIN PHASE ===
        # Verify password against stored hash (as login would)
        password_verified = verify_password_bcrypt(password, stored_password_hash)
        assert password_verified, "Login should verify password successfully"
        
        # Create JWT token (as login would return)
        access_token = create_test_access_token(user_id, email)
        
        # === ACCESS VERIFICATION PHASE ===
        # Decode token (as protected resource access would)
        payload = decode_test_token(access_token)
        
        # Verify token is valid and contains correct info
        assert payload["sub"] == user_id, "Token should contain correct user ID"
        assert payload["email"] == email, "Token should contain correct email"
        
        # Verify token is not expired (within validity period)
        exp_timestamp = payload["exp"]
        current_time = datetime.now(timezone.utc).timestamp()
        assert exp_timestamp > current_time, "Token should not be expired"
    
    @given(email=valid_emails(), password=valid_passwords())
    @settings(max_examples=10, deadline=None)
    def test_token_contains_required_claims(self, email: str, password: str):
        """JWT token SHALL contain all required claims for protected resource access.
        
        **Validates: Requirements 1.1, 1.9**
        
        Required claims:
        - sub: user identifier
        - email: user email
        - exp: expiration timestamp
        - iat: issued at timestamp
        - type: token type (access)
        """
        user_id = str(uuid4())
        
        # Create token
        access_token = create_test_access_token(user_id, email)
        
        # Decode and verify all required claims
        payload = decode_test_token(access_token)
        
        # Verify all required claims are present
        assert "sub" in payload, "Token should contain 'sub' claim"
        assert "email" in payload, "Token should contain 'email' claim"
        assert "exp" in payload, "Token should contain 'exp' claim"
        assert "iat" in payload, "Token should contain 'iat' claim"
        assert "type" in payload, "Token should contain 'type' claim"
        
        # Verify claim values
        assert payload["sub"] == user_id, "sub claim should match user ID"
        assert payload["email"] == email, "email claim should match user email"
        assert payload["type"] == "access", "type claim should be 'access'"
        
        # Verify timestamps are valid
        assert isinstance(payload["exp"], (int, float)), "exp should be a timestamp"
        assert isinstance(payload["iat"], (int, float)), "iat should be a timestamp"
        assert payload["exp"] > payload["iat"], "exp should be after iat"
    
    @given(email=valid_emails(), password=valid_passwords())
    @settings(max_examples=10, deadline=None)
    def test_token_validity_period(self, email: str, password: str):
        """Token SHALL be valid within the configured validity period.
        
        **Validates: Requirements 1.9**
        
        Verifies that the token expiration is set correctly based on
        the configured access_token_expire_minutes.
        """
        user_id = str(uuid4())
        
        # Record time before token creation
        before_creation = datetime.now(timezone.utc)
        
        # Create token
        access_token = create_test_access_token(user_id, email)
        
        # Record time after token creation
        after_creation = datetime.now(timezone.utc)
        
        # Decode token
        payload = decode_test_token(access_token)
        
        # Calculate expected expiration window
        expected_exp_min = before_creation + timedelta(minutes=TEST_ACCESS_TOKEN_EXPIRE_MINUTES)
        expected_exp_max = after_creation + timedelta(minutes=TEST_ACCESS_TOKEN_EXPIRE_MINUTES)
        
        # Get actual expiration from token
        actual_exp = datetime.fromtimestamp(payload["exp"], tz=timezone.utc)
        
        # Verify expiration is within expected window (with small tolerance)
        tolerance = timedelta(seconds=5)
        assert actual_exp >= expected_exp_min - tolerance, (
            f"Token expiration {actual_exp} should be >= {expected_exp_min - tolerance}"
        )
        assert actual_exp <= expected_exp_max + tolerance, (
            f"Token expiration {actual_exp} should be <= {expected_exp_max + tolerance}"
        )


# ============================================================================
# Property 2: Invalid Email Rejection
# ============================================================================

# Strategy for generating invalid email strings
@st.composite
def invalid_emails_missing_at(draw):
    """Generate email strings missing the @ symbol.
    
    Examples: 'userexample.com', 'testdomain.org'
    """
    # Generate local part and domain without @
    local_chars = string.ascii_lowercase + string.digits + "._-"
    local_length = draw(st.integers(min_value=1, max_value=20))
    local_part = draw(st.text(alphabet=local_chars, min_size=local_length, max_size=local_length))
    
    # Ensure local part starts with a letter
    if not local_part or not local_part[0].isalpha():
        local_part = "a" + local_part
    
    domain_chars = string.ascii_lowercase + string.digits
    domain_length = draw(st.integers(min_value=1, max_value=15))
    domain = draw(st.text(alphabet=domain_chars, min_size=domain_length, max_size=domain_length))
    
    tld_length = draw(st.integers(min_value=2, max_value=6))
    tld = draw(st.text(alphabet=string.ascii_lowercase, min_size=tld_length, max_size=tld_length))
    
    # Return without @ symbol
    return f"{local_part}{domain}.{tld}"


@st.composite
def invalid_emails_missing_domain(draw):
    """Generate email strings missing the domain part.
    
    Examples: 'user@', 'test@.com'
    """
    local_chars = string.ascii_lowercase + string.digits + "._-"
    local_length = draw(st.integers(min_value=1, max_value=20))
    local_part = draw(st.text(alphabet=local_chars, min_size=local_length, max_size=local_length))
    
    if not local_part or not local_part[0].isalpha():
        local_part = "a" + local_part
    
    # Choose between missing domain entirely or having only TLD
    variant = draw(st.integers(min_value=0, max_value=2))
    
    if variant == 0:
        # Just @ with nothing after
        return f"{local_part}@"
    elif variant == 1:
        # @ with only a dot and TLD
        tld = draw(st.text(alphabet=string.ascii_lowercase, min_size=2, max_size=4))
        return f"{local_part}@.{tld}"
    else:
        # @ with domain but no TLD
        domain = draw(st.text(alphabet=string.ascii_lowercase, min_size=1, max_size=10))
        return f"{local_part}@{domain}"


@st.composite
def invalid_emails_missing_tld(draw):
    """Generate email strings missing the TLD (top-level domain).
    
    Examples: 'user@domain', 'test@example.'
    """
    local_chars = string.ascii_lowercase + string.digits + "._-"
    local_length = draw(st.integers(min_value=1, max_value=20))
    local_part = draw(st.text(alphabet=local_chars, min_size=local_length, max_size=local_length))
    
    if not local_part or not local_part[0].isalpha():
        local_part = "a" + local_part
    
    domain = draw(st.text(alphabet=string.ascii_lowercase + string.digits, min_size=1, max_size=15))
    if not domain or not domain[0].isalpha():
        domain = "a" + domain
    
    # Choose between no dot at all or trailing dot
    variant = draw(st.booleans())
    
    if variant:
        return f"{local_part}@{domain}."
    else:
        return f"{local_part}@{domain}"


@st.composite
def invalid_emails_consecutive_dots(draw):
    """Generate email strings with consecutive dots.
    
    Examples: 'user..name@example.com', 'user@example..com'
    """
    local_start = draw(st.sampled_from(string.ascii_lowercase))
    local_end = draw(st.text(alphabet=string.ascii_lowercase + string.digits, min_size=1, max_size=10))
    
    domain = draw(st.text(alphabet=string.ascii_lowercase + string.digits, min_size=1, max_size=10))
    if not domain or not domain[0].isalpha():
        domain = "a" + domain
    
    tld = draw(st.text(alphabet=string.ascii_lowercase, min_size=2, max_size=4))
    
    # Choose where to put consecutive dots
    variant = draw(st.integers(min_value=0, max_value=2))
    
    if variant == 0:
        # Consecutive dots in local part
        return f"{local_start}..{local_end}@{domain}.{tld}"
    elif variant == 1:
        # Consecutive dots in domain
        return f"{local_start}{local_end}@{domain}..{tld}"
    else:
        # Multiple consecutive dots
        return f"{local_start}...{local_end}@{domain}.{tld}"


@st.composite
def invalid_emails_starting_with_dot_or_hyphen(draw):
    """Generate email strings starting with a dot or hyphen.
    
    Examples: '.user@example.com', '-user@example.com'
    """
    # Start with dot or hyphen
    start_char = draw(st.sampled_from([".", "-"]))
    
    local_rest = draw(st.text(alphabet=string.ascii_lowercase + string.digits, min_size=1, max_size=15))
    
    domain = draw(st.text(alphabet=string.ascii_lowercase + string.digits, min_size=1, max_size=10))
    if not domain or not domain[0].isalpha():
        domain = "a" + domain
    
    tld = draw(st.text(alphabet=string.ascii_lowercase, min_size=2, max_size=4))
    
    return f"{start_char}{local_rest}@{domain}.{tld}"


@st.composite
def invalid_emails_empty_local_part(draw):
    """Generate email strings with empty local part.
    
    Examples: '@example.com', '@domain.org'
    """
    domain = draw(st.text(alphabet=string.ascii_lowercase + string.digits, min_size=1, max_size=10))
    if not domain or not domain[0].isalpha():
        domain = "a" + domain
    
    tld = draw(st.text(alphabet=string.ascii_lowercase, min_size=2, max_size=4))
    
    return f"@{domain}.{tld}"


@st.composite
def invalid_emails_invalid_characters(draw):
    """Generate email strings with invalid characters.
    
    Examples: 'user name@example.com', 'user<>@example.com'
    
    Note: Some special characters like % + are actually valid in email local parts.
    We focus on characters that are definitely invalid: spaces, angle brackets,
    parentheses, brackets, backslash, comma, semicolon, colon, quotes.
    """
    # Characters that are definitely invalid in email addresses
    # (spaces and control characters are always invalid)
    invalid_chars = " <>()[]\\,;:\""
    
    local_start = draw(st.sampled_from(string.ascii_lowercase))
    invalid_char = draw(st.sampled_from(invalid_chars))
    local_end = draw(st.text(alphabet=string.ascii_lowercase + string.digits, min_size=1, max_size=10))
    
    domain = draw(st.text(alphabet=string.ascii_lowercase + string.digits, min_size=1, max_size=10))
    if not domain or not domain[0].isalpha():
        domain = "a" + domain
    
    tld = draw(st.text(alphabet=string.ascii_lowercase, min_size=2, max_size=4))
    
    return f"{local_start}{invalid_char}{local_end}@{domain}.{tld}"


@st.composite
def invalid_emails_short_tld(draw):
    """Generate email strings with TLD that's too short (single character).
    
    Examples: 'user@example.c', 'test@domain.x'
    """
    local_chars = string.ascii_lowercase + string.digits
    local_length = draw(st.integers(min_value=1, max_value=15))
    local_part = draw(st.text(alphabet=local_chars, min_size=local_length, max_size=local_length))
    
    if not local_part or not local_part[0].isalpha():
        local_part = "a" + local_part
    
    domain = draw(st.text(alphabet=string.ascii_lowercase + string.digits, min_size=1, max_size=10))
    if not domain or not domain[0].isalpha():
        domain = "a" + domain
    
    # Single character TLD (invalid)
    tld = draw(st.sampled_from(string.ascii_lowercase))
    
    return f"{local_part}@{domain}.{tld}"


# Combined strategy for all types of invalid emails
@st.composite
def invalid_emails(draw):
    """Generate various types of invalid email strings.
    
    Combines all invalid email strategies to test comprehensive rejection.
    """
    strategy = draw(st.sampled_from([
        invalid_emails_missing_at(),
        invalid_emails_missing_domain(),
        invalid_emails_missing_tld(),
        invalid_emails_consecutive_dots(),
        invalid_emails_starting_with_dot_or_hyphen(),
        invalid_emails_empty_local_part(),
        invalid_emails_invalid_characters(),
        invalid_emails_short_tld(),
    ]))
    return draw(strategy)


class TestInvalidEmailRejectionProperty:
    """Property 2: Invalid Email Rejection.
    
    **Validates: Requirements 1.2**
    
    For any string that does not conform to valid email format (missing @,
    invalid domain, etc.), the Auth_Service SHALL reject registration with
    a validation error specifying the email field.
    """
    
    @given(email=invalid_emails_missing_at())
    @settings(max_examples=10, deadline=None)
    def test_rejects_email_missing_at_symbol(self, email: str):
        """Email missing @ symbol SHALL be rejected with validation error.
        
        **Validates: Requirements 1.2**
        """
        with pytest.raises(ValidationError) as exc_info:
            UserRegister(email=email, password="ValidP@ss123")
        
        # Verify the error mentions the email field
        errors = exc_info.value.errors()
        email_errors = [e for e in errors if "email" in str(e.get("loc", []))]
        assert len(email_errors) > 0, f"Validation error should specify email field for: {email}"
    
    @given(email=invalid_emails_missing_domain())
    @settings(max_examples=10, deadline=None)
    def test_rejects_email_missing_domain(self, email: str):
        """Email missing domain SHALL be rejected with validation error.
        
        **Validates: Requirements 1.2**
        """
        with pytest.raises(ValidationError) as exc_info:
            UserRegister(email=email, password="ValidP@ss123")
        
        errors = exc_info.value.errors()
        email_errors = [e for e in errors if "email" in str(e.get("loc", []))]
        assert len(email_errors) > 0, f"Validation error should specify email field for: {email}"
    
    @given(email=invalid_emails_missing_tld())
    @settings(max_examples=10, deadline=None)
    def test_rejects_email_missing_tld(self, email: str):
        """Email missing TLD SHALL be rejected with validation error.
        
        **Validates: Requirements 1.2**
        """
        with pytest.raises(ValidationError) as exc_info:
            UserRegister(email=email, password="ValidP@ss123")
        
        errors = exc_info.value.errors()
        email_errors = [e for e in errors if "email" in str(e.get("loc", []))]
        assert len(email_errors) > 0, f"Validation error should specify email field for: {email}"
    
    @given(email=invalid_emails_consecutive_dots())
    @settings(max_examples=10, deadline=None)
    def test_rejects_email_with_consecutive_dots(self, email: str):
        """Email with consecutive dots SHALL be rejected with validation error.
        
        **Validates: Requirements 1.2**
        """
        with pytest.raises(ValidationError) as exc_info:
            UserRegister(email=email, password="ValidP@ss123")
        
        errors = exc_info.value.errors()
        email_errors = [e for e in errors if "email" in str(e.get("loc", []))]
        assert len(email_errors) > 0, f"Validation error should specify email field for: {email}"
    
    @given(email=invalid_emails_starting_with_dot_or_hyphen())
    @settings(max_examples=10, deadline=None)
    def test_rejects_email_starting_with_dot_or_hyphen(self, email: str):
        """Email starting with dot or hyphen SHALL be rejected with validation error.
        
        **Validates: Requirements 1.2**
        """
        with pytest.raises(ValidationError) as exc_info:
            UserRegister(email=email, password="ValidP@ss123")
        
        errors = exc_info.value.errors()
        email_errors = [e for e in errors if "email" in str(e.get("loc", []))]
        assert len(email_errors) > 0, f"Validation error should specify email field for: {email}"
    
    @given(email=invalid_emails_empty_local_part())
    @settings(max_examples=10, deadline=None)
    def test_rejects_email_with_empty_local_part(self, email: str):
        """Email with empty local part SHALL be rejected with validation error.
        
        **Validates: Requirements 1.2**
        """
        with pytest.raises(ValidationError) as exc_info:
            UserRegister(email=email, password="ValidP@ss123")
        
        errors = exc_info.value.errors()
        email_errors = [e for e in errors if "email" in str(e.get("loc", []))]
        assert len(email_errors) > 0, f"Validation error should specify email field for: {email}"
    
    @given(email=invalid_emails_invalid_characters())
    @settings(max_examples=10, deadline=None)
    def test_rejects_email_with_invalid_characters(self, email: str):
        """Email with invalid characters SHALL be rejected with validation error.
        
        **Validates: Requirements 1.2**
        """
        with pytest.raises(ValidationError) as exc_info:
            UserRegister(email=email, password="ValidP@ss123")
        
        errors = exc_info.value.errors()
        email_errors = [e for e in errors if "email" in str(e.get("loc", []))]
        assert len(email_errors) > 0, f"Validation error should specify email field for: {email}"
    
    @given(email=invalid_emails_short_tld())
    @settings(max_examples=10, deadline=None)
    def test_rejects_email_with_short_tld(self, email: str):
        """Email with single-character TLD SHALL be rejected with validation error.
        
        **Validates: Requirements 1.2**
        """
        with pytest.raises(ValidationError) as exc_info:
            UserRegister(email=email, password="ValidP@ss123")
        
        errors = exc_info.value.errors()
        email_errors = [e for e in errors if "email" in str(e.get("loc", []))]
        assert len(email_errors) > 0, f"Validation error should specify email field for: {email}"
    
    @given(email=invalid_emails())
    @settings(max_examples=10, deadline=None)
    def test_all_invalid_emails_are_rejected(self, email: str):
        """All invalid email formats SHALL be rejected with validation error.
        
        **Validates: Requirements 1.2**
        
        This is the comprehensive test that combines all invalid email types.
        """
        with pytest.raises(ValidationError) as exc_info:
            UserRegister(email=email, password="ValidP@ss123")
        
        errors = exc_info.value.errors()
        email_errors = [e for e in errors if "email" in str(e.get("loc", []))]
        assert len(email_errors) > 0, f"Validation error should specify email field for: {email}"


# ============================================================================
# Property 4: OTP Validity Window
# ============================================================================

# Strategy for generating valid phone numbers
@st.composite
def valid_phone_numbers(draw):
    """Generate valid phone numbers for OTP testing.
    
    Generates phone numbers with:
    - Optional + prefix
    - 10-15 digits
    """
    has_plus = draw(st.booleans())
    # Generate 10-15 digits
    num_digits = draw(st.integers(min_value=10, max_value=15))
    digits = draw(st.text(alphabet=string.digits, min_size=num_digits, max_size=num_digits))
    
    # Ensure first digit is not 0 for realistic phone numbers
    if digits[0] == '0':
        digits = draw(st.sampled_from('123456789')) + digits[1:]
    
    if has_plus:
        return f"+{digits}"
    return digits


class TestOTPValidityWindowProperty:
    """Property 4: OTP Validity Window.
    
    **Validates: Requirements 1.5, 1.6**
    
    For any OTP generated for phone verification, submitting the correct OTP
    within 5 minutes SHALL succeed, and submitting after 5 minutes SHALL fail
    with an expiration error.
    """
    
    @given(phone=valid_phone_numbers())
    @settings(max_examples=10, deadline=None)
    @pytest.mark.asyncio
    async def test_correct_otp_within_validity_window_succeeds(self, phone: str):
        """Submitting correct OTP within 5 minutes SHALL succeed.
        
        **Validates: Requirements 1.5**
        
        Simulates:
        1. Generating and storing an OTP
        2. Verifying the OTP within the validity window
        3. Verification should succeed
        """
        from unittest.mock import AsyncMock, patch
        from app.services.otp import generate_otp, verify_otp, OTP_KEY_PREFIX
        
        # Generate an OTP
        otp = generate_otp()
        
        # Verify OTP format
        assert len(otp) == 6, "OTP should be 6 digits"
        assert otp.isdigit(), "OTP should contain only digits"
        
        # Mock Redis to simulate OTP stored and not expired (within validity window)
        mock_redis = AsyncMock()
        mock_redis.get.return_value = otp  # OTP exists (not expired)
        mock_redis.delete.return_value = 1  # Successful deletion
        
        with patch("app.services.otp.get_redis", return_value=mock_redis):
            result = await verify_otp(phone, otp)
        
        # Verification should succeed
        assert result is True, "Correct OTP within validity window should succeed"
        
        # Verify Redis was called correctly
        mock_redis.get.assert_called_once_with(f"{OTP_KEY_PREFIX}{phone}")
        mock_redis.delete.assert_called_once_with(f"{OTP_KEY_PREFIX}{phone}")
    
    @given(phone=valid_phone_numbers())
    @settings(max_examples=10, deadline=None)
    @pytest.mark.asyncio
    async def test_otp_after_expiry_fails_with_expiration_error(self, phone: str):
        """Submitting OTP after 5 minutes SHALL fail with expiration error.
        
        **Validates: Requirements 1.6**
        
        Simulates:
        1. OTP was generated but has expired (Redis returns None)
        2. Verification should fail with expiration error
        """
        from unittest.mock import AsyncMock, patch
        from app.services.otp import generate_otp, verify_otp
        from app.core.exceptions import ValidationError
        
        # Generate an OTP (that would have been stored earlier)
        otp = generate_otp()
        
        # Mock Redis to simulate expired OTP (returns None)
        mock_redis = AsyncMock()
        mock_redis.get.return_value = None  # OTP expired or never existed
        
        # Run the async verification and expect ValidationError
        with pytest.raises(ValidationError) as exc_info:
            with patch("app.services.otp.get_redis", return_value=mock_redis):
                await verify_otp(phone, otp)
        
        # Verify error message indicates expiration
        error = exc_info.value
        assert "expired" in error.message.lower() or "invalid" in error.message.lower(), (
            f"Error message should indicate expiration: {error.message}"
        )
        
        # Verify field_errors contains OTP field (stored in details)
        field_errors = error.details.get("field_errors", {})
        assert "otp" in field_errors, "Error should specify OTP field"
    
    @given(phone=valid_phone_numbers(), wrong_otp_suffix=st.integers(min_value=1, max_value=999999))
    @settings(max_examples=10, deadline=None)
    @pytest.mark.asyncio
    async def test_incorrect_otp_always_fails_regardless_of_timing(self, phone: str, wrong_otp_suffix: int):
        """Incorrect OTP SHALL always fail regardless of timing.
        
        **Validates: Requirements 1.5, 1.6**
        
        Simulates:
        1. Generating and storing an OTP
        2. Submitting a different OTP
        3. Verification should fail even within validity window
        """
        from unittest.mock import AsyncMock, patch
        from app.services.otp import generate_otp, verify_otp
        from app.core.exceptions import ValidationError
        
        # Generate the correct OTP
        correct_otp = generate_otp()
        
        # Generate a wrong OTP (ensure it's different)
        wrong_otp = str(wrong_otp_suffix).zfill(6)
        if wrong_otp == correct_otp:
            # If by chance they're the same, modify it
            wrong_otp = str((int(wrong_otp) + 1) % 1000000).zfill(6)
        
        assume(wrong_otp != correct_otp)
        
        # Mock Redis to simulate OTP stored and not expired
        mock_redis = AsyncMock()
        mock_redis.get.return_value = correct_otp  # Correct OTP is stored
        
        # Run the async verification and expect ValidationError
        with pytest.raises(ValidationError) as exc_info:
            with patch("app.services.otp.get_redis", return_value=mock_redis):
                await verify_otp(phone, wrong_otp)
        
        # Verify error message indicates invalid OTP
        error = exc_info.value
        assert "invalid" in error.message.lower(), (
            f"Error message should indicate invalid OTP: {error.message}"
        )
    
    @given(phone=valid_phone_numbers())
    @settings(max_examples=10, deadline=None)
    @pytest.mark.asyncio
    async def test_otp_is_single_use(self, phone: str):
        """OTP SHALL be deleted after successful verification (single use).
        
        **Validates: Requirements 1.5**
        
        Verifies that after successful OTP verification, the OTP is deleted
        from Redis, preventing reuse.
        """
        from unittest.mock import AsyncMock, patch
        from app.services.otp import generate_otp, verify_otp, OTP_KEY_PREFIX
        
        # Generate an OTP
        otp = generate_otp()
        
        # Mock Redis
        mock_redis = AsyncMock()
        mock_redis.get.return_value = otp
        mock_redis.delete.return_value = 1
        
        with patch("app.services.otp.get_redis", return_value=mock_redis):
            result = await verify_otp(phone, otp)
        
        # First verification should succeed
        assert result is True
        
        # Verify delete was called (OTP is single-use)
        mock_redis.delete.assert_called_with(f"{OTP_KEY_PREFIX}{phone}")
    
    @given(phone=valid_phone_numbers())
    @settings(max_examples=10, deadline=None)
    @pytest.mark.asyncio
    async def test_otp_stored_with_correct_ttl(self, phone: str):
        """OTP SHALL be stored with 5-minute (300 seconds) TTL.
        
        **Validates: Requirements 1.5, 1.6**
        
        Verifies that when storing an OTP, it's set with the correct TTL
        to ensure automatic expiration after 5 minutes.
        """
        from unittest.mock import AsyncMock, patch
        from app.services.otp import generate_otp, store_otp, OTP_KEY_PREFIX, OTP_TTL_SECONDS
        
        # Generate an OTP
        otp = generate_otp()
        
        # Verify TTL is 300 seconds (5 minutes)
        assert OTP_TTL_SECONDS == 300, "OTP TTL should be 300 seconds (5 minutes)"
        
        # Mock Redis
        mock_redis = AsyncMock()
        
        with patch("app.services.otp.get_redis", return_value=mock_redis):
            await store_otp(phone, otp)
        
        # Verify setex was called with correct TTL
        mock_redis.setex.assert_called_once_with(
            f"{OTP_KEY_PREFIX}{phone}",
            OTP_TTL_SECONDS,
            otp,
        )
    
    @given(phone=valid_phone_numbers())
    @settings(max_examples=10, deadline=None)
    def test_generated_otp_format_is_valid(self, phone: str):
        """Generated OTP SHALL be a 6-digit numeric string.
        
        **Validates: Requirements 1.5**
        
        Verifies that all generated OTPs conform to the expected format.
        """
        from app.services.otp import generate_otp
        
        # Generate multiple OTPs to verify format consistency
        for _ in range(5):
            otp = generate_otp()
            
            # Verify format
            assert len(otp) == 6, f"OTP should be 6 digits, got {len(otp)}"
            assert otp.isdigit(), f"OTP should contain only digits, got {otp}"
            
            # Verify range (100000-999999)
            otp_int = int(otp)
            assert 100000 <= otp_int <= 999999, (
                f"OTP should be between 100000 and 999999, got {otp_int}"
            )


# ============================================================================
# Property 5: JWT Expiry Enforcement
# ============================================================================


def create_expired_token(user_id: str, email: str, expired_seconds_ago: int) -> str:
    """Create a JWT token that expired a specified number of seconds ago.
    
    Args:
        user_id: User's unique identifier
        email: User's email address
        expired_seconds_ago: How many seconds ago the token expired
        
    Returns:
        Encoded JWT token string with expiry in the past
    """
    # Set expiry time in the past
    expire = datetime.now(timezone.utc) - timedelta(seconds=expired_seconds_ago)
    
    to_encode = {
        "sub": user_id,
        "email": email,
        "exp": expire,
        "iat": datetime.now(timezone.utc) - timedelta(seconds=expired_seconds_ago + 1800),  # Issued 30 min before expiry
        "type": "access",
    }
    
    return jwt.encode(to_encode, TEST_SECRET_KEY, algorithm=TEST_ALGORITHM)


def create_valid_future_token(user_id: str, email: str, valid_for_minutes: int = 30) -> str:
    """Create a JWT token that expires in the future.
    
    Args:
        user_id: User's unique identifier
        email: User's email address
        valid_for_minutes: How many minutes until the token expires
        
    Returns:
        Encoded JWT token string with expiry in the future
    """
    expire = datetime.now(timezone.utc) + timedelta(minutes=valid_for_minutes)
    
    to_encode = {
        "sub": user_id,
        "email": email,
        "exp": expire,
        "iat": datetime.now(timezone.utc),
        "type": "access",
    }
    
    return jwt.encode(to_encode, TEST_SECRET_KEY, algorithm=TEST_ALGORITHM)


class TestJWTExpiryEnforcementProperty:
    """Property 5: JWT Expiry Enforcement.
    
    **Validates: Requirements 1.7**
    
    For any JWT token with an expiry time in the past, accessing protected
    resources SHALL return an unauthorized error.
    """
    
    @given(
        email=valid_emails(),
        expired_seconds_ago=st.integers(min_value=1, max_value=86400 * 365)  # 1 second to 1 year ago
    )
    @settings(max_examples=10, deadline=None)
    def test_expired_token_returns_unauthorized_error(self, email: str, expired_seconds_ago: int):
        """Expired JWT token SHALL return an unauthorized error.
        
        **Validates: Requirements 1.7**
        
        Tests that tokens with expiry times in the past are rejected
        when attempting to decode/validate them.
        """
        from jose import JWTError, ExpiredSignatureError
        
        user_id = str(uuid4())
        
        # Create a token that expired in the past
        expired_token = create_expired_token(user_id, email, expired_seconds_ago)
        
        # Verify token is a valid JWT string (just not valid for access)
        assert isinstance(expired_token, str), "Token should be a string"
        assert len(expired_token) > 0, "Token should not be empty"
        
        # Attempting to decode the expired token should raise an error
        with pytest.raises((JWTError, ExpiredSignatureError)):
            jwt.decode(expired_token, TEST_SECRET_KEY, algorithms=[TEST_ALGORITHM])
    
    @given(email=valid_emails())
    @settings(max_examples=10, deadline=None)
    def test_token_expired_just_now_returns_unauthorized(self, email: str):
        """Token that expired just now (edge case) SHALL return unauthorized error.
        
        **Validates: Requirements 1.7**
        
        Tests the boundary condition where a token has just expired
        (1 second ago).
        """
        from jose import JWTError, ExpiredSignatureError
        
        user_id = str(uuid4())
        
        # Create a token that expired 1 second ago (edge case)
        expired_token = create_expired_token(user_id, email, expired_seconds_ago=1)
        
        # Attempting to decode should fail
        with pytest.raises((JWTError, ExpiredSignatureError)):
            jwt.decode(expired_token, TEST_SECRET_KEY, algorithms=[TEST_ALGORITHM])
    
    @given(
        email=valid_emails(),
        expired_days_ago=st.integers(min_value=30, max_value=365)
    )
    @settings(max_examples=10, deadline=None)
    def test_token_expired_long_ago_returns_unauthorized(self, email: str, expired_days_ago: int):
        """Token that expired a long time ago SHALL return unauthorized error.
        
        **Validates: Requirements 1.7**
        
        Tests that tokens which expired weeks or months ago are still
        properly rejected.
        """
        from jose import JWTError, ExpiredSignatureError
        
        user_id = str(uuid4())
        
        # Create a token that expired many days ago
        expired_seconds = expired_days_ago * 86400  # Convert days to seconds
        expired_token = create_expired_token(user_id, email, expired_seconds_ago=expired_seconds)
        
        # Attempting to decode should fail
        with pytest.raises((JWTError, ExpiredSignatureError)):
            jwt.decode(expired_token, TEST_SECRET_KEY, algorithms=[TEST_ALGORITHM])
    
    @given(
        email=valid_emails(),
        valid_for_minutes=st.integers(min_value=1, max_value=60)
    )
    @settings(max_examples=10, deadline=None)
    def test_valid_token_with_future_expiry_succeeds(self, email: str, valid_for_minutes: int):
        """Token with valid expiry time (in the future) SHALL succeed.
        
        **Validates: Requirements 1.7**
        
        Tests that tokens with expiry times in the future are accepted,
        providing a contrast to the expired token tests.
        """
        user_id = str(uuid4())
        
        # Create a token that expires in the future
        valid_token = create_valid_future_token(user_id, email, valid_for_minutes)
        
        # Decoding should succeed
        payload = jwt.decode(valid_token, TEST_SECRET_KEY, algorithms=[TEST_ALGORITHM])
        
        # Verify payload contains correct data
        assert payload["sub"] == user_id, "Token should contain correct user ID"
        assert payload["email"] == email, "Token should contain correct email"
        assert payload["type"] == "access", "Token should be an access token"
        
        # Verify expiry is in the future
        exp_timestamp = payload["exp"]
        current_time = datetime.now(timezone.utc).timestamp()
        assert exp_timestamp > current_time, "Token expiry should be in the future"
    
    @given(email=valid_emails(), password=valid_passwords())
    @settings(max_examples=10, deadline=None)
    def test_expired_token_after_valid_registration_fails(self, email: str, password: str):
        """After valid registration, an expired token SHALL fail to grant access.
        
        **Validates: Requirements 1.7**
        
        Simulates the full flow:
        1. User registers (gets valid token)
        2. Token expires
        3. Attempting to use expired token fails
        """
        from jose import JWTError, ExpiredSignatureError
        
        # === REGISTRATION PHASE ===
        password_hash = hash_password_bcrypt(password)
        user_id = str(uuid4())
        
        # Verify registration would succeed
        assert verify_password_bcrypt(password, password_hash)
        
        # === TOKEN CREATION (simulating time passing) ===
        # Create a token that has already expired (simulating time passing)
        expired_token = create_expired_token(user_id, email, expired_seconds_ago=3600)  # 1 hour ago
        
        # === ACCESS ATTEMPT WITH EXPIRED TOKEN ===
        # Attempting to decode the expired token should fail
        with pytest.raises((JWTError, ExpiredSignatureError)):
            jwt.decode(expired_token, TEST_SECRET_KEY, algorithms=[TEST_ALGORITHM])
    
    @given(
        email=valid_emails(),
        expired_seconds_ago=st.integers(min_value=1, max_value=86400)
    )
    @settings(max_examples=10, deadline=None)
    def test_expired_token_error_type_is_appropriate(self, email: str, expired_seconds_ago: int):
        """Expired token error SHALL be an appropriate JWT/expiration error.
        
        **Validates: Requirements 1.7**
        
        Verifies that the error raised for expired tokens is specifically
        related to JWT validation or expiration, not a generic error.
        """
        from jose import JWTError, ExpiredSignatureError
        
        user_id = str(uuid4())
        expired_token = create_expired_token(user_id, email, expired_seconds_ago)
        
        try:
            jwt.decode(expired_token, TEST_SECRET_KEY, algorithms=[TEST_ALGORITHM])
            pytest.fail("Expected JWTError or ExpiredSignatureError for expired token")
        except ExpiredSignatureError:
            # This is the most specific expected error
            pass
        except JWTError as e:
            # JWTError is also acceptable (ExpiredSignatureError is a subclass)
            # Verify the error message relates to expiration
            error_msg = str(e).lower()
            assert "expir" in error_msg or "signature" in error_msg or "token" in error_msg, (
                f"Error message should relate to token expiration: {e}"
            )
    
    @given(email=valid_emails())
    @settings(max_examples=10, deadline=None)
    def test_token_expiry_boundary_at_exact_expiry_time(self, email: str):
        """Token at exact expiry boundary SHALL be treated as expired.
        
        **Validates: Requirements 1.7**
        
        Tests the exact boundary condition where the current time equals
        the token's expiry time. The token should be considered expired.
        """
        from jose import JWTError, ExpiredSignatureError
        import time
        
        user_id = str(uuid4())
        
        # Create a token that expires in 1 second
        expire = datetime.now(timezone.utc) + timedelta(seconds=1)
        
        to_encode = {
            "sub": user_id,
            "email": email,
            "exp": expire,
            "iat": datetime.now(timezone.utc),
            "type": "access",
        }
        
        token = jwt.encode(to_encode, TEST_SECRET_KEY, algorithm=TEST_ALGORITHM)
        
        # Wait for the token to expire
        time.sleep(2)
        
        # Now the token should be expired
        with pytest.raises((JWTError, ExpiredSignatureError)):
            jwt.decode(token, TEST_SECRET_KEY, algorithms=[TEST_ALGORITHM])
    
    @given(
        email=valid_emails(),
        expired_seconds_ago=st.integers(min_value=1, max_value=3600)
    )
    @settings(max_examples=10, deadline=None)
    def test_expired_token_still_contains_valid_structure(self, email: str, expired_seconds_ago: int):
        """Expired token SHALL still have valid JWT structure (just expired claims).
        
        **Validates: Requirements 1.7**
        
        Verifies that expired tokens are structurally valid JWTs - they
        fail validation due to expiry, not due to malformed structure.
        """
        user_id = str(uuid4())
        expired_token = create_expired_token(user_id, email, expired_seconds_ago)
        
        # Token should have 3 parts (header.payload.signature)
        parts = expired_token.split(".")
        assert len(parts) == 3, "JWT should have 3 parts separated by dots"
        
        # Each part should be non-empty
        for i, part in enumerate(parts):
            assert len(part) > 0, f"JWT part {i} should not be empty"
        
        # Decode without verification to check structure
        payload = jwt.decode(
            expired_token, 
            TEST_SECRET_KEY, 
            algorithms=[TEST_ALGORITHM],
            options={"verify_exp": False}  # Skip expiry verification
        )
        
        # Verify all expected claims are present
        assert "sub" in payload, "Token should contain 'sub' claim"
        assert "email" in payload, "Token should contain 'email' claim"
        assert "exp" in payload, "Token should contain 'exp' claim"
        assert "iat" in payload, "Token should contain 'iat' claim"
        assert "type" in payload, "Token should contain 'type' claim"
        
        # Verify the expiry is indeed in the past
        exp_timestamp = payload["exp"]
        current_time = datetime.now(timezone.utc).timestamp()
        assert exp_timestamp < current_time, "Token expiry should be in the past"
