"""Tests for S3/R2 storage utilities.

These tests use mocking to avoid requiring actual S3 credentials.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from botocore.exceptions import ClientError

from app.core import storage


@pytest.fixture
def mock_s3_client():
    """Create a mock S3 client."""
    with patch.object(storage, "_s3_client", None):
        with patch.object(storage, "_executor", None):
            mock_client = MagicMock()
            with patch.object(storage, "_create_s3_client", return_value=mock_client):
                yield mock_client


@pytest.fixture
def mock_settings():
    """Mock settings for tests."""
    with patch("app.core.storage.get_settings") as mock:
        settings = MagicMock()
        settings.s3_bucket_name = "test-bucket"
        settings.s3_region = "us-east-1"
        settings.s3_access_key = "test-key"
        settings.s3_secret_key = "test-secret"
        settings.s3_endpoint_url = None
        mock.return_value = settings
        yield settings


class TestGetS3Client:
    """Tests for get_s3_client function."""

    def test_creates_client_on_first_call(self, mock_s3_client, mock_settings):
        """Should create client on first call."""
        client = storage.get_s3_client()
        assert client is mock_s3_client

    def test_returns_same_client_on_subsequent_calls(self, mock_s3_client, mock_settings):
        """Should return cached client on subsequent calls."""
        client1 = storage.get_s3_client()
        client2 = storage.get_s3_client()
        assert client1 is client2


class TestUploadFile:
    """Tests for upload_file function."""

    @pytest.mark.asyncio
    async def test_upload_file_success(self, mock_s3_client, mock_settings):
        """Should upload file successfully."""
        mock_s3_client.put_object.return_value = {}
        
        result = await storage.upload_file(
            file_data=b"test content",
            key="test/file.txt",
            content_type="text/plain",
        )
        
        assert result == "test/file.txt"
        mock_s3_client.put_object.assert_called_once()
        call_kwargs = mock_s3_client.put_object.call_args[1]
        assert call_kwargs["Bucket"] == "test-bucket"
        assert call_kwargs["Key"] == "test/file.txt"
        assert call_kwargs["Body"] == b"test content"
        assert call_kwargs["ContentType"] == "text/plain"
        assert call_kwargs["ServerSideEncryption"] == "AES256"

    @pytest.mark.asyncio
    async def test_upload_file_with_metadata(self, mock_s3_client, mock_settings):
        """Should include metadata in upload."""
        mock_s3_client.put_object.return_value = {}
        
        await storage.upload_file(
            file_data=b"test",
            key="test.txt",
            metadata={"user_id": "123", "category": "documents"},
        )
        
        call_kwargs = mock_s3_client.put_object.call_args[1]
        assert call_kwargs["Metadata"] == {"user_id": "123", "category": "documents"}

    @pytest.mark.asyncio
    async def test_upload_file_error(self, mock_s3_client, mock_settings):
        """Should raise exception on upload error."""
        mock_s3_client.put_object.side_effect = ClientError(
            {"Error": {"Code": "AccessDenied", "Message": "Access Denied"}},
            "PutObject",
        )
        
        with pytest.raises(ClientError):
            await storage.upload_file(b"test", "test.txt")


class TestDownloadFile:
    """Tests for download_file function."""

    @pytest.mark.asyncio
    async def test_download_file_success(self, mock_s3_client, mock_settings):
        """Should download file successfully."""
        mock_body = MagicMock()
        mock_body.read.return_value = b"file content"
        mock_s3_client.get_object.return_value = {"Body": mock_body}
        
        result = await storage.download_file("test/file.txt")
        
        assert result == b"file content"
        mock_s3_client.get_object.assert_called_once_with(
            Bucket="test-bucket",
            Key="test/file.txt",
        )

    @pytest.mark.asyncio
    async def test_download_file_not_found(self, mock_s3_client, mock_settings):
        """Should raise FileNotFoundError when file doesn't exist."""
        mock_s3_client.get_object.side_effect = ClientError(
            {"Error": {"Code": "NoSuchKey", "Message": "Not Found"}},
            "GetObject",
        )
        
        with pytest.raises(FileNotFoundError, match="File not found"):
            await storage.download_file("nonexistent.txt")


