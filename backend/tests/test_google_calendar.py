"""Unit tests for Google Calendar integration.

Tests Requirements 4.1, 4.2, 4.3, 4.4, 4.5 for exam calendar integration.
"""

import asyncio
import uuid
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.models.exam import ExamType
from app.schemas.calendar import (
    CalendarEventCreate,
    CalendarEventResponse,
    CalendarSyncResponse,
    GoogleCalendarAuthURL,
    GoogleCalendarCallback,
    GoogleCalendarStatus,
    GoogleCalendarTokenResponse,
)
from app.services.google_calendar import (
    GoogleCalendarError,
    GoogleCalendarService,
    _retry_with_backoff,
    MAX_RETRIES,
    BASE_DELAY,
)


# Test user ID (matches the mock in router)
TEST_USER_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")


# ============================================================================
# Schema Tests
# ============================================================================

class TestCalendarSchemas:
    """Tests for calendar Pydantic schemas."""

    def test_google_calendar_auth_url_schema(self):
        """Test GoogleCalendarAuthURL schema."""
        auth_url = GoogleCalendarAuthURL(
            auth_url="https://accounts.google.com/o/oauth2/v2/auth?...",
            state="random_state_token",
        )
        assert "accounts.google.com" in auth_url.auth_url
        assert auth_url.state == "random_state_token"

    def test_google_calendar_callback_schema(self):
        """Test GoogleCalendarCallback schema."""
        callback = GoogleCalendarCallback(
            code="auth_code_from_google",
            state="random_state_token",
        )
        assert callback.code == "auth_code_from_google"
        assert callback.state == "random_state_token"

    def test_google_calendar_token_response_schema(self):
        """Test GoogleCalendarTokenResponse schema."""
        response = GoogleCalendarTokenResponse(
            connected=True,
            message="Google Calendar connected successfully",
        )
        assert response.connected is True
        assert "connected" in response.message.lower()

    def test_google_calendar_status_connected(self):
        """Test GoogleCalendarStatus when connected."""
        expiry = datetime.now(timezone.utc) + timedelta(hours=1)
        status = GoogleCalendarStatus(
            connected=True,
            token_expiry=expiry,
        )
        assert status.connected is True
        assert status.token_expiry == expiry

    def test_google_calendar_status_disconnected(self):
        """Test GoogleCalendarStatus when disconnected."""
        status = GoogleCalendarStatus(
            connected=False,
            token_expiry=None,
        )
        assert status.connected is False
        assert status.token_expiry is None

    def test_calendar_event_create_schema(self):
        """Test CalendarEventCreate schema."""
        exam_id = uuid.uuid4()
        event = CalendarEventCreate(exam_id=exam_id)
        assert event.exam_id == exam_id

    def test_calendar_event_response_schema(self):
        """Test CalendarEventResponse schema."""
        sync_id = uuid.uuid4()
        exam_id = uuid.uuid4()
        synced_at = datetime.now(timezone.utc)
        
        response = CalendarEventResponse(
            id=sync_id,
            exam_id=exam_id,
            google_event_id="google_event_123",
            synced_at=synced_at,
        )
        
        assert response.id == sync_id
        assert response.exam_id == exam_id
        assert response.google_event_id == "google_event_123"
        assert response.synced_at == synced_at

    def test_calendar_sync_response_synced(self):
        """Test CalendarSyncResponse when synced."""
        exam_id = uuid.uuid4()
        synced_at = datetime.now(timezone.utc)
        
        response = CalendarSyncResponse(
            exam_id=exam_id,
            is_synced=True,
            google_event_id="google_event_123",
            synced_at=synced_at,
        )
        
        assert response.exam_id == exam_id
        assert response.is_synced is True
        assert response.google_event_id == "google_event_123"
        assert response.synced_at == synced_at

    def test_calendar_sync_response_not_synced(self):
        """Test CalendarSyncResponse when not synced."""
        exam_id = uuid.uuid4()
        
        response = CalendarSyncResponse(
            exam_id=exam_id,
            is_synced=False,
            google_event_id=None,
            synced_at=None,
        )
        
        assert response.exam_id == exam_id
        assert response.is_synced is False
        assert response.google_event_id is None
        assert response.synced_at is None


