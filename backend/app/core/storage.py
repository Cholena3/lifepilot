"""Local filesystem storage for file operations.

Stores files on the local disk under a configurable directory.
Drop-in replacement for the S3 storage module.
"""

import logging
import os
import shutil
from pathlib import Path
from typing import Optional

from app.core.config import get_settings

logger = logging.getLogger(__name__)

# Base upload directory (resolved at init time)
_storage_dir: Optional[Path] = None


def _get_storage_dir() -> Path:
    """Get the resolved storage directory, creating it if needed."""
    global _storage_dir
    if _storage_dir is None:
        settings = get_settings()
        _storage_dir = Path(settings.storage_dir).resolve()
        _storage_dir.mkdir(parents=True, exist_ok=True)
    return _storage_dir


async def init_storage() -> None:
    """Ensure the local storage directory exists."""
    d = _get_storage_dir()
    logger.info(f"Local storage directory: {d}")


async def close_storage() -> None:
    """No-op for local storage."""
    pass


def _resolve_path(key: str) -> Path:
    """Resolve a storage key to an absolute file path."""
    return _get_storage_dir() / key


async def upload_file(
    file_data: bytes,
    key: str,
    content_type: str = "application/octet-stream",
    metadata: Optional[dict] = None,
) -> str:
    """Write file bytes to local disk.

    Returns the key (relative path) of the stored file.
    """
    dest = _resolve_path(key)
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(file_data)
    logger.info(f"Stored file locally: {key} ({len(file_data)} bytes)")
    return key


async def download_file(key: str) -> bytes:
    """Read file bytes from local disk.

    Raises FileNotFoundError if the file does not exist.
    """
    path = _resolve_path(key)
    if not path.is_file():
        raise FileNotFoundError(f"File not found: {key}")
    data = path.read_bytes()
    logger.info(f"Read file from disk: {key} ({len(data)} bytes)")
    return data


async def delete_file(key: str) -> bool:
    """Delete a file from local disk."""
    path = _resolve_path(key)
    if path.is_file():
        path.unlink()
        logger.info(f"Deleted file: {key}")
        return True
    logger.warning(f"File not found for deletion: {key}")
    return False


async def file_exists(key: str) -> bool:
    """Check whether a file exists on disk."""
    return _resolve_path(key).is_file()


async def get_file_metadata(key: str) -> dict:
    """Return basic metadata for a stored file."""
    path = _resolve_path(key)
    if not path.is_file():
        raise FileNotFoundError(f"File not found: {key}")
    stat = path.stat()
    return {
        "size": stat.st_size,
        "last_modified": stat.st_mtime,
    }


async def generate_presigned_url(
    key: str,
    expiry_seconds: int = 3600,
    http_method: str = "GET",
) -> str:
    """Return a local download path (no real presigning for local storage)."""
    return f"/api/v1/files/{key}"