class TestDeleteFile:
    """Tests for delete_file function."""

    @pytest.mark.asyncio
    async def test_delete_file_success(self, mock_s3_client, mock_settings):
        """Should delete file successfully."""
        mock_s3_client.delete_object.return_value = {}
        
        result = await storage.delete_file("test/file.txt")
        
        assert result is True
        mock_s3_client.delete_object.assert_called_once_with(
            Bucket="test-bucket",
            Key="test/file.txt",
        )

    @pytest.mark.asyncio
    async def test_delete_file_error(self, mock_s3_client, mock_settings):
        """Should raise exception on delete error."""
        mock_s3_client.delete_object.side_effect = ClientError(
            {"Error": {"Code": "AccessDenied", "Message": "Access Denied"}},
            "DeleteObject",
        )
        
        with pytest.raises(ClientError):
            await storage.delete_file("test.txt")


class TestGeneratePresignedUrl:
    """Tests for generate_presigned_url function."""

    @pytest.mark.asyncio
    async def test_generate_presigned_url_success(self, mock_s3_client, mock_settings):
        """Should generate presigned URL successfully."""
        mock_s3_client.generate_presigned_url.return_value = "https://example.com/presigned"
        
        result = await storage.generate_presigned_url("test/file.txt", expiry_seconds=3600)
        
        assert result == "https://example.com/presigned"
        mock_s3_client.generate_presigned_url.assert_called_once_with(
            ClientMethod="get_object",
            Params={"Bucket": "test-bucket", "Key": "test/file.txt"},
            ExpiresIn=3600,
        )

    @pytest.mark.asyncio
    async def test_generate_presigned_url_for_upload(self, mock_s3_client, mock_settings):
        """Should generate presigned URL for PUT method."""
        mock_s3_client.generate_presigned_url.return_value = "https://example.com/upload"
        
        result = await storage.generate_presigned_url(
            "test/file.txt",
            http_method="PUT",
        )
        
        assert result == "https://example.com/upload"
        mock_s3_client.generate_presigned_url.assert_called_once_with(
            ClientMethod="put_object",
            Params={"Bucket": "test-bucket", "Key": "test/file.txt"},
            ExpiresIn=3600,
        )


class TestFileExists:
    """Tests for file_exists function."""

    @pytest.mark.asyncio
    async def test_file_exists_true(self, mock_s3_client, mock_settings):
        """Should return True when file exists."""
        mock_s3_client.head_object.return_value = {}
        
        result = await storage.file_exists("test/file.txt")
        
        assert result is True

    @pytest.mark.asyncio
    async def test_file_exists_false(self, mock_s3_client, mock_settings):
        """Should return False when file doesn't exist."""
        mock_s3_client.head_object.side_effect = ClientError(
            {"Error": {"Code": "404", "Message": "Not Found"}},
            "HeadObject",
        )
        
        result = await storage.file_exists("nonexistent.txt")
        
        assert result is False


class TestGetFileMetadata:
    """Tests for get_file_metadata function."""

    @pytest.mark.asyncio
    async def test_get_file_metadata_success(self, mock_s3_client, mock_settings):
        """Should return file metadata."""
        from datetime import datetime
        
        mock_s3_client.head_object.return_value = {
            "ContentType": "text/plain",
            "ContentLength": 1024,
            "LastModified": datetime(2024, 1, 1),
            "ETag": '"abc123"',
            "Metadata": {"user_id": "123"},
        }
        
        result = await storage.get_file_metadata("test/file.txt")
        
        assert result["content_type"] == "text/plain"
        assert result["size"] == 1024
        assert result["etag"] == '"abc123"'
        assert result["metadata"] == {"user_id": "123"}

    @pytest.mark.asyncio
    async def test_get_file_metadata_not_found(self, mock_s3_client, mock_settings):
        """Should raise FileNotFoundError when file doesn't exist."""
        mock_s3_client.head_object.side_effect = ClientError(
            {"Error": {"Code": "404", "Message": "Not Found"}},
            "HeadObject",
        )
        
        with pytest.raises(FileNotFoundError, match="File not found"):
            await storage.get_file_metadata("nonexistent.txt")