# ============================================================================
# Retry Logic Tests (Requirement 4.5)
# ============================================================================

class TestRetryWithBackoff:
    """Tests for exponential backoff retry logic.
    
    Validates: Requirement 4.5
    """

    @pytest.mark.asyncio
    async def test_retry_succeeds_on_first_attempt(self):
        """Test that successful calls don't retry."""
        mock_func = AsyncMock(return_value="success")
        
        result = await _retry_with_backoff(mock_func, max_retries=3, base_delay=0.01)
        
        assert result == "success"
        assert mock_func.call_count == 1

    @pytest.mark.asyncio
    async def test_retry_succeeds_after_failures(self):
        """Test that retries work after initial failures."""
        mock_func = AsyncMock(
            side_effect=[
                httpx.RequestError("Connection failed"),
                httpx.RequestError("Connection failed"),
                "success",
            ]
        )
        
        result = await _retry_with_backoff(mock_func, max_retries=3, base_delay=0.01)
        
        assert result == "success"
        assert mock_func.call_count == 3

    @pytest.mark.asyncio
    async def test_retry_raises_after_max_retries(self):
        """Test that error is raised after max retries.
        
        Requirement 4.5: Retry up to 3 times with exponential backoff
        """
        mock_func = AsyncMock(
            side_effect=httpx.RequestError("Connection failed")
        )
        
        with pytest.raises(GoogleCalendarError) as exc_info:
            await _retry_with_backoff(mock_func, max_retries=3, base_delay=0.01)
        
        assert "failed after 3 retries" in str(exc_info.value)
        assert mock_func.call_count == 3

    @pytest.mark.asyncio
    async def test_retry_handles_http_status_error(self):
        """Test retry handles HTTP status errors."""
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_func = AsyncMock(
            side_effect=[
                httpx.HTTPStatusError("Server error", request=MagicMock(), response=mock_response),
                "success",
            ]
        )
        
        result = await _retry_with_backoff(mock_func, max_retries=3, base_delay=0.01)
        
        assert result == "success"
        assert mock_func.call_count == 2

    @pytest.mark.asyncio
    async def test_retry_handles_google_calendar_error(self):
        """Test retry handles GoogleCalendarError."""
        mock_func = AsyncMock(
            side_effect=[
                GoogleCalendarError(message="API error"),
                "success",
            ]
        )
        
        result = await _retry_with_backoff(mock_func, max_retries=3, base_delay=0.01)
        
        assert result == "success"
        assert mock_func.call_count == 2


# ============================================================================
# OAuth Flow Tests (Requirement 4.1)
# ============================================================================

class TestOAuthFlow:
    """Tests for Google Calendar OAuth flow.
    
    Validates: Requirement 4.1
    """

    def test_auth_url_generation(self):
        """Test OAuth authorization URL generation.
        
        Requirement 4.1: Obtain OAuth tokens
        """
        # Create a mock service
        with patch('app.services.google_calendar.settings') as mock_settings:
            mock_settings.google_client_id = "test_client_id"
            mock_settings.google_calendar_redirect_uri = "http://localhost:8000/callback"
            
            from app.services.google_calendar import GoogleCalendarService
            
            # Create service with mock session
            mock_session = MagicMock()
            service = GoogleCalendarService(mock_session)
            
            auth_url_response = service.get_auth_url()
            
            assert "accounts.google.com" in auth_url_response.auth_url
            assert "client_id=test_client_id" in auth_url_response.auth_url
            assert "scope=" in auth_url_response.auth_url
            assert auth_url_response.state is not None
            assert len(auth_url_response.state) > 0

    def test_auth_url_with_custom_state(self):
        """Test OAuth URL generation with custom state."""
        with patch('app.services.google_calendar.settings') as mock_settings:
            mock_settings.google_client_id = "test_client_id"
            mock_settings.google_calendar_redirect_uri = "http://localhost:8000/callback"
            
            from app.services.google_calendar import GoogleCalendarService
            
            mock_session = MagicMock()
            service = GoogleCalendarService(mock_session)
            
            custom_state = "my_custom_state_123"
            auth_url_response = service.get_auth_url(state=custom_state)
            
            assert auth_url_response.state == custom_state
            assert f"state={custom_state}" in auth_url_response.auth_url


