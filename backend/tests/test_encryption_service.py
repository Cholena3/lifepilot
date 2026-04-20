"""Tests for the data encryption at rest service.

Tests the EncryptionService and SQLAlchemy encrypted field types.

Validates: Requirements 36.1
"""

import base64
import json
import pytest
import secrets

from app.core.encryption_service import (
    AES_KEY_SIZE,
    DecryptionError,
    EncryptionError,
    EncryptionService,
    KeyDerivationError,
    get_encryption_service,
    init_encryption_service,
)


class TestEncryptionServiceInit:
    """Tests for EncryptionService initialization."""

    def test_init_with_base64_key(self):
        """Should initialize with a valid base64-encoded 32-byte key."""
        key = base64.b64encode(secrets.token_bytes(32)).decode()
        service = EncryptionService(key)
        assert service is not None

    def test_init_with_passphrase(self):
        """Should initialize with a passphrase and derive key."""
        passphrase = "my-secure-passphrase-for-testing"
        service = EncryptionService(passphrase)
        assert service is not None

    def test_init_with_short_key_derives(self):
        """Should derive key from short input."""
        short_key = "short"
        service = EncryptionService(short_key)
        assert service is not None

    def test_generate_master_key(self):
        """Should generate a valid master key."""
        key = EncryptionService.generate_master_key()
        decoded = base64.b64decode(key)
        assert len(decoded) == AES_KEY_SIZE


class TestEncryptionServiceEncryptDecrypt:
    """Tests for encrypt/decrypt operations."""

    @pytest.fixture
    def service(self):
        """Create an encryption service for testing."""
        key = EncryptionService.generate_master_key()
        return EncryptionService(key)

    def test_encrypt_decrypt_string_roundtrip(self, service):
        """Encrypted string should decrypt to original."""
        plaintext = "Hello, World! This is sensitive data."
        
        ciphertext = service.encrypt(plaintext)
        decrypted = service.decrypt(ciphertext)
        
        assert decrypted == plaintext

    def test_encrypt_decrypt_with_field_name(self, service):
        """Should work with field-specific encryption."""
        plaintext = "Sensitive medical data"
        field_name = "health_notes"
        
        ciphertext = service.encrypt(plaintext, field_name=field_name)
        decrypted = service.decrypt(ciphertext, field_name=field_name)
        
        assert decrypted == plaintext

    def test_encrypt_decrypt_with_user_id(self, service):
        """Should work with user-specific encryption."""
        plaintext = "User-specific data"
        user_id = "user-123"
        
        ciphertext = service.encrypt(plaintext, user_id=user_id)
        decrypted = service.decrypt(ciphertext, user_id=user_id)
        
        assert decrypted == plaintext

    def test_encrypt_produces_different_output(self, service):
        """Same plaintext should produce different ciphertext each time."""
        plaintext = "Same data"
        
        ciphertext1 = service.encrypt(plaintext)
        ciphertext2 = service.encrypt(plaintext)
        
        assert ciphertext1 != ciphertext2

    def test_ciphertext_is_base64(self, service):
        """Ciphertext should be valid base64."""
        plaintext = "Test data"
        ciphertext = service.encrypt(plaintext)
        
        # Should not raise
        decoded = base64.b64decode(ciphertext)
        assert len(decoded) > 0

    def test_decrypt_with_wrong_field_name_fails(self, service):
        """Decryption with wrong field name should fail."""
        plaintext = "Test data"
        
        ciphertext = service.encrypt(plaintext, field_name="field1")
        
        with pytest.raises(DecryptionError):
            service.decrypt(ciphertext, field_name="field2")

    def test_decrypt_with_wrong_user_id_fails(self, service):
        """Decryption with wrong user ID should fail."""
        plaintext = "Test data"
        
        ciphertext = service.encrypt(plaintext, user_id="user1")
        
        with pytest.raises(DecryptionError):
            service.decrypt(ciphertext, user_id="user2")

    def test_decrypt_tampered_data_fails(self, service):
        """Decryption of tampered data should fail."""
        plaintext = "Test data"
        ciphertext = service.encrypt(plaintext)
        
        # Tamper with the ciphertext
        decoded = base64.b64decode(ciphertext)
        tampered = bytes([decoded[0] ^ 0xFF]) + decoded[1:]
        tampered_b64 = base64.b64encode(tampered).decode()
        
        with pytest.raises(DecryptionError):
            service.decrypt(tampered_b64)

    def test_decrypt_invalid_base64_fails(self, service):
        """Decryption of invalid base64 should fail."""
        with pytest.raises(DecryptionError):
            service.decrypt("not-valid-base64!!!")

    def test_encrypt_empty_string(self, service):
        """Should handle empty string."""
        plaintext = ""
        
        ciphertext = service.encrypt(plaintext)
        decrypted = service.decrypt(ciphertext)
        
        assert decrypted == plaintext

    def test_encrypt_unicode_string(self, service):
        """Should handle unicode characters."""
        plaintext = "Hello 世界! 🔐 Émojis and spëcial çharacters"
        
        ciphertext = service.encrypt(plaintext)
        decrypted = service.decrypt(ciphertext)
        
        assert decrypted == plaintext

    def test_encrypt_large_string(self, service):
        """Should handle large strings."""
        plaintext = "x" * (1024 * 100)  # 100KB
        
        ciphertext = service.encrypt(plaintext)
        decrypted = service.decrypt(ciphertext)
        
        assert decrypted == plaintext

    def test_encrypt_bytes(self, service):
        """Should handle bytes input that is UTF-8 decodable."""
        plaintext = b"Binary data that is UTF-8 safe"
        
        ciphertext = service.encrypt(plaintext)
        decrypted = service.decrypt(ciphertext)
        
        assert decrypted == plaintext.decode('utf-8')


