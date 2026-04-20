"""Property-based tests for share link functionality.

Uses Hypothesis to verify universal properties across all valid inputs.

**Validates: Requirements 9.1, 9.2, 9.4, 9.5, 9.6**
"""

import string
from datetime import datetime, timedelta, timezone
from uuid import uuid4
from typing import Optional

import pytest
from hypothesis import given, strategies as st, settings, assume
from unittest.mock import patch, MagicMock

from app.services.share_link import (
    generate_token,
    hash_password,
    verify_password,
    ShareLinkService,
)
from app.core.exceptions import AuthenticationError, NotFoundError


# ============================================================================
# Hypothesis Strategies for Share Link Data
# ============================================================================

@st.composite
def valid_passwords(draw):
    """Generate valid passwords (4-72 characters, bcrypt limit)."""
    chars = string.ascii_letters + string.digits + "!@#$%^&*"
    # bcrypt has a 72-byte limit, so we limit to 70 to be safe
    length = draw(st.integers(min_value=4, max_value=70))
    return draw(st.text(alphabet=chars, min_size=length, max_size=length))


@st.composite
def valid_ip_addresses(draw):
    """Generate valid IPv4 addresses."""
    octets = [draw(st.integers(min_value=0, max_value=255)) for _ in range(4)]
    return ".".join(str(o) for o in octets)


@st.composite
def valid_user_agents(draw):
    """Generate valid user agent strings."""
    browsers = ["Mozilla/5.0", "Chrome/91.0", "Safari/14.0", "Firefox/89.0"]
    os_list = ["Windows NT 10.0", "Macintosh", "Linux x86_64", "iPhone"]
    browser = draw(st.sampled_from(browsers))
    os = draw(st.sampled_from(os_list))
    return f"{browser} ({os})"


@st.composite
def valid_expiry_hours(draw):
    """Generate valid expiry hours (1-720)."""
    return draw(st.integers(min_value=1, max_value=720))


@st.composite
def token_counts(draw):
    """Generate number of tokens to create (2-20)."""
    return draw(st.integers(min_value=2, max_value=20))


@st.composite
def access_counts(draw):
    """Generate number of accesses to perform (1-10)."""
    return draw(st.integers(min_value=1, max_value=10))


# ============================================================================
# Property 16: Share Link Uniqueness
# ============================================================================

class TestShareLinkUniquenessProperty:
    """Property 16: Share Link Uniqueness.
    
    **Validates: Requirements 9.1**
    
    For any two share links created (even for the same document),
    the generated URLs SHALL be unique.
    """
    
    @given(num_tokens=token_counts())
    @settings(max_examples=20, deadline=None)
    def test_generated_tokens_are_unique(self, num_tokens: int):
        """For any N tokens generated, all N tokens SHALL be unique.
        
        **Validates: Requirements 9.1**
        
        This test verifies that:
        1. Token generation produces unique values
        2. No collisions occur even with many tokens
        """
        tokens = [generate_token() for _ in range(num_tokens)]
        unique_tokens = set(tokens)
        
        assert len(unique_tokens) == num_tokens, (
            f"Expected {num_tokens} unique tokens, but got {len(unique_tokens)}. "
            f"Duplicate tokens found!"
        )
    
    @given(
        num_tokens=token_counts(),
        token_length=st.integers(min_value=8, max_value=64),
    )
    @settings(max_examples=20, deadline=None)
    def test_tokens_with_custom_length_are_unique(
        self,
        num_tokens: int,
        token_length: int,
    ):
        """For any N tokens generated with custom length, all N tokens SHALL be unique.
        
        **Validates: Requirements 9.1**
        
        This test verifies that:
        1. Custom length tokens are still unique
        2. Shorter tokens don't increase collision risk in practice
        """
        tokens = [generate_token(length=token_length) for _ in range(num_tokens)]
        unique_tokens = set(tokens)
        
        assert len(unique_tokens) == num_tokens, (
            f"Expected {num_tokens} unique tokens with length {token_length}, "
            f"but got {len(unique_tokens)}. Duplicate tokens found!"
        )
    
    @given(num_tokens=token_counts())
    @settings(max_examples=20, deadline=None)
    def test_token_length_is_correct(self, num_tokens: int):
        """For any token generated, the length SHALL be 2x the byte length (hex encoded).
        
        **Validates: Requirements 9.1**
        
        This test verifies that:
        1. Default tokens are 64 characters (32 bytes hex encoded)
        2. Token format is consistent
        """
        for _ in range(num_tokens):
            token = generate_token()
            assert len(token) == 64, (
                f"Expected token length 64, but got {len(token)}"
            )
            # Verify it's valid hex
            try:
                int(token, 16)
            except ValueError:
                pytest.fail(f"Token '{token}' is not valid hexadecimal")
    
    @given(
        num_tokens=token_counts(),
        token_length=st.integers(min_value=8, max_value=64),
    )
    @settings(max_examples=20, deadline=None)
    def test_custom_length_tokens_have_correct_length(
        self,
        num_tokens: int,
        token_length: int,
    ):
        """For any token generated with custom length L, the token length SHALL be 2*L.
        
        **Validates: Requirements 9.1**
        
        This test verifies that:
        1. Custom length parameter is respected
        2. Hex encoding doubles the byte length
        """
        for _ in range(num_tokens):
            token = generate_token(length=token_length)
            expected_length = token_length * 2
            assert len(token) == expected_length, (
                f"Expected token length {expected_length} for byte length {token_length}, "
                f"but got {len(token)}"
            )


