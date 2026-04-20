"""Property-based tests for data encryption at rest.

**Validates: Requirements 36.1**

Property 44: Data Encryption at Rest
*For any* sensitive data stored in the database, the data SHALL be encrypted
using AES-256, and decryption with the correct key SHALL return the original data.

These tests use Hypothesis to verify encryption properties across a wide range
of inputs, ensuring the encryption service behaves correctly for all valid data.
"""

import base64
import pytest
from hypothesis import given, assume, settings, HealthCheck
from hypothesis import strategies as st

from app.core.encryption_service import (
    EncryptionService,
    DecryptionError,
    init_encryption_service,
)


# Custom strategies for generating test data
# Strategy for generating valid plaintext strings (including unicode)
plaintext_strategy = st.text(min_size=0, max_size=1000)

# Strategy for generating binary data
binary_data_strategy = st.binary(min_size=0, max_size=1000)

# Strategy for generating field names (alphanumeric with underscores)
field_name_strategy = st.text(
    alphabet=st.sampled_from("abcdefghijklmnopqrstuvwxyz_0123456789"),
    min_size=1,
    max_size=50,
)

# Strategy for generating user IDs
user_id_strategy = st.text(
    alphabet=st.sampled_from("abcdefghijklmnopqrstuvwxyz0123456789-"),
    min_size=1,
    max_size=36,
)

# Strategy for generating JSON-serializable data
json_strategy = st.recursive(
    st.none() | st.booleans() | st.integers() | st.floats(allow_nan=False) | st.text(max_size=100),
    lambda children: st.lists(children, max_size=5) | st.dictionaries(
        st.text(min_size=1, max_size=20), children, max_size=5
    ),
    max_leaves=20,
)


def create_encryption_service() -> EncryptionService:
    """Create a fresh encryption service for testing."""
    key = EncryptionService.generate_master_key()
    return EncryptionService(key)


class TestEncryptionRoundTrip:
    """Property tests for encryption round-trip correctness.
    
    **Validates: Requirements 36.1**
    
    Property: For any plaintext, encrypting then decrypting with the same
    key and parameters SHALL return the original plaintext.
    """

    @given(plaintext=plaintext_strategy)
    def test_string_encryption_roundtrip(self, plaintext: str):
        """Any plaintext encrypted then decrypted equals the original.
        
        **Validates: Requirements 36.1**
        """
        service = create_encryption_service()
        ciphertext = service.encrypt(plaintext)
        decrypted = service.decrypt(ciphertext)
        
        assert decrypted == plaintext

    @given(plaintext=plaintext_strategy, field_name=field_name_strategy)
    def test_string_encryption_roundtrip_with_field(
        self, plaintext: str, field_name: str
    ):
        """Encryption roundtrip works with any field name.
        
        **Validates: Requirements 36.1**
        """
        service = create_encryption_service()
        ciphertext = service.encrypt(plaintext, field_name=field_name)
        decrypted = service.decrypt(ciphertext, field_name=field_name)
        
        assert decrypted == plaintext

    @given(plaintext=plaintext_strategy, user_id=user_id_strategy)
    def test_string_encryption_roundtrip_with_user(
        self, plaintext: str, user_id: str
    ):
        """Encryption roundtrip works with any user ID.
        
        **Validates: Requirements 36.1**
        """
        service = create_encryption_service()
        ciphertext = service.encrypt(plaintext, user_id=user_id)
        decrypted = service.decrypt(ciphertext, user_id=user_id)
        
        assert decrypted == plaintext

    @given(data=json_strategy)
    def test_json_encryption_roundtrip(self, data):
        """Any JSON-serializable data encrypted then decrypted equals the original.
        
        **Validates: Requirements 36.1**
        """
        service = create_encryption_service()
        ciphertext = service.encrypt_json(data)
        decrypted = service.decrypt_json(ciphertext)
        
        assert decrypted == data

    @given(data=binary_data_strategy)
    def test_bytes_encryption_roundtrip(self, data: bytes):
        """Any binary data encrypted then decrypted equals the original.
        
        **Validates: Requirements 36.1**
        """
        service = create_encryption_service()
        encrypted = service.encrypt_bytes(data)
        decrypted = service.decrypt_bytes(encrypted)
        
        assert decrypted == data