class TestEncryptionServiceJSON:
    """Tests for JSON encryption/decryption."""

    @pytest.fixture
    def service(self):
        """Create an encryption service for testing."""
        key = EncryptionService.generate_master_key()
        return EncryptionService(key)

    def test_encrypt_decrypt_json_dict(self, service):
        """Should encrypt/decrypt JSON dict."""
        data = {"name": "John", "age": 30, "active": True}
        
        ciphertext = service.encrypt_json(data)
        decrypted = service.decrypt_json(ciphertext)
        
        assert decrypted == data

    def test_encrypt_decrypt_json_list(self, service):
        """Should encrypt/decrypt JSON list."""
        data = ["item1", "item2", {"nested": "value"}]
        
        ciphertext = service.encrypt_json(data)
        decrypted = service.decrypt_json(ciphertext)
        
        assert decrypted == data

    def test_encrypt_decrypt_json_nested(self, service):
        """Should encrypt/decrypt nested JSON."""
        data = {
            "user": {
                "profile": {
                    "name": "John",
                    "contacts": [
                        {"type": "email", "value": "john@example.com"},
                        {"type": "phone", "value": "+1234567890"},
                    ]
                }
            }
        }
        
        ciphertext = service.encrypt_json(data)
        decrypted = service.decrypt_json(ciphertext)
        
        assert decrypted == data

    def test_encrypt_decrypt_json_with_field_name(self, service):
        """Should work with field-specific JSON encryption."""
        data = {"allergies": ["peanuts", "shellfish"]}
        field_name = "emergency_allergies"
        
        ciphertext = service.encrypt_json(data, field_name=field_name)
        decrypted = service.decrypt_json(ciphertext, field_name=field_name)
        
        assert decrypted == data


class TestEncryptionServiceBytes:
    """Tests for binary data encryption/decryption."""

    @pytest.fixture
    def service(self):
        """Create an encryption service for testing."""
        key = EncryptionService.generate_master_key()
        return EncryptionService(key)

    def test_encrypt_decrypt_bytes_roundtrip(self, service):
        """Should encrypt/decrypt binary data."""
        data = b"\x00\x01\x02\x03\xff\xfe\xfd"
        
        encrypted = service.encrypt_bytes(data)
        decrypted = service.decrypt_bytes(encrypted)
        
        assert decrypted == data

    def test_encrypt_bytes_produces_bytes(self, service):
        """encrypt_bytes should return bytes."""
        data = b"test"
        encrypted = service.encrypt_bytes(data)
        assert isinstance(encrypted, bytes)