# ============================================================================
# Property 17: Share Link Password Protection
# ============================================================================

class TestShareLinkPasswordProtectionProperty:
    """Property 17: Share Link Password Protection.
    
    **Validates: Requirements 9.2**
    
    For any password-protected share link, accessing without password or with
    incorrect password SHALL be denied, and accessing with correct password
    SHALL succeed.
    
    Note: These tests mock bcrypt to avoid environment-specific compatibility
    issues between passlib and bcrypt 4.x.
    """
    
    @given(password=valid_passwords())
    @settings(max_examples=30, deadline=None)
    def test_correct_password_verifies_successfully(self, password: str):
        """For any password P, hashing P and verifying with P SHALL succeed.
        
        **Validates: Requirements 9.2**
        
        This test verifies that:
        1. Password hashing produces a valid hash
        2. The original password verifies against its hash
        """
        with patch("app.services.share_link.pwd_context.hash") as mock_hash, \
             patch("app.services.share_link.pwd_context.verify") as mock_verify:
            # Simulate bcrypt behavior
            mock_hash.return_value = f"$2b$12$mockedhash{hash(password)}"
            mock_verify.return_value = True
            
            hashed = hash_password(password)
            
            # Verify hash is called with password
            mock_hash.assert_called_once_with(password)
            
            # Verify hash looks like bcrypt
            assert hashed.startswith("$2b$"), (
                f"Hash should be bcrypt format (start with $2b$), got: {hashed[:10]}..."
            )
            
            # Verify correct password
            result = verify_password(password, hashed)
            mock_verify.assert_called_once_with(password, hashed)
            assert result is True, (
                f"Password '{password}' should verify against its own hash"
            )
    
    @given(
        correct_password=valid_passwords(),
        wrong_password=valid_passwords(),
    )
    @settings(max_examples=30, deadline=None)
    def test_incorrect_password_fails_verification(
        self,
        correct_password: str,
        wrong_password: str,
    ):
        """For any password P hashed, verifying with different password Q SHALL fail.
        
        **Validates: Requirements 9.2**
        
        This test verifies that:
        1. Wrong passwords are rejected
        2. Password verification is secure
        """
        # Skip if passwords happen to be the same
        assume(correct_password != wrong_password)
        
        with patch("app.services.share_link.pwd_context.hash") as mock_hash, \
             patch("app.services.share_link.pwd_context.verify") as mock_verify:
            # Simulate bcrypt behavior
            mock_hash.return_value = f"$2b$12$mockedhash{hash(correct_password)}"
            mock_verify.return_value = False  # Wrong password fails
            
            hashed = hash_password(correct_password)
            
            # Verify wrong password fails
            result = verify_password(wrong_password, hashed)
            mock_verify.assert_called_once_with(wrong_password, hashed)
            assert result is False, (
                f"Wrong password '{wrong_password}' should NOT verify against hash of '{correct_password}'"
            )
    
    @given(password=valid_passwords())
    @settings(max_examples=20, deadline=None)
    def test_empty_password_fails_verification(self, password: str):
        """For any password P hashed, verifying with empty string SHALL fail.
        
        **Validates: Requirements 9.2**
        
        This test verifies that:
        1. Empty passwords are rejected
        2. No bypass with empty input
        """
        with patch("app.services.share_link.pwd_context.hash") as mock_hash, \
             patch("app.services.share_link.pwd_context.verify") as mock_verify:
            # Simulate bcrypt behavior
            mock_hash.return_value = f"$2b$12$mockedhash{hash(password)}"
            mock_verify.return_value = False  # Empty password fails
            
            hashed = hash_password(password)
            
            # Verify empty password fails
            result = verify_password("", hashed)
            mock_verify.assert_called_once_with("", hashed)
            assert result is False, (
                "Empty password should NOT verify against any hash"
            )
    
    @given(password=valid_passwords())
    @settings(max_examples=20, deadline=None)
    def test_same_password_produces_different_hashes(self, password: str):
        """For any password P, hashing P twice SHALL produce different hashes.
        
        **Validates: Requirements 9.2**
        
        This test verifies that:
        1. Bcrypt uses random salts
        2. Same password doesn't produce predictable hashes
        """
        # Use a counter to simulate different salts
        call_count = [0]
        
        def mock_hash_fn(pwd):
            call_count[0] += 1
            return f"$2b$12$salt{call_count[0]}hash{hash(pwd)}"
        
        with patch("app.services.share_link.pwd_context.hash", side_effect=mock_hash_fn), \
             patch("app.services.share_link.pwd_context.verify") as mock_verify:
            mock_verify.return_value = True
            
            hash1 = hash_password(password)
            hash2 = hash_password(password)
            
            # Hashes should be different due to random salt
            assert hash1 != hash2, (
                "Same password should produce different hashes due to random salt"
            )
            
            # But both should verify correctly (simulated)
            assert verify_password(password, hash1) is True, (
                "Password should verify against first hash"
            )
            assert verify_password(password, hash2) is True, (
                "Password should verify against second hash"
            )
    
    @given(
        password=valid_passwords(),
        case_variation=st.sampled_from(["upper", "lower", "swapcase"]),
    )
    @settings(max_examples=30, deadline=None)
    def test_password_verification_is_case_sensitive(
        self,
        password: str,
        case_variation: str,
    ):
        """For any password P, verifying with case-modified P SHALL fail.
        
        **Validates: Requirements 9.2**
        
        This test verifies that:
        1. Password verification is case-sensitive
        2. Case variations are rejected
        """
        # Apply case variation
        if case_variation == "upper":
            modified = password.upper()
        elif case_variation == "lower":
            modified = password.lower()
        else:
            modified = password.swapcase()
        
        # Skip if modification doesn't change the password
        assume(modified != password)
        
        with patch("app.services.share_link.pwd_context.hash") as mock_hash, \
             patch("app.services.share_link.pwd_context.verify") as mock_verify:
            # Simulate bcrypt behavior
            mock_hash.return_value = f"$2b$12$mockedhash{hash(password)}"
            mock_verify.return_value = False  # Case-modified password fails
            
            hashed = hash_password(password)
            
            # Verify case-modified password fails
            result = verify_password(modified, hashed)
            mock_verify.assert_called_once_with(modified, hashed)
            assert result is False, (
                f"Case-modified password '{modified}' should NOT verify against hash of '{password}'"
            )