class TestCiphertextUniqueness:
    """Property tests for ciphertext uniqueness.
    
    **Validates: Requirements 36.1**
    
    Property: Different plaintexts should produce different ciphertexts,
    and same plaintext encrypted twice should produce different ciphertexts
    (due to random nonce/salt).
    """

    @given(plaintext1=plaintext_strategy, plaintext2=plaintext_strategy)
    def test_different_plaintexts_produce_different_ciphertexts(
        self, plaintext1: str, plaintext2: str
    ):
        """Different plaintexts produce different ciphertexts.
        
        **Validates: Requirements 36.1**
        """
        assume(plaintext1 != plaintext2)
        
        service = create_encryption_service()
        ciphertext1 = service.encrypt(plaintext1)
        ciphertext2 = service.encrypt(plaintext2)
        
        assert ciphertext1 != ciphertext2

    @given(plaintext=plaintext_strategy)
    def test_same_plaintext_produces_different_ciphertexts(
        self, plaintext: str
    ):
        """Same plaintext encrypted twice produces different ciphertexts (random nonce).
        
        **Validates: Requirements 36.1**
        """
        service = create_encryption_service()
        ciphertext1 = service.encrypt(plaintext)
        ciphertext2 = service.encrypt(plaintext)
        
        # Due to random nonce/salt, ciphertexts should differ
        assert ciphertext1 != ciphertext2
        
        # But both should decrypt to the same plaintext
        assert service.decrypt(ciphertext1) == plaintext
        assert service.decrypt(ciphertext2) == plaintext


class TestTamperDetection:
    """Property tests for tamper detection.
    
    **Validates: Requirements 36.1**
    
    Property: Tampering with ciphertext should cause decryption to fail
    (AES-GCM provides authenticated encryption).
    """

    @given(plaintext=st.text(min_size=1, max_size=100))
    def test_tampering_with_ciphertext_causes_failure(
        self, plaintext: str
    ):
        """Tampering with ciphertext causes decryption to fail.
        
        **Validates: Requirements 36.1**
        """
        service = create_encryption_service()
        ciphertext = service.encrypt(plaintext)
        
        # Decode, tamper, re-encode
        decoded = base64.b64decode(ciphertext)
        
        # Tamper with a byte in the middle (after version, salt, nonce)
        # The ciphertext starts at position 1 + 16 + 12 = 29
        if len(decoded) > 30:
            tamper_pos = 30
            tampered = decoded[:tamper_pos] + bytes([decoded[tamper_pos] ^ 0xFF]) + decoded[tamper_pos + 1:]
            tampered_b64 = base64.b64encode(tampered).decode('utf-8')
            
            with pytest.raises(DecryptionError):
                service.decrypt(tampered_b64)


class TestWrongKeyFailure:
    """Property tests for wrong key/field_name failure.
    
    **Validates: Requirements 36.1**
    
    Property: Decryption with wrong key or field_name should fail.
    """

    @given(plaintext=st.text(min_size=1, max_size=100), field1=field_name_strategy, field2=field_name_strategy)
    def test_wrong_field_name_causes_failure(
        self, plaintext: str, field1: str, field2: str
    ):
        """Wrong field_name causes decryption to fail.
        
        **Validates: Requirements 36.1**
        """
        assume(field1 != field2)
        
        service = create_encryption_service()
        ciphertext = service.encrypt(plaintext, field_name=field1)
        
        with pytest.raises(DecryptionError):
            service.decrypt(ciphertext, field_name=field2)

    @given(plaintext=st.text(min_size=1, max_size=100), user1=user_id_strategy, user2=user_id_strategy)
    def test_wrong_user_id_causes_failure(
        self, plaintext: str, user1: str, user2: str
    ):
        """Wrong user_id causes decryption to fail.
        
        **Validates: Requirements 36.1**
        """
        assume(user1 != user2)
        
        service = create_encryption_service()
        ciphertext = service.encrypt(plaintext, user_id=user1)
        
        with pytest.raises(DecryptionError):
            service.decrypt(ciphertext, user_id=user2)

    @given(plaintext=st.text(min_size=1, max_size=100))
    def test_different_master_key_causes_failure(self, plaintext: str):
        """Different master key causes decryption to fail.
        
        **Validates: Requirements 36.1**
        """
        service1 = EncryptionService(EncryptionService.generate_master_key())
        service2 = EncryptionService(EncryptionService.generate_master_key())
        
        ciphertext = service1.encrypt(plaintext)
        
        with pytest.raises(DecryptionError):
            service2.decrypt(ciphertext)


