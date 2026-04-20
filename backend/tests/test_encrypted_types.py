"""Tests for SQLAlchemy encrypted field types.

Tests the EncryptedString, EncryptedJSON, and EncryptedBytes TypeDecorators.

Validates: Requirements 36.1
"""

import pytest
from unittest.mock import MagicMock, patch

from app.core.encrypted_types import (
    EncryptedString,
    EncryptedText,
    EncryptedJSON,
    EncryptedBytes,
    UserEncryptedString,
)
from app.core.encryption_service import (
    EncryptionService,
    init_encryption_service,
)


@pytest.fixture(autouse=True)
def setup_encryption_service():
    """Initialize encryption service for all tests."""
    key = EncryptionService.generate_master_key()
    init_encryption_service(key)
    yield


class TestEncryptedString:
    """Tests for EncryptedString TypeDecorator."""

    def test_process_bind_param_encrypts(self):
        """Should encrypt value when binding to database."""
        field = EncryptedString(field_name="test_field")
        
        plaintext = "sensitive data"
        encrypted = field.process_bind_param(plaintext, None)
        
        assert encrypted is not None
        assert encrypted != plaintext
        # Should be base64 encoded
        import base64
        base64.b64decode(encrypted)  # Should not raise

    def test_process_bind_param_none(self):
        """Should return None for None value."""
        field = EncryptedString(field_name="test_field")
        
        result = field.process_bind_param(None, None)
        
        assert result is None

    def test_process_result_value_decrypts(self):
        """Should decrypt value when retrieving from database."""
        field = EncryptedString(field_name="test_field")
        
        plaintext = "sensitive data"
        encrypted = field.process_bind_param(plaintext, None)
        decrypted = field.process_result_value(encrypted, None)
        
        assert decrypted == plaintext

    def test_process_result_value_none(self):
        """Should return None for None value."""
        field = EncryptedString(field_name="test_field")
        
        result = field.process_result_value(None, None)
        
        assert result is None

    def test_roundtrip_with_unicode(self):
        """Should handle unicode characters."""
        field = EncryptedString(field_name="test_field")
        
        plaintext = "Hello 世界! 🔐 Émojis"
        encrypted = field.process_bind_param(plaintext, None)
        decrypted = field.process_result_value(encrypted, None)
        
        assert decrypted == plaintext

    def test_different_field_names_produce_different_ciphertext(self):
        """Different field names should produce different encryption."""
        field1 = EncryptedString(field_name="field1")
        field2 = EncryptedString(field_name="field2")
        
        plaintext = "same data"
        encrypted1 = field1.process_bind_param(plaintext, None)
        encrypted2 = field2.process_bind_param(plaintext, None)
        
        # Different field names = different keys = different ciphertext
        # (though both should decrypt to same plaintext with correct field)
        assert encrypted1 != encrypted2

    def test_cache_ok_is_true(self):
        """EncryptedString should be cacheable."""
        field = EncryptedString(field_name="test_field")
        assert field.cache_ok is True


class TestEncryptedText:
    """Tests for EncryptedText TypeDecorator (alias for EncryptedString)."""

    def test_is_alias_for_encrypted_string(self):
        """EncryptedText should be a subclass of EncryptedString."""
        assert issubclass(EncryptedText, EncryptedString)

    def test_roundtrip_large_text(self):
        """Should handle large text content."""
        field = EncryptedText(field_name="notes_field")
        
        plaintext = "x" * 10000  # 10KB of text
        encrypted = field.process_bind_param(plaintext, None)
        decrypted = field.process_result_value(encrypted, None)
        
        assert decrypted == plaintext


class TestEncryptedJSON:
    """Tests for EncryptedJSON TypeDecorator."""

    def test_process_bind_param_encrypts_dict(self):
        """Should encrypt dict value when binding to database."""
        field = EncryptedJSON(field_name="json_field")
        
        data = {"name": "John", "age": 30}
        encrypted = field.process_bind_param(data, None)
        
        assert encrypted is not None
        assert isinstance(encrypted, str)

    def test_process_bind_param_none(self):
        """Should return None for None value."""
        field = EncryptedJSON(field_name="json_field")
        
        result = field.process_bind_param(None, None)
        
        assert result is None

    def test_process_result_value_decrypts_dict(self):
        """Should decrypt to original dict."""
        field = EncryptedJSON(field_name="json_field")
        
        data = {"name": "John", "age": 30, "active": True}
        encrypted = field.process_bind_param(data, None)
        decrypted = field.process_result_value(encrypted, None)
        
        assert decrypted == data

    def test_process_result_value_none(self):
        """Should return None for None value."""
        field = EncryptedJSON(field_name="json_field")
        
        result = field.process_result_value(None, None)
        
        assert result is None

    def test_roundtrip_list(self):
        """Should handle list values."""
        field = EncryptedJSON(field_name="json_field")
        
        data = ["item1", "item2", {"nested": "value"}]
        encrypted = field.process_bind_param(data, None)
        decrypted = field.process_result_value(encrypted, None)
        
        assert decrypted == data

    def test_roundtrip_nested_structure(self):
        """Should handle deeply nested structures."""
        field = EncryptedJSON(field_name="json_field")
        
        data = {
            "user": {
                "profile": {
                    "contacts": [
                        {"type": "email", "value": "test@example.com"},
                        {"type": "phone", "value": "+1234567890"},
                    ]
                }
            }
        }
        encrypted = field.process_bind_param(data, None)
        decrypted = field.process_result_value(encrypted, None)
        
        assert decrypted == data

    def test_cache_ok_is_true(self):
        """EncryptedJSON should be cacheable."""
        field = EncryptedJSON(field_name="json_field")
        assert field.cache_ok is True