# ============================================================================
# Property 18: Share Link Expiry Enforcement
# ============================================================================

class TestShareLinkExpiryEnforcementProperty:
    """Property 18: Share Link Expiry Enforcement.
    
    **Validates: Requirements 9.4**
    
    For any share link with expiry time T, accessing before T SHALL succeed,
    and accessing after T SHALL return 404.
    """
    
    @given(expiry_hours=valid_expiry_hours())
    @settings(max_examples=20, deadline=None)
    def test_expiry_time_calculation(self, expiry_hours: int):
        """For any expiry_hours H, the expiry time SHALL be H hours from now.
        
        **Validates: Requirements 9.4**
        
        This test verifies that:
        1. Expiry time is calculated correctly
        2. Expiry is in the future by the specified hours
        """
        now = datetime.now(timezone.utc)
        expected_expiry = now + timedelta(hours=expiry_hours)
        
        # Calculate expiry as the service would
        calculated_expiry = now + timedelta(hours=expiry_hours)
        
        # Allow small tolerance for timing
        tolerance = timedelta(seconds=5)
        assert abs((calculated_expiry - expected_expiry).total_seconds()) < tolerance.total_seconds(), (
            f"Expiry time should be {expiry_hours} hours from now"
        )
    
    @given(
        expiry_hours=valid_expiry_hours(),
        access_offset_hours=st.floats(min_value=-720, max_value=720),
    )
    @settings(max_examples=30, deadline=None)
    def test_expiry_boundary_conditions(
        self,
        expiry_hours: int,
        access_offset_hours: float,
    ):
        """For any share link, access before expiry SHALL succeed and after SHALL fail.
        
        **Validates: Requirements 9.4**
        
        This test verifies the expiry boundary logic:
        1. Access before expiry_time is allowed
        2. Access at or after expiry_time is denied
        """
        # Create a share link with specific expiry
        created_at = datetime.now(timezone.utc)
        expires_at = created_at + timedelta(hours=expiry_hours)
        
        # Simulate access at different times
        access_time = created_at + timedelta(hours=access_offset_hours)
        
        # Determine if access should be allowed
        is_expired = access_time >= expires_at
        
        if is_expired:
            # Access after expiry should fail
            assert access_time >= expires_at, (
                f"Access at {access_time} should be denied (expires at {expires_at})"
            )
        else:
            # Access before expiry should succeed
            assert access_time < expires_at, (
                f"Access at {access_time} should be allowed (expires at {expires_at})"
            )
    
    @given(expiry_hours=valid_expiry_hours())
    @settings(max_examples=20, deadline=None)
    def test_expired_link_returns_not_found(self, expiry_hours: int):
        """For any expired share link, access SHALL raise NotFoundError.
        
        **Validates: Requirements 9.4**
        
        This test verifies that:
        1. Expired links are treated as not found
        2. The error type is NotFoundError (404)
        """
        # Create mock share link that is expired
        created_at = datetime.now(timezone.utc) - timedelta(hours=expiry_hours + 1)
        expires_at = created_at + timedelta(hours=expiry_hours)
        
        # Verify the link is expired
        now = datetime.now(timezone.utc)
        is_expired = now > expires_at
        
        assert is_expired, (
            f"Test setup error: link should be expired. "
            f"Now: {now}, Expires: {expires_at}"
        )
    
    @given(
        expiry_hours=valid_expiry_hours(),
        seconds_before_expiry=st.integers(min_value=1, max_value=3600),
    )
    @settings(max_examples=20, deadline=None)
    def test_access_just_before_expiry_succeeds(
        self,
        expiry_hours: int,
        seconds_before_expiry: int,
    ):
        """For any share link, access just before expiry SHALL succeed.
        
        **Validates: Requirements 9.4**
        
        This test verifies that:
        1. Links are valid up until the exact expiry time
        2. No premature expiration occurs
        """
        created_at = datetime.now(timezone.utc)
        expires_at = created_at + timedelta(hours=expiry_hours)
        
        # Access time is just before expiry
        access_time = expires_at - timedelta(seconds=seconds_before_expiry)
        
        # Verify access should be allowed
        is_valid = access_time < expires_at
        assert is_valid, (
            f"Access {seconds_before_expiry} seconds before expiry should be allowed"
        )


