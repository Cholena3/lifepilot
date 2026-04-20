"""S3/R2 storage client for file storage operations.

Implements file storage utilities as per Requirements 6.4 and 36.1.
Supports AWS S3, Cloudflare R2, and MinIO with server-side encryption.
Uses boto3 with run_in_executor for async compatibility.
"""

import asyncio
import logging
from concurrent.futures import ThreadPoolExecutor
from functools import partial
from typing import Optional

import boto3
from botocore.config import Config
from botocore.exceptions import ClientError

from app.core.config import get_settings

logger = logging.getLogger(__name__)

# Thread pool for running sync boto3 operations
_executor: Optional[ThreadPoolExecutor] = None
_s3_client = None


def _get_executor() -> ThreadPoolExecutor:
    """Get or create the thread pool executor."""
    global _executor
    if _executor is None:
        _executor = ThreadPoolExecutor(max_workers=4, thread_name_prefix="s3-")
    return _executor


def _create_s3_client():
    """Create a boto3 S3 client with configured settings."""
    settings = get_settings()
    
    # Configure boto3 client
    config = Config(
        retries={"max_attempts": 3, "mode": "adaptive"},
        connect_timeout=5,
        read_timeout=30,
    )
    
    client_kwargs = {
        "service_name": "s3",
        "region_name": settings.s3_region,
        "config": config,
    }
    
    # Add credentials if provided
    if settings.s3_access_key and settings.s3_secret_key:
        client_kwargs["aws_access_key_id"] = settings.s3_access_key
        client_kwargs["aws_secret_access_key"] = settings.s3_secret_key
    
    # Add custom endpoint URL for R2 or MinIO
    if settings.s3_endpoint_url:
        client_kwargs["endpoint_url"] = settings.s3_endpoint_url
    
    return boto3.client(**client_kwargs)


def get_s3_client():
    """Get or create the S3 client instance."""
    global _s3_client
    if _s3_client is None:
        _s3_client = _create_s3_client()
        logger.info("S3 client initialized")
    return _s3_client


async def init_storage() -> None:
    """Initialize the storage client and verify connectivity."""
    settings = get_settings()
    client = get_s3_client()
    
    # Verify bucket exists or can be accessed
    try:
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(
            _get_executor(),
            partial(client.head_bucket, Bucket=settings.s3_bucket_name),
        )
        logger.info(f"S3 bucket '{settings.s3_bucket_name}' is accessible")
    except ClientError as e:
        error_code = e.response.get("Error", {}).get("Code", "")
        if error_code == "404":
            logger.warning(
                f"S3 bucket '{settings.s3_bucket_name}' does not exist. "
                "It will be created on first upload if permissions allow."
            )
        elif error_code == "403":
            logger.warning(
                f"Access denied to S3 bucket '{settings.s3_bucket_name}'. "
                "Check credentials and permissions."
            )
        else:
            logger.error(f"Error checking S3 bucket: {e}")


async def close_storage() -> None:
    """Close the storage client and clean up resources."""
    global _s3_client, _executor
    
    if _executor is not None:
        _executor.shutdown(wait=True)
        _executor = None
        logger.info("S3 thread pool executor closed")
    
    _s3_client = None
    logger.info("S3 client closed")


async def upload_file(
    file_data: bytes,
    key: str,
    content_type: str = "application/octet-stream",
    metadata: Optional[dict] = None,
) -> str:
    """Upload a file to S3/R2 storage with server-side encryption.
    
    Args:
        file_data: Raw file bytes to upload.
        key: The S3 object key (path) for the file.
        content_type: MIME type of the file.
        metadata: Optional metadata dict to store with the file.
        
    Returns:
        The S3 object key of the uploaded file.
        
    Raises:
        Exception: If upload fails.
    """
    settings = get_settings()
    client = get_s3_client()
    
    put_kwargs = {
        "Bucket": settings.s3_bucket_name,
        "Key": key,
        "Body": file_data,
        "ContentType": content_type,
        # Server-side encryption with AES-256
        "ServerSideEncryption": "AES256",
    }
    
    if metadata:
        put_kwargs["Metadata"] = {k: str(v) for k, v in metadata.items()}
    
    try:
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(
            _get_executor(),
            partial(client.put_object, **put_kwargs),
        )
        logger.info(f"Uploaded file to S3: {key} ({len(file_data)} bytes)")
        return key
    except ClientError as e:
        logger.error(f"Failed to upload file to S3: {key} - {e}")
        raise