class TestEncryptionServiceKeyRotation:
    """Tests for key rotation functionality."""

    @pytest.fixture
    def service(self):
        """Create an encryption service for testing."""
        key = EncryptionService.generate_master_key()
        return EncryptionService(key)

    def test_rotate_key(self, service):
        """Should re-encrypt data with new key parameters."""
        plaintext = "Sensitive data"
        old_field = "old_field"
        new_field = "new_field"
        
        # Encrypt with old field
        old_ciphertext = service.encrypt(plaintext, field_name=old_field)
        
        # Rotate to new field
        new_ciphertext = service.rotate_key(
            old_ciphertext,
            old_field_name=old_field,
            new_field_name=new_field,
        )
        
        # Should decrypt with new field
        decrypted = service.decrypt(new_ciphertext, field_name=new_field)
        assert decrypted == plaintext
        
        # Old ciphertext should still work with old field
        old_decrypted = service.decrypt(old_ciphertext, field_name=old_field)
        assert old_decrypted == plaintext

    def test_rotate_key_with_user_id(self, service):
        """Should re-encrypt with different user IDs."""
        plaintext = "User data"
        
        old_ciphertext = service.encrypt(plaintext, user_id="user1")
        
        new_ciphertext = service.rotate_key(
            old_ciphertext,
            old_field_name="default",
            new_field_name="default",
            old_user_id="user1",
            new_user_id="user2",
        )
        
        decrypted = service.decrypt(new_ciphertext, user_id="user2")
        assert decrypted == plaintext

    def test_clear_key_cache(self, service):
        """Should clear the key cache."""
        # Generate some cached keys
        service.derive_field_key("field1")
        service.derive_field_key("field2")
        
        # Clear cache
        service.clear_key_cache()
        
        # Cache should be empty (internal check)
        assert len(service._key_cache) == 0


class TestEncryptionServiceFieldKeyDerivation:
    """Tests for field-specific key derivation."""

    @pytest.fixture
    def service(self):
        """Create an encryption service for testing."""
        key = EncryptionService.generate_master_key()
        return EncryptionService(key)

    def test_different_fields_have_different_keys(self, service):
        """Different field names should derive different keys."""
        key1 = service.derive_field_key("field1")
        key2 = service.derive_field_key("field2")
        
        assert key1 != key2

    def test_same_field_returns_cached_key(self, service):
        """Same field name should return cached key."""
        key1 = service.derive_field_key("field1")
        key2 = service.derive_field_key("field1")
        
        assert key1 == key2

    def test_user_specific_keys_are_different(self, service):
        """Different user IDs should derive different keys."""
        key1 = service.derive_field_key("field", user_id="user1")
        key2 = service.derive_field_key("field", user_id="user2")
        
        assert key1 != key2


class TestEncryptionServiceCrossInstance:
    """Tests for encryption across service instances."""

    def test_same_key_produces_compatible_encryption(self):
        """Two services with same key should be compatible."""
        master_key = EncryptionService.generate_master_key()
        
        service1 = EncryptionService(master_key)
        service2 = EncryptionService(master_key)
        
        plaintext = "Test data"
        ciphertext = service1.encrypt(plaintext)
        decrypted = service2.decrypt(ciphertext)
        
        assert decrypted == plaintext

    def test_different_keys_are_incompatible(self):
        """Two services with different keys should be incompatible."""
        service1 = EncryptionService(EncryptionService.generate_master_key())
        service2 = EncryptionService(EncryptionService.generate_master_key())
        
        plaintext = "Test data"
        ciphertext = service1.encrypt(plaintext)
        
        with pytest.raises(DecryptionError):
            service2.decrypt(ciphertext)


class TestGlobalEncryptionService:
    """Tests for global encryption service management."""

    def test_init_and_get_encryption_service(self):
        """Should initialize and retrieve global service."""
        # Reset global service first
        import app.core.encryption_service as enc_module
        enc_module._encryption_service = None
        
        key = EncryptionService.generate_master_key()
        
        service = init_encryption_service(key)
        retrieved = get_encryption_service()
        
        assert service is retrieved

    def test_get_encryption_service_uses_config(self, monkeypatch):
        """Should use config settings when not initialized."""
        # Reset global service
        import app.core.encryption_service as enc_module
        enc_module._encryption_service = None
        
        # Mock the get_settings function in the config module
        class MockSettings:
            encryption_master_key = EncryptionService.generate_master_key()
        
        monkeypatch.setattr(
            "app.core.config.get_settings",
            lambda: MockSettings()
        )
        
        service = get_encryption_service()
        assert service is not None