class TestEncryptedBytes:
    """Tests for EncryptedBytes TypeDecorator."""

    def test_process_bind_param_encrypts(self):
        """Should encrypt bytes value when binding to database."""
        field = EncryptedBytes(field_name="bytes_field")
        
        data = b"\x00\x01\x02\x03\xff\xfe"
        encrypted = field.process_bind_param(data, None)
        
        assert encrypted is not None
        assert isinstance(encrypted, str)

    def test_process_bind_param_none(self):
        """Should return None for None value."""
        field = EncryptedBytes(field_name="bytes_field")
        
        result = field.process_bind_param(None, None)
        
        assert result is None

    def test_process_result_value_decrypts(self):
        """Should decrypt to original bytes."""
        field = EncryptedBytes(field_name="bytes_field")
        
        data = b"\x00\x01\x02\x03\xff\xfe"
        encrypted = field.process_bind_param(data, None)
        decrypted = field.process_result_value(encrypted, None)
        
        assert decrypted == data

    def test_process_result_value_none(self):
        """Should return None for None value."""
        field = EncryptedBytes(field_name="bytes_field")
        
        result = field.process_result_value(None, None)
        
        assert result is None

    def test_cache_ok_is_true(self):
        """EncryptedBytes should be cacheable."""
        field = EncryptedBytes(field_name="bytes_field")
        assert field.cache_ok is True


class TestUserEncryptedString:
    """Tests for UserEncryptedString TypeDecorator."""

    def test_process_bind_param_encrypts(self):
        """Should encrypt value when binding to database."""
        field = UserEncryptedString(field_name="user_field")
        
        plaintext = "user-specific data"
        encrypted = field.process_bind_param(plaintext, None)
        
        assert encrypted is not None
        assert encrypted != plaintext

    def test_process_bind_param_none(self):
        """Should return None for None value."""
        field = UserEncryptedString(field_name="user_field")
        
        result = field.process_bind_param(None, None)
        
        assert result is None

    def test_process_result_value_decrypts(self):
        """Should decrypt value when retrieving from database."""
        field = UserEncryptedString(field_name="user_field")
        
        plaintext = "user-specific data"
        encrypted = field.process_bind_param(plaintext, None)
        decrypted = field.process_result_value(encrypted, None)
        
        assert decrypted == plaintext

    def test_cache_ok_is_false(self):
        """UserEncryptedString should not be cacheable due to user-specific keys."""
        field = UserEncryptedString(field_name="user_field")
        assert field.cache_ok is False


class TestEncryptedTypesIntegration:
    """Integration tests for encrypted types working together."""

    def test_multiple_fields_same_model(self):
        """Multiple encrypted fields should work independently."""
        string_field = EncryptedString(field_name="string_field")
        json_field = EncryptedJSON(field_name="json_field")
        
        string_data = "sensitive string"
        json_data = {"key": "value"}
        
        # Encrypt both
        encrypted_string = string_field.process_bind_param(string_data, None)
        encrypted_json = json_field.process_bind_param(json_data, None)
        
        # Decrypt both
        decrypted_string = string_field.process_result_value(encrypted_string, None)
        decrypted_json = json_field.process_result_value(encrypted_json, None)
        
        assert decrypted_string == string_data
        assert decrypted_json == json_data

    def test_cross_field_decryption_fails(self):
        """Decrypting with wrong field should fail."""
        field1 = EncryptedString(field_name="field1")
        field2 = EncryptedString(field_name="field2")
        
        plaintext = "test data"
        encrypted = field1.process_bind_param(plaintext, None)
        
        # Trying to decrypt with different field should fail
        with pytest.raises(Exception):
            field2.process_result_value(encrypted, None)
