"""SQLAlchemy TypeDecorators for encrypted database fields.

Provides transparent encryption/decryption for sensitive data stored in
database columns. Uses AES-256-GCM encryption via the EncryptionService.

Validates: Requirements 36.1

Usage:
    from app.core.encrypted_types import EncryptedString, EncryptedJSON

    class User(Base):
        # Encrypted string field
        ssn = Column(EncryptedString(field_name="user_ssn"), nullable=True)
        
        # Encrypted JSON field
        sensitive_data = Column(EncryptedJSON(field_name="user_data"), nullable=True)
"""

import json
import logging
from typing import Any, Optional, Type, TypeVar

from sqlalchemy import String, Text, TypeDecorator
from sqlalchemy.dialects.postgresql import JSONB

logger = logging.getLogger(__name__)

T = TypeVar('T')


class EncryptedString(TypeDecorator):
    """SQLAlchemy TypeDecorator for encrypted string fields.
    
    Automatically encrypts data before storing and decrypts when retrieving.
    Uses AES-256-GCM encryption with field-specific key derivation.
    
    Validates: Requirements 36.1
    
    Attributes:
        impl: The underlying SQLAlchemy type (Text for storing encrypted data).
        cache_ok: Whether this type is safe to cache.
        
    Example:
        class HealthRecord(Base):
            # Encrypt sensitive medical notes
            medical_notes = Column(
                EncryptedString(field_name="health_medical_notes"),
                nullable=True
            )
    """
    
    impl = Text
    cache_ok = True
    
    def __init__(
        self,
        field_name: str = "default",
        length: Optional[int] = None,
        *args,
        **kwargs
    ):
        """Initialize the encrypted string type.
        
        Args:
            field_name: Unique name for key derivation. Use descriptive names
                       like "user_ssn" or "health_notes" for different fields.
            length: Optional maximum length (not enforced for encrypted data).
            *args: Additional positional arguments for TypeDecorator.
            **kwargs: Additional keyword arguments for TypeDecorator.
        """
        self.field_name = field_name
        self._length = length
        super().__init__(*args, **kwargs)
    
    def process_bind_param(self, value: Optional[str], dialect) -> Optional[str]:
        """Encrypt the value before storing in the database.
        
        Args:
            value: The plaintext string value to encrypt.
            dialect: The SQLAlchemy dialect.
            
        Returns:
            The encrypted value as a base64 string, or None if value is None.
        """
        if value is None:
            return None
        
        try:
            from app.core.encryption_service import get_encryption_service
            service = get_encryption_service()
            return service.encrypt(value, self.field_name)
        except Exception as e:
            logger.error(f"Failed to encrypt field {self.field_name}: {e}")
            raise
    
    def process_result_value(self, value: Optional[str], dialect) -> Optional[str]:
        """Decrypt the value when retrieving from the database.
        
        Args:
            value: The encrypted base64 string from the database.
            dialect: The SQLAlchemy dialect.
            
        Returns:
            The decrypted plaintext string, or None if value is None.
        """
        if value is None:
            return None
        
        try:
            from app.core.encryption_service import get_encryption_service
            service = get_encryption_service()
            return service.decrypt(value, self.field_name)
        except Exception as e:
            logger.error(f"Failed to decrypt field {self.field_name}: {e}")
            raise


class EncryptedText(EncryptedString):
    """Alias for EncryptedString for semantic clarity with large text fields.
    
    Use this for fields that store large amounts of text like medical notes,
    personal descriptions, etc.
    
    Validates: Requirements 36.1
    """
    pass


class EncryptedJSON(TypeDecorator):
    """SQLAlchemy TypeDecorator for encrypted JSON fields.
    
    Automatically encrypts JSON data before storing and decrypts when retrieving.
    Supports any JSON-serializable Python object (dict, list, etc.).
    
    Validates: Requirements 36.1
    
    Example:
        class EmergencyInfo(Base):
            # Encrypt sensitive emergency contact data
            emergency_contacts = Column(
                EncryptedJSON(field_name="emergency_contacts"),
                nullable=True
            )
    """
    
    impl = Text
    cache_ok = True
    
    def __init__(self, field_name: str = "default", *args, **kwargs):
        """Initialize the encrypted JSON type.
        
        Args:
            field_name: Unique name for key derivation.
            *args: Additional positional arguments for TypeDecorator.
            **kwargs: Additional keyword arguments for TypeDecorator.
        """
        self.field_name = field_name
        super().__init__(*args, **kwargs)
    
    def process_bind_param(self, value: Optional[Any], dialect) -> Optional[str]:
        """Encrypt the JSON value before storing in the database.
        
        Args:
            value: The JSON-serializable value to encrypt.
            dialect: The SQLAlchemy dialect.
            
        Returns:
            The encrypted value as a base64 string, or None if value is None.
        """
        if value is None:
            return None
        
        try:
            from app.core.encryption_service import get_encryption_service
            service = get_encryption_service()
            return service.encrypt_json(value, self.field_name)
        except Exception as e:
            logger.error(f"Failed to encrypt JSON field {self.field_name}: {e}")
            raise
    
    def process_result_value(self, value: Optional[str], dialect) -> Optional[Any]:
        """Decrypt the JSON value when retrieving from the database.
        
        Args:
            value: The encrypted base64 string from the database.
            dialect: The SQLAlchemy dialect.
            
        Returns:
            The decrypted JSON data, or None if value is None.
        """
        if value is None:
            return None
        
        try:
            from app.core.encryption_service import get_encryption_service
            service = get_encryption_service()
            return service.decrypt_json(value, self.field_name)
        except Exception as e:
            logger.error(f"Failed to decrypt JSON field {self.field_name}: {e}")
            raise