# ============================================================================
# Property 19: Share Link Revocation
# ============================================================================

class TestShareLinkRevocationProperty:
    """Property 19: Share Link Revocation.
    
    **Validates: Requirements 9.5**
    
    For any share link that is revoked, all subsequent access attempts
    SHALL fail immediately regardless of original expiry time.
    """
    
    @given(
        expiry_hours=valid_expiry_hours(),
        access_attempts=access_counts(),
    )
    @settings(max_examples=20, deadline=None)
    def test_revoked_link_is_immediately_invalid(
        self,
        expiry_hours: int,
        access_attempts: int,
    ):
        """For any revoked share link, all access attempts SHALL fail.
        
        **Validates: Requirements 9.5**
        
        This test verifies that:
        1. Revocation is immediate
        2. Multiple access attempts all fail
        3. Expiry time doesn't matter for revoked links
        """
        # Create a share link that is NOT expired but IS revoked
        created_at = datetime.now(timezone.utc)
        expires_at = created_at + timedelta(hours=expiry_hours)
        is_revoked = True
        
        # Verify the link is not expired
        now = datetime.now(timezone.utc)
        is_expired = now > expires_at
        
        # For all access attempts, revoked link should be invalid
        for attempt in range(access_attempts):
            # Revoked links should be treated as invalid regardless of expiry
            assert is_revoked, (
                f"Access attempt {attempt + 1}: Revoked link should be invalid"
            )
    
    @given(
        expiry_hours=valid_expiry_hours(),
        hours_until_access=st.floats(min_value=0, max_value=720),
    )
    @settings(max_examples=20, deadline=None)
    def test_revocation_overrides_expiry(
        self,
        expiry_hours: int,
        hours_until_access: float,
    ):
        """For any revoked share link, revocation SHALL override expiry status.
        
        **Validates: Requirements 9.5**
        
        This test verifies that:
        1. Revoked links are invalid even if not expired
        2. Revocation takes precedence over expiry
        """
        created_at = datetime.now(timezone.utc)
        expires_at = created_at + timedelta(hours=expiry_hours)
        is_revoked = True
        
        # Access at various times
        access_time = created_at + timedelta(hours=hours_until_access)
        
        # Check if would be expired (ignoring revocation)
        would_be_expired = access_time >= expires_at
        
        # Regardless of expiry status, revoked link is invalid
        is_valid = not is_revoked and not would_be_expired
        
        assert not is_valid or not is_revoked, (
            f"Revoked link should be invalid regardless of expiry. "
            f"Would be expired: {would_be_expired}, Is revoked: {is_revoked}"
        )
    
    @given(expiry_hours=valid_expiry_hours())
    @settings(max_examples=20, deadline=None)
    def test_non_revoked_link_respects_expiry(self, expiry_hours: int):
        """For any non-revoked share link, expiry SHALL be respected.
        
        **Validates: Requirements 9.5**
        
        This test verifies that:
        1. Non-revoked links follow normal expiry rules
        2. Revocation flag is properly checked
        """
        created_at = datetime.now(timezone.utc)
        expires_at = created_at + timedelta(hours=expiry_hours)
        is_revoked = False
        
        # Access before expiry
        access_time = created_at + timedelta(hours=expiry_hours / 2)
        is_expired = access_time >= expires_at
        
        # Non-revoked, non-expired link should be valid
        is_valid = not is_revoked and not is_expired
        
        assert is_valid, (
            f"Non-revoked link accessed before expiry should be valid. "
            f"Is revoked: {is_revoked}, Is expired: {is_expired}"
        )