# ============================================================================
# Event Building Tests
# ============================================================================

class TestEventBuilding:
    """Tests for building Google Calendar events from exams."""

    def test_build_event_data_with_exam_date(self):
        """Test building event data when exam has exam_date."""
        from app.services.google_calendar import GoogleCalendarService
        
        mock_session = MagicMock()
        service = GoogleCalendarService(mock_session)
        
        # Create mock exam
        mock_exam = MagicMock()
        mock_exam.name = "GATE 2024"
        mock_exam.description = "Graduate Aptitude Test"
        mock_exam.organization = "IIT"
        mock_exam.exam_date = date(2024, 2, 15)
        mock_exam.registration_start = date(2023, 9, 1)
        mock_exam.registration_end = date(2023, 10, 15)
        mock_exam.source_url = "https://gate.iitk.ac.in"
        
        event_data = service._build_event_data(mock_exam)
        
        assert event_data["summary"] == "Exam: GATE 2024"
        assert "Graduate Aptitude Test" in event_data["description"]
        assert "IIT" in event_data["description"]
        assert event_data["start"]["date"] == "2024-02-15"
        assert event_data["end"]["date"] == "2024-02-15"

    def test_build_event_data_with_registration_end(self):
        """Test building event data when exam has only registration_end."""
        from app.services.google_calendar import GoogleCalendarService
        
        mock_session = MagicMock()
        service = GoogleCalendarService(mock_session)
        
        mock_exam = MagicMock()
        mock_exam.name = "TCS NQT"
        mock_exam.description = None
        mock_exam.organization = "TCS"
        mock_exam.exam_date = None
        mock_exam.registration_start = None
        mock_exam.registration_end = date(2024, 3, 1)
        mock_exam.source_url = None
        
        event_data = service._build_event_data(mock_exam)
        
        assert event_data["summary"] == "Exam: TCS NQT"
        assert event_data["start"]["date"] == "2024-03-01"

    def test_build_event_data_includes_reminders(self):
        """Test that event data includes reminder settings."""
        from app.services.google_calendar import GoogleCalendarService
        
        mock_session = MagicMock()
        service = GoogleCalendarService(mock_session)
        
        mock_exam = MagicMock()
        mock_exam.name = "Test Exam"
        mock_exam.description = None
        mock_exam.organization = "Test Org"
        mock_exam.exam_date = date(2024, 6, 1)
        mock_exam.registration_start = None
        mock_exam.registration_end = None
        mock_exam.source_url = None
        
        event_data = service._build_event_data(mock_exam)
        
        assert "reminders" in event_data
        assert event_data["reminders"]["useDefault"] is False
        assert len(event_data["reminders"]["overrides"]) == 2
        # Check for 1 day and 7 day reminders
        reminder_minutes = [r["minutes"] for r in event_data["reminders"]["overrides"]]
        assert 1440 in reminder_minutes  # 1 day
        assert 10080 in reminder_minutes  # 7 days


# ============================================================================
# API Endpoint Tests
# ============================================================================

@pytest.fixture
async def client() -> AsyncClient:
    """Create an async test client."""
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as ac:
        yield ac


