"""File encryption utilities using AES-256.

Implements encryption for stored files as per Requirements 6.4 and 36.1.
Uses AES-256-GCM for authenticated encryption with automatic key management.
"""

import base64
import logging
import os
import secrets
from typing import Tuple

from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

logger = logging.getLogger(__name__)

# AES-256 key size in bytes (256 bits = 32 bytes)
AES_KEY_SIZE = 32
# GCM nonce size in bytes (96 bits = 12 bytes, recommended for GCM)
GCM_NONCE_SIZE = 12


def generate_encryption_key() -> str:
    """Generate a new AES-256 encryption key.
    
    Returns:
        Base64-encoded encryption key string.
    """
    key = secrets.token_bytes(AES_KEY_SIZE)
    return base64.b64encode(key).decode("utf-8")


def _decode_key(key_b64: str) -> bytes:
    """Decode a base64-encoded key to bytes.
    
    Args:
        key_b64: Base64-encoded key string.
        
    Returns:
        Raw key bytes.
        
    Raises:
        ValueError: If the key is invalid or wrong size.
    """
    try:
        key = base64.b64decode(key_b64)
        if len(key) != AES_KEY_SIZE:
            raise ValueError(
                f"Invalid key size: expected {AES_KEY_SIZE} bytes, got {len(key)}"
            )
        return key
    except Exception as e:
        logger.error(f"Failed to decode encryption key: {e}")
        raise ValueError("Invalid encryption key format") from e


def encrypt_data(data: bytes, key_b64: str) -> Tuple[bytes, str]:
    """Encrypt data using AES-256-GCM.
    
    Args:
        data: Raw bytes to encrypt.
        key_b64: Base64-encoded AES-256 key.
        
    Returns:
        Tuple of (encrypted_data, nonce_b64) where nonce_b64 is base64-encoded.
        
    Raises:
        ValueError: If the key is invalid.
        Exception: If encryption fails.
    """
    key = _decode_key(key_b64)
    
    # Generate a random nonce for this encryption
    nonce = os.urandom(GCM_NONCE_SIZE)
    
    # Create AESGCM cipher and encrypt
    aesgcm = AESGCM(key)
    encrypted_data = aesgcm.encrypt(nonce, data, None)
    
    # Return encrypted data and base64-encoded nonce
    nonce_b64 = base64.b64encode(nonce).decode("utf-8")
    
    logger.debug(f"Encrypted {len(data)} bytes of data")
    return encrypted_data, nonce_b64


def decrypt_data(encrypted_data: bytes, key_b64: str, nonce_b64: str) -> bytes:
    """Decrypt data using AES-256-GCM.
    
    Args:
        encrypted_data: Encrypted bytes.
        key_b64: Base64-encoded AES-256 key.
        nonce_b64: Base64-encoded nonce used during encryption.
        
    Returns:
        Decrypted raw bytes.
        
    Raises:
        ValueError: If the key or nonce is invalid.
        Exception: If decryption fails (e.g., authentication failure).
    """
    key = _decode_key(key_b64)
    
    try:
        nonce = base64.b64decode(nonce_b64)
        if len(nonce) != GCM_NONCE_SIZE:
            raise ValueError(
                f"Invalid nonce size: expected {GCM_NONCE_SIZE} bytes, got {len(nonce)}"
            )
    except Exception as e:
        logger.error(f"Failed to decode nonce: {e}")
        raise ValueError("Invalid nonce format") from e
    
    # Create AESGCM cipher and decrypt
    aesgcm = AESGCM(key)
    decrypted_data = aesgcm.decrypt(nonce, encrypted_data, None)
    
    logger.debug(f"Decrypted {len(decrypted_data)} bytes of data")
    return decrypted_data


def encrypt_file(file_data: bytes, key_b64: str | None = None) -> Tuple[bytes, str, str]:
    """Encrypt file data with optional key generation.
    
    Convenience function that generates a key if not provided.
    
    Args:
        file_data: Raw file bytes to encrypt.
        key_b64: Optional base64-encoded key. If None, a new key is generated.
        
    Returns:
        Tuple of (encrypted_data, key_b64, nonce_b64).
    """
    if key_b64 is None:
        key_b64 = generate_encryption_key()
    
    encrypted_data, nonce_b64 = encrypt_data(file_data, key_b64)
    return encrypted_data, key_b64, nonce_b64


def decrypt_file(encrypted_data: bytes, key_b64: str, nonce_b64: str) -> bytes:
    """Decrypt file data.
    
    Convenience wrapper around decrypt_data for file operations.
    
    Args:
        encrypted_data: Encrypted file bytes.
        key_b64: Base64-encoded AES-256 key.
        nonce_b64: Base64-encoded nonce.
        
    Returns:
        Decrypted file bytes.
    """
    return decrypt_data(encrypted_data, key_b64, nonce_b64)
