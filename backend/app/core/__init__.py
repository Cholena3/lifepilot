# Core module - configuration, security, and shared utilities

from app.core.cache import (
    cache_key,
    cached,
    delete_cached,
    delete_pattern,
    get_cached,
    set_cached,
)
from app.core.config import Settings, get_settings
from app.core.encryption import (
    decrypt_data,
    decrypt_file,
    encrypt_data,
    encrypt_file,
    generate_encryption_key,
)
from app.core.encryption_service import (
    DecryptionError,
    EncryptionError,
    EncryptionService,
    KeyDerivationError,
    get_encryption_service,
    init_encryption_service,
)
from app.core.encrypted_types import (
    EncryptedBytes,
    EncryptedJSON,
    EncryptedString,
    EncryptedText,
    UserEncryptedString,
)
from app.core.redis import close_redis, get_redis, init_redis
from app.core.storage import (
    close_storage,
    delete_file,
    download_file,
    file_exists,
    get_file_metadata,
    init_storage,
    upload_file,
)

__all__ = [
    # Config
    "Settings",
    "get_settings",
    # Redis
    "init_redis",
    "close_redis",
    "get_redis",
    # Cache utilities
    "get_cached",
    "set_cached",
    "delete_cached",
    "delete_pattern",
    "cache_key",
    "cached",
    # File encryption utilities (for files/documents)
    "generate_encryption_key",
    "encrypt_data",
    "decrypt_data",
    "encrypt_file",
    "decrypt_file",
    # Data encryption at rest service (for database fields)
    "EncryptionService",
    "EncryptionError",
    "DecryptionError",
    "KeyDerivationError",
    "get_encryption_service",
    "init_encryption_service",
    # SQLAlchemy encrypted field types
    "EncryptedString",
    "EncryptedText",
    "EncryptedJSON",
    "EncryptedBytes",
    "UserEncryptedString",
    # Storage utilities
    "init_storage",
    "close_storage",
    "upload_file",
    "download_file",
    "delete_file",
    "file_exists",
    "get_file_metadata",
]