class EncryptedBytes(TypeDecorator):
    """SQLAlchemy TypeDecorator for encrypted binary fields.
    
    Automatically encrypts binary data before storing and decrypts when retrieving.
    Stores the encrypted data as base64-encoded text.
    
    Validates: Requirements 36.1
    
    Example:
        class Document(Base):
            # Encrypt sensitive binary content
            encrypted_content = Column(
                EncryptedBytes(field_name="document_content"),
                nullable=True
            )
    """
    
    impl = Text
    cache_ok = True
    
    def __init__(self, field_name: str = "default", *args, **kwargs):
        """Initialize the encrypted bytes type.
        
        Args:
            field_name: Unique name for key derivation.
            *args: Additional positional arguments for TypeDecorator.
            **kwargs: Additional keyword arguments for TypeDecorator.
        """
        self.field_name = field_name
        super().__init__(*args, **kwargs)
    
    def process_bind_param(self, value: Optional[bytes], dialect) -> Optional[str]:
        """Encrypt the binary value before storing in the database.
        
        Args:
            value: The binary data to encrypt.
            dialect: The SQLAlchemy dialect.
            
        Returns:
            The encrypted value as a base64 string, or None if value is None.
        """
        if value is None:
            return None
        
        try:
            from app.core.encryption_service import get_encryption_service
            import base64
            service = get_encryption_service()
            encrypted = service.encrypt_bytes(value, self.field_name)
            return base64.b64encode(encrypted).decode('utf-8')
        except Exception as e:
            logger.error(f"Failed to encrypt bytes field {self.field_name}: {e}")
            raise
    
    def process_result_value(self, value: Optional[str], dialect) -> Optional[bytes]:
        """Decrypt the binary value when retrieving from the database.
        
        Args:
            value: The encrypted base64 string from the database.
            dialect: The SQLAlchemy dialect.
            
        Returns:
            The decrypted binary data, or None if value is None.
        """
        if value is None:
            return None
        
        try:
            from app.core.encryption_service import get_encryption_service
            import base64
            service = get_encryption_service()
            encrypted = base64.b64decode(value)
            return service.decrypt_bytes(encrypted, self.field_name)
        except Exception as e:
            logger.error(f"Failed to decrypt bytes field {self.field_name}: {e}")
            raise


class UserEncryptedString(TypeDecorator):
    """SQLAlchemy TypeDecorator for user-specific encrypted string fields.
    
    Similar to EncryptedString but derives a unique key per user.
    Requires the model to have a user_id attribute.
    
    Note: This type requires special handling in queries since the encryption
    key depends on the user_id. Use with caution and ensure user_id is always
    available when accessing these fields.
    
    Validates: Requirements 36.1
    """
    
    impl = Text
    cache_ok = False  # Not cacheable due to user-specific keys
    
    def __init__(self, field_name: str = "default", *args, **kwargs):
        """Initialize the user-encrypted string type.
        
        Args:
            field_name: Unique name for key derivation.
            *args: Additional positional arguments for TypeDecorator.
            **kwargs: Additional keyword arguments for TypeDecorator.
        """
        self.field_name = field_name
        super().__init__(*args, **kwargs)
    
    def process_bind_param(self, value: Optional[str], dialect) -> Optional[str]:
        """Encrypt the value before storing in the database.
        
        Note: For user-specific encryption, the user_id must be passed
        through the execution context or handled at the service layer.
        This implementation falls back to field-level encryption.
        
        Args:
            value: The plaintext string value to encrypt.
            dialect: The SQLAlchemy dialect.
            
        Returns:
            The encrypted value as a base64 string, or None if value is None.
        """
        if value is None:
            return None
        
        try:
            from app.core.encryption_service import get_encryption_service
            service = get_encryption_service()
            # Note: User-specific encryption should be handled at service layer
            # where user_id is available. This provides field-level encryption.
            return service.encrypt(value, self.field_name)
        except Exception as e:
            logger.error(f"Failed to encrypt user field {self.field_name}: {e}")
            raise
    
    def process_result_value(self, value: Optional[str], dialect) -> Optional[str]:
        """Decrypt the value when retrieving from the database.
        
        Args:
            value: The encrypted base64 string from the database.
            dialect: The SQLAlchemy dialect.
            
        Returns:
            The decrypted plaintext string, or None if value is None.
        """
        if value is None:
            return None
        
        try:
            from app.core.encryption_service import get_encryption_service
            service = get_encryption_service()
            return service.decrypt(value, self.field_name)
        except Exception as e:
            logger.error(f"Failed to decrypt user field {self.field_name}: {e}")
            raise