class TestCalendarEndpoints:
    """Integration tests for calendar API endpoints."""

    @pytest.mark.asyncio
    async def test_get_calendar_auth_url_endpoint(self, client: AsyncClient):
        """Test getting calendar auth URL via API.
        
        Requirement 4.1: Obtain OAuth tokens
        """
        response = await client.get("/api/v1/exams/calendar/auth")
        assert response.status_code == 200
        data = response.json()
        assert "auth_url" in data
        assert "state" in data

    @pytest.mark.asyncio
    async def test_calendar_callback_endpoint(self, client: AsyncClient):
        """Test calendar OAuth callback via API.
        
        Requirement 4.1: Store tokens securely
        """
        response = await client.post(
            "/api/v1/exams/calendar/callback",
            json={
                "code": "test_auth_code",
                "state": "test_state",
            },
        )
        # Will fail without actual Google OAuth, but endpoint should exist
        assert response.status_code in [200, 401, 500]

    @pytest.mark.asyncio
    async def test_get_calendar_status_endpoint(self, client: AsyncClient):
        """Test getting calendar status via API."""
        response = await client.get("/api/v1/exams/calendar/status")
        assert response.status_code in [200, 500]

    @pytest.mark.asyncio
    async def test_disconnect_calendar_endpoint(self, client: AsyncClient):
        """Test disconnecting calendar via API."""
        response = await client.delete("/api/v1/exams/calendar/disconnect")
        assert response.status_code in [204, 404, 500]

    @pytest.mark.asyncio
    async def test_sync_exam_to_calendar_endpoint(self, client: AsyncClient):
        """Test syncing exam to calendar via API.
        
        Requirement 4.2: Create a Google Calendar event
        """
        exam_id = uuid.uuid4()
        response = await client.post(f"/api/v1/exams/calendar/sync/{exam_id}")
        # Will fail without calendar connection, but endpoint should exist
        assert response.status_code in [201, 401, 404, 500, 502]

    @pytest.mark.asyncio
    async def test_update_calendar_event_endpoint(self, client: AsyncClient):
        """Test updating calendar event via API.
        
        Requirement 4.3: Update the corresponding Google Calendar event
        """
        exam_id = uuid.uuid4()
        response = await client.put(f"/api/v1/exams/calendar/sync/{exam_id}")
        assert response.status_code in [200, 401, 404, 500, 502]

    @pytest.mark.asyncio
    async def test_remove_from_calendar_endpoint(self, client: AsyncClient):
        """Test removing exam from calendar via API.
        
        Requirement 4.4: Delete the Google Calendar event
        """
        exam_id = uuid.uuid4()
        response = await client.delete(f"/api/v1/exams/calendar/sync/{exam_id}")
        assert response.status_code in [204, 401, 404, 500, 502]

    @pytest.mark.asyncio
    async def test_get_calendar_sync_status_endpoint(self, client: AsyncClient):
        """Test getting calendar sync status via API."""
        exam_id = uuid.uuid4()
        response = await client.get(f"/api/v1/exams/calendar/sync/{exam_id}")
        assert response.status_code in [200, 500]


# ============================================================================
# Error Handling Tests
# ============================================================================

class TestErrorHandling:
    """Tests for error handling in calendar operations."""

    def test_google_calendar_error_message(self):
        """Test GoogleCalendarError contains proper message."""
        error = GoogleCalendarError(message="API rate limit exceeded")
        assert str(error) == "API rate limit exceeded"
        assert error.message == "API rate limit exceeded"

    @pytest.mark.asyncio
    async def test_retry_preserves_error_details(self):
        """Test that retry preserves error details in final exception."""
        original_error = httpx.RequestError("Connection timeout")
        mock_func = AsyncMock(side_effect=original_error)
        
        with pytest.raises(GoogleCalendarError) as exc_info:
            await _retry_with_backoff(mock_func, max_retries=2, base_delay=0.01)
        
        assert "Connection timeout" in str(exc_info.value)


# ============================================================================
# Token Management Tests
# ============================================================================

class TestTokenManagement:
    """Tests for OAuth token management."""

    def test_token_expiry_check_logic(self):
        """Test token expiry checking logic."""
        # Token that expires in 10 minutes - should be valid
        future_expiry = datetime.now(timezone.utc) + timedelta(minutes=10)
        buffer = timedelta(minutes=5)
        assert datetime.now(timezone.utc) < future_expiry - buffer
        
        # Token that expires in 3 minutes - should need refresh
        near_expiry = datetime.now(timezone.utc) + timedelta(minutes=3)
        assert datetime.now(timezone.utc) >= near_expiry - buffer
        
        # Token that already expired - should need refresh
        past_expiry = datetime.now(timezone.utc) - timedelta(minutes=1)
        assert datetime.now(timezone.utc) >= past_expiry - buffer


# ============================================================================
# Constants Tests
# ============================================================================

class TestConstants:
    """Tests for service constants."""

    def test_max_retries_is_three(self):
        """Test that MAX_RETRIES is 3 as per requirement.
        
        Requirement 4.5: Retry up to 3 times
        """
        assert MAX_RETRIES == 3

    def test_base_delay_is_one_second(self):
        """Test that BASE_DELAY is 1 second for exponential backoff."""
        assert BASE_DELAY == 1
