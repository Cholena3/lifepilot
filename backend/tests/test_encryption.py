"""Tests for encryption utilities."""

import pytest

from app.core.encryption import (
    AES_KEY_SIZE,
    GCM_NONCE_SIZE,
    decrypt_data,
    decrypt_file,
    encrypt_data,
    encrypt_file,
    generate_encryption_key,
)
import base64


class TestGenerateEncryptionKey:
    """Tests for generate_encryption_key function."""

    def test_generates_valid_base64_key(self):
        """Key should be valid base64."""
        key = generate_encryption_key()
        # Should not raise
        decoded = base64.b64decode(key)
        assert len(decoded) == AES_KEY_SIZE

    def test_generates_unique_keys(self):
        """Each call should generate a unique key."""
        keys = [generate_encryption_key() for _ in range(10)]
        assert len(set(keys)) == 10


class TestEncryptDecryptData:
    """Tests for encrypt_data and decrypt_data functions."""

    def test_encrypt_decrypt_roundtrip(self):
        """Encrypted data should decrypt to original."""
        key = generate_encryption_key()
        original_data = b"Hello, World! This is test data."
        
        encrypted, nonce = encrypt_data(original_data, key)
        decrypted = decrypt_data(encrypted, key, nonce)
        
        assert decrypted == original_data

    def test_encrypt_produces_different_output(self):
        """Encryption should produce different ciphertext each time (due to random nonce)."""
        key = generate_encryption_key()
        data = b"Same data"
        
        encrypted1, nonce1 = encrypt_data(data, key)
        encrypted2, nonce2 = encrypt_data(data, key)
        
        # Nonces should be different
        assert nonce1 != nonce2
        # Ciphertext should be different
        assert encrypted1 != encrypted2

    def test_encrypted_data_is_different_from_original(self):
        """Encrypted data should not match original."""
        key = generate_encryption_key()
        data = b"Secret message"
        
        encrypted, _ = encrypt_data(data, key)
        
        assert encrypted != data

    def test_decrypt_with_wrong_key_fails(self):
        """Decryption with wrong key should fail."""
        key1 = generate_encryption_key()
        key2 = generate_encryption_key()
        data = b"Test data"
        
        encrypted, nonce = encrypt_data(data, key1)
        
        with pytest.raises(Exception):
            decrypt_data(encrypted, key2, nonce)

    def test_decrypt_with_wrong_nonce_fails(self):
        """Decryption with wrong nonce should fail."""
        key = generate_encryption_key()
        data = b"Test data"
        
        encrypted, _ = encrypt_data(data, key)
        _, wrong_nonce = encrypt_data(b"other", key)
        
        with pytest.raises(Exception):
            decrypt_data(encrypted, key, wrong_nonce)

    def test_decrypt_tampered_data_fails(self):
        """Decryption of tampered data should fail (GCM authentication)."""
        key = generate_encryption_key()
        data = b"Test data"
        
        encrypted, nonce = encrypt_data(data, key)
        
        # Tamper with the encrypted data
        tampered = bytes([encrypted[0] ^ 0xFF]) + encrypted[1:]
        
        with pytest.raises(Exception):
            decrypt_data(tampered, key, nonce)

    def test_encrypt_empty_data(self):
        """Should handle empty data."""
        key = generate_encryption_key()
        data = b""
        
        encrypted, nonce = encrypt_data(data, key)
        decrypted = decrypt_data(encrypted, key, nonce)
        
        assert decrypted == data

    def test_encrypt_large_data(self):
        """Should handle large data."""
        key = generate_encryption_key()
        data = b"x" * (1024 * 1024)  # 1MB
        
        encrypted, nonce = encrypt_data(data, key)
        decrypted = decrypt_data(encrypted, key, nonce)
        
        assert decrypted == data

    def test_invalid_key_format_raises_error(self):
        """Invalid key format should raise ValueError."""
        with pytest.raises(ValueError, match="Invalid encryption key"):
            encrypt_data(b"data", "not-valid-base64!!!")

    def test_invalid_key_size_raises_error(self):
        """Wrong key size should raise ValueError."""
        short_key = base64.b64encode(b"short").decode()
        with pytest.raises(ValueError, match="Invalid encryption key"):
            encrypt_data(b"data", short_key)

    def test_invalid_nonce_format_raises_error(self):
        """Invalid nonce format should raise ValueError."""
        key = generate_encryption_key()
        encrypted, _ = encrypt_data(b"data", key)
        
        with pytest.raises(ValueError, match="Invalid nonce"):
            decrypt_data(encrypted, key, "not-valid-base64!!!")


class TestEncryptDecryptFile:
    """Tests for encrypt_file and decrypt_file convenience functions."""

    def test_encrypt_file_generates_key_if_not_provided(self):
        """encrypt_file should generate a key if none provided."""
        data = b"File content"
        
        encrypted, key, nonce = encrypt_file(data)
        
        assert key is not None
        assert len(base64.b64decode(key)) == AES_KEY_SIZE
        assert nonce is not None

    def test_encrypt_file_uses_provided_key(self):
        """encrypt_file should use provided key."""
        data = b"File content"
        provided_key = generate_encryption_key()
        
        encrypted, returned_key, nonce = encrypt_file(data, provided_key)
        
        assert returned_key == provided_key

    def test_encrypt_decrypt_file_roundtrip(self):
        """File encryption/decryption roundtrip should work."""
        data = b"File content with binary data: \x00\x01\x02\xff"
        
        encrypted, key, nonce = encrypt_file(data)
        decrypted = decrypt_file(encrypted, key, nonce)
        
        assert decrypted == data