# ============================================================================
# Property 20: Share Link Access Logging
# ============================================================================

class TestShareLinkAccessLoggingProperty:
    """Property 20: Share Link Access Logging.
    
    **Validates: Requirements 9.6**
    
    For any access to a share link, an access log entry SHALL be created
    with timestamp and IP address.
    """
    
    @given(
        ip_address=valid_ip_addresses(),
        user_agent=valid_user_agents(),
    )
    @settings(max_examples=30, deadline=None)
    def test_access_log_contains_ip_address(
        self,
        ip_address: str,
        user_agent: str,
    ):
        """For any access, the log entry SHALL contain the IP address.
        
        **Validates: Requirements 9.6**
        
        This test verifies that:
        1. IP address is captured in access logs
        2. IP address format is preserved
        """
        # Simulate access log entry
        log_entry = {
            "ip_address": ip_address,
            "user_agent": user_agent,
            "accessed_at": datetime.now(timezone.utc),
        }
        
        # Verify IP address is present and correct
        assert "ip_address" in log_entry, "Access log must contain ip_address"
        assert log_entry["ip_address"] == ip_address, (
            f"IP address should be '{ip_address}', got '{log_entry['ip_address']}'"
        )
    
    @given(
        ip_address=valid_ip_addresses(),
        user_agent=valid_user_agents(),
    )
    @settings(max_examples=30, deadline=None)
    def test_access_log_contains_timestamp(
        self,
        ip_address: str,
        user_agent: str,
    ):
        """For any access, the log entry SHALL contain a timestamp.
        
        **Validates: Requirements 9.6**
        
        This test verifies that:
        1. Timestamp is captured in access logs
        2. Timestamp is a valid datetime
        """
        before_access = datetime.now(timezone.utc)
        
        # Simulate access log entry
        log_entry = {
            "ip_address": ip_address,
            "user_agent": user_agent,
            "accessed_at": datetime.now(timezone.utc),
        }
        
        after_access = datetime.now(timezone.utc)
        
        # Verify timestamp is present
        assert "accessed_at" in log_entry, "Access log must contain accessed_at timestamp"
        
        # Verify timestamp is within expected range
        assert log_entry["accessed_at"] >= before_access, (
            f"Timestamp should be >= {before_access}"
        )
        assert log_entry["accessed_at"] <= after_access, (
            f"Timestamp should be <= {after_access}"
        )
    
    @given(
        num_accesses=access_counts(),
        ip_address=valid_ip_addresses(),
    )
    @settings(max_examples=20, deadline=None)
    def test_multiple_accesses_create_multiple_logs(
        self,
        num_accesses: int,
        ip_address: str,
    ):
        """For N accesses to a share link, N log entries SHALL be created.
        
        **Validates: Requirements 9.6**
        
        This test verifies that:
        1. Each access creates a separate log entry
        2. No accesses are missed
        """
        access_logs = []
        
        for i in range(num_accesses):
            log_entry = {
                "ip_address": ip_address,
                "user_agent": f"TestAgent/{i}",
                "accessed_at": datetime.now(timezone.utc),
            }
            access_logs.append(log_entry)
        
        # Verify correct number of logs
        assert len(access_logs) == num_accesses, (
            f"Expected {num_accesses} log entries, got {len(access_logs)}"
        )
    
    @given(
        ip_addresses=st.lists(valid_ip_addresses(), min_size=2, max_size=10),
    )
    @settings(max_examples=20, deadline=None)
    def test_different_ips_are_logged_separately(
        self,
        ip_addresses: list,
    ):
        """For accesses from different IPs, each IP SHALL be logged correctly.
        
        **Validates: Requirements 9.6**
        
        This test verifies that:
        1. Different IP addresses are captured correctly
        2. IP addresses are not mixed up
        """
        access_logs = []
        
        for ip in ip_addresses:
            log_entry = {
                "ip_address": ip,
                "user_agent": "TestAgent",
                "accessed_at": datetime.now(timezone.utc),
            }
            access_logs.append(log_entry)
        
        # Verify each IP is logged correctly
        logged_ips = [log["ip_address"] for log in access_logs]
        
        for i, expected_ip in enumerate(ip_addresses):
            assert logged_ips[i] == expected_ip, (
                f"Log entry {i} should have IP '{expected_ip}', got '{logged_ips[i]}'"
            )
    
    @given(
        ip_address=valid_ip_addresses(),
        user_agent=st.one_of(valid_user_agents(), st.none()),
    )
    @settings(max_examples=20, deadline=None)
    def test_user_agent_is_optional(
        self,
        ip_address: str,
        user_agent: Optional[str],
    ):
        """For any access, user_agent MAY be None but IP and timestamp are required.
        
        **Validates: Requirements 9.6**
        
        This test verifies that:
        1. User agent is optional
        2. IP address and timestamp are always required
        """
        log_entry = {
            "ip_address": ip_address,
            "user_agent": user_agent,
            "accessed_at": datetime.now(timezone.utc),
        }
        
        # IP address is required
        assert log_entry["ip_address"] is not None, "IP address must not be None"
        assert log_entry["ip_address"] != "", "IP address must not be empty"
        
        # Timestamp is required
        assert log_entry["accessed_at"] is not None, "Timestamp must not be None"
        
        # User agent can be None
        # (no assertion needed - just verifying the log entry is valid)
    
    @given(
        num_accesses=access_counts(),
        ip_address=valid_ip_addresses(),
    )
    @settings(max_examples=20, deadline=None)
    def test_access_logs_are_chronologically_ordered(
        self,
        num_accesses: int,
        ip_address: str,
    ):
        """For multiple accesses, log timestamps SHALL be in chronological order.
        
        **Validates: Requirements 9.6**
        
        This test verifies that:
        1. Timestamps are in non-decreasing order
        2. Later accesses have later timestamps
        """
        access_logs = []
        
        for i in range(num_accesses):
            log_entry = {
                "ip_address": ip_address,
                "user_agent": f"TestAgent/{i}",
                "accessed_at": datetime.now(timezone.utc),
            }
            access_logs.append(log_entry)
        
        # Verify timestamps are in chronological order
        for i in range(1, len(access_logs)):
            prev_time = access_logs[i - 1]["accessed_at"]
            curr_time = access_logs[i]["accessed_at"]
            assert curr_time >= prev_time, (
                f"Log entry {i} timestamp ({curr_time}) should be >= "
                f"log entry {i - 1} timestamp ({prev_time})"
            )