async def download_file(key: str) -> bytes:
    """Download a file from S3/R2 storage.
    
    Args:
        key: The S3 object key (path) of the file.
        
    Returns:
        The file contents as bytes.
        
    Raises:
        FileNotFoundError: If the file does not exist.
        Exception: If download fails.
    """
    settings = get_settings()
    client = get_s3_client()
    
    try:
        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(
            _get_executor(),
            partial(
                client.get_object,
                Bucket=settings.s3_bucket_name,
                Key=key,
            ),
        )
        
        # Read the body content
        body = response["Body"]
        file_data = await loop.run_in_executor(_get_executor(), body.read)
        
        logger.info(f"Downloaded file from S3: {key} ({len(file_data)} bytes)")
        return file_data
        
    except ClientError as e:
        error_code = e.response.get("Error", {}).get("Code", "")
        if error_code == "NoSuchKey":
            logger.warning(f"File not found in S3: {key}")
            raise FileNotFoundError(f"File not found: {key}") from e
        logger.error(f"Failed to download file from S3: {key} - {e}")
        raise


async def delete_file(key: str) -> bool:
    """Delete a file from S3/R2 storage.
    
    Args:
        key: The S3 object key (path) of the file.
        
    Returns:
        True if the file was deleted successfully.
        
    Raises:
        Exception: If deletion fails.
    """
    settings = get_settings()
    client = get_s3_client()
    
    try:
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(
            _get_executor(),
            partial(
                client.delete_object,
                Bucket=settings.s3_bucket_name,
                Key=key,
            ),
        )
        logger.info(f"Deleted file from S3: {key}")
        return True
        
    except ClientError as e:
        logger.error(f"Failed to delete file from S3: {key} - {e}")
        raise


async def generate_presigned_url(
    key: str,
    expiry_seconds: int = 3600,
    http_method: str = "GET",
) -> str:
    """Generate a presigned URL for temporary file access.
    
    Args:
        key: The S3 object key (path) of the file.
        expiry_seconds: URL validity period in seconds (default: 1 hour).
        http_method: HTTP method for the URL (GET for download, PUT for upload).
        
    Returns:
        The presigned URL string.
        
    Raises:
        Exception: If URL generation fails.
    """
    settings = get_settings()
    client = get_s3_client()
    
    client_method = "get_object" if http_method == "GET" else "put_object"
    
    try:
        loop = asyncio.get_event_loop()
        url = await loop.run_in_executor(
            _get_executor(),
            partial(
                client.generate_presigned_url,
                ClientMethod=client_method,
                Params={
                    "Bucket": settings.s3_bucket_name,
                    "Key": key,
                },
                ExpiresIn=expiry_seconds,
            ),
        )
        logger.debug(f"Generated presigned URL for: {key} (expires in {expiry_seconds}s)")
        return url
        
    except ClientError as e:
        logger.error(f"Failed to generate presigned URL for: {key} - {e}")
        raise


async def file_exists(key: str) -> bool:
    """Check if a file exists in S3/R2 storage.
    
    Args:
        key: The S3 object key (path) to check.
        
    Returns:
        True if the file exists, False otherwise.
    """
    settings = get_settings()
    client = get_s3_client()
    
    try:
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(
            _get_executor(),
            partial(
                client.head_object,
                Bucket=settings.s3_bucket_name,
                Key=key,
            ),
        )
        return True
        
    except ClientError as e:
        error_code = e.response.get("Error", {}).get("Code", "")
        if error_code == "404":
            return False
        logger.error(f"Error checking file existence: {key} - {e}")
        raise


async def get_file_metadata(key: str) -> dict:
    """Get metadata for a file in S3/R2 storage.
    
    Args:
        key: The S3 object key (path) of the file.
        
    Returns:
        Dict containing file metadata (content_type, size, last_modified, etc.).
        
    Raises:
        FileNotFoundError: If the file does not exist.
    """
    settings = get_settings()
    client = get_s3_client()
    
    try:
        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(
            _get_executor(),
            partial(
                client.head_object,
                Bucket=settings.s3_bucket_name,
                Key=key,
            ),
        )
        
        return {
            "content_type": response.get("ContentType"),
            "size": response.get("ContentLength"),
            "last_modified": response.get("LastModified"),
            "etag": response.get("ETag"),
            "metadata": response.get("Metadata", {}),
        }
        
    except ClientError as e:
        error_code = e.response.get("Error", {}).get("Code", "")
        if error_code == "404":
            raise FileNotFoundError(f"File not found: {key}") from e
        logger.error(f"Failed to get file metadata: {key} - {e}")
        raise