class TestKeyDerivationConsistency:
    """Property tests for key derivation consistency.
    
    **Validates: Requirements 36.1**
    
    Property: Key derivation should produce consistent keys for same inputs.
    """

    @given(field_name=field_name_strategy, user_id=st.one_of(st.none(), user_id_strategy))
    def test_key_derivation_is_deterministic(
        self, field_name: str, user_id
    ):
        """Key derivation produces consistent keys for same inputs.
        
        **Validates: Requirements 36.1**
        """
        service = create_encryption_service()
        
        # Clear cache to ensure fresh derivation
        service.clear_key_cache()
        
        key1 = service.derive_field_key(field_name, user_id)
        
        # Clear cache again
        service.clear_key_cache()
        
        key2 = service.derive_field_key(field_name, user_id)
        
        assert key1 == key2

    @given(field1=field_name_strategy, field2=field_name_strategy)
    def test_different_fields_derive_different_keys(
        self, field1: str, field2: str
    ):
        """Different field names derive different keys.
        
        **Validates: Requirements 36.1**
        """
        assume(field1 != field2)
        
        service = create_encryption_service()
        key1 = service.derive_field_key(field1)
        key2 = service.derive_field_key(field2)
        
        assert key1 != key2

    @given(field_name=field_name_strategy, user1=user_id_strategy, user2=user_id_strategy)
    def test_different_users_derive_different_keys(
        self, field_name: str, user1: str, user2: str
    ):
        """Different user IDs derive different keys for same field.
        
        **Validates: Requirements 36.1**
        """
        assume(user1 != user2)
        
        service = create_encryption_service()
        key1 = service.derive_field_key(field_name, user1)
        key2 = service.derive_field_key(field_name, user2)
        
        assert key1 != key2


class TestCrossInstanceCompatibility:
    """Property tests for cross-instance encryption compatibility.
    
    **Validates: Requirements 36.1**
    
    Property: Two encryption service instances with the same master key
    should be able to decrypt each other's ciphertexts.
    """

    @given(plaintext=plaintext_strategy)
    def test_same_key_cross_instance_compatibility(self, plaintext: str):
        """Two services with same key can decrypt each other's data.
        
        **Validates: Requirements 36.1**
        """
        master_key = EncryptionService.generate_master_key()
        
        service1 = EncryptionService(master_key)
        service2 = EncryptionService(master_key)
        
        # Encrypt with service1, decrypt with service2
        ciphertext = service1.encrypt(plaintext)
        decrypted = service2.decrypt(ciphertext)
        
        assert decrypted == plaintext

    @given(plaintext=plaintext_strategy, field_name=field_name_strategy)
    def test_same_key_cross_instance_with_field(self, plaintext: str, field_name: str):
        """Cross-instance compatibility works with field names.
        
        **Validates: Requirements 36.1**
        """
        master_key = EncryptionService.generate_master_key()
        
        service1 = EncryptionService(master_key)
        service2 = EncryptionService(master_key)
        
        ciphertext = service1.encrypt(plaintext, field_name=field_name)
        decrypted = service2.decrypt(ciphertext, field_name=field_name)
        
        assert decrypted == plaintext
