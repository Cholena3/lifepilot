"""Google Calendar service for exam calendar integration.

Implements Requirements 4.1-4.5 for exam calendar integration.
"""

import asyncio
import secrets
import uuid
from datetime import date, datetime, timedelta, timezone
from typing import Any, Optional
from urllib.parse import urlencode

import httpx
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.exceptions import AuthenticationError, NotFoundError, ServiceError
from app.models.calendar_sync import CalendarSync, GoogleCalendarToken
from app.models.exam import Exam
from app.repositories.calendar_sync import CalendarSyncRepository, GoogleCalendarTokenRepository
from app.repositories.exam import ExamRepository
from app.schemas.calendar import (
    CalendarEventDetails,
    CalendarEventResponse,
    CalendarSyncResponse,
    GoogleCalendarAuthURL,
    GoogleCalendarStatus,
    GoogleCalendarTokenResponse,
)

settings = get_settings()

# Google Calendar OAuth endpoints
GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_CALENDAR_API_BASE = "https://www.googleapis.com/calendar/v3"

# Calendar API scopes
CALENDAR_SCOPES = "https://www.googleapis.com/auth/calendar.events"

# Retry configuration (Requirement 4.5)
MAX_RETRIES = 3
BASE_DELAY = 1  # seconds


class GoogleCalendarError(ServiceError):
    """Error from Google Calendar API."""
    pass


async def _retry_with_backoff(
    func,
    *args,
    max_retries: int = MAX_RETRIES,
    base_delay: float = BASE_DELAY,
    **kwargs,
) -> Any:
    """Execute function with exponential backoff retry.
    
    Requirement 4.5: Retry up to 3 times with exponential backoff
    
    Args:
        func: Async function to execute
        max_retries: Maximum number of retry attempts
        base_delay: Base delay in seconds for exponential backoff
        *args: Positional arguments for func
        **kwargs: Keyword arguments for func
        
    Returns:
        Result from func
        
    Raises:
        GoogleCalendarError: If all retries fail
    """
    last_exception = None
    
    for attempt in range(max_retries):
        try:
            return await func(*args, **kwargs)
        except (httpx.HTTPStatusError, httpx.RequestError, GoogleCalendarError) as e:
            last_exception = e
            if attempt < max_retries - 1:
                delay = base_delay * (2 ** attempt)
                await asyncio.sleep(delay)
    
    raise GoogleCalendarError(
        message=f"Google Calendar API failed after {max_retries} retries: {str(last_exception)}"
    )


class GoogleCalendarService:
    """Service for Google Calendar integration.
    
    Implements Requirements 4.1-4.5 for exam calendar integration.
    """

    def __init__(self, session: AsyncSession):
        self.session = session
        self.token_repo = GoogleCalendarTokenRepository(session)
        self.sync_repo = CalendarSyncRepository(session)
        self.exam_repo = ExamRepository(session)

    # ========================================================================
    # OAuth Methods (Requirement 4.1)
    # ========================================================================

    def get_auth_url(self, state: Optional[str] = None) -> GoogleCalendarAuthURL:
        """Generate Google Calendar OAuth authorization URL.
        
        Requirement 4.1: Obtain OAuth tokens
        
        Args:
            state: Optional state parameter for CSRF protection
            
        Returns:
            GoogleCalendarAuthURL with auth_url and state
        """
        if state is None:
            state = secrets.token_urlsafe(32)
        
        params = {
            "client_id": settings.google_client_id,
            "redirect_uri": settings.google_calendar_redirect_uri,
            "response_type": "code",
            "scope": CALENDAR_SCOPES,
            "access_type": "offline",
            "state": state,
            "prompt": "consent",
        }
        
        auth_url = f"{GOOGLE_AUTH_URL}?{urlencode(params)}"
        return GoogleCalendarAuthURL(auth_url=auth_url, state=state)

    async def handle_callback(
        self,
        user_id: uuid.UUID,
        code: str,
    ) -> GoogleCalendarTokenResponse:
        """Handle Google Calendar OAuth callback.
        
        Requirement 4.1: Obtain OAuth tokens and store them securely
        
        Args:
            user_id: User ID
            code: Authorization code from Google
            
        Returns:
            GoogleCalendarTokenResponse indicating success
            
        Raises:
            AuthenticationError: If token exchange fails
        """
        # Exchange code for tokens
        token_data = await self._exchange_code(code)
        
        # Calculate token expiry
        expires_in = token_data.get("expires_in", 3600)
        token_expiry = datetime.now(timezone.utc) + timedelta(seconds=expires_in)
        
        # Store tokens
        await self.token_repo.create_token(
            user_id=user_id,
            access_token=token_data["access_token"],
            refresh_token=token_data.get("refresh_token"),
            token_expiry=token_expiry,
            scope=token_data.get("scope"),
        )
        
        return GoogleCalendarTokenResponse(
            connected=True,
            message="Google Calendar connected successfully",
        )

    async def _exchange_code(self, code: str) -> dict[str, Any]:
        """Exchange authorization code for tokens."""
        async with httpx.AsyncClient() as client:
            response = await client.post(
                GOOGLE_TOKEN_URL,
                data={
                    "client_id": settings.google_client_id,
                    "client_secret": settings.google_client_secret,
                    "code": code,
                    "grant_type": "authorization_code",
                    "redirect_uri": settings.google_calendar_redirect_uri,
                },
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )
            
            if response.status_code != 200:
                raise AuthenticationError(
                    message="Failed to exchange authorization code for Google Calendar"
                )
            
            return response.json()

    async def _refresh_access_token(
        self,
        user_id: uuid.UUID,
        refresh_token: str,
    ) -> str:
        """Refresh the access token using refresh token."""
        async with httpx.AsyncClient() as client:
            response = await client.post(
                GOOGLE_TOKEN_URL,
                data={
                    "client_id": settings.google_client_id,
                    "client_secret": settings.google_client_secret,
                    "refresh_token": refresh_token,
                    "grant_type": "refresh_token",
                },
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )
            
            if response.status_code != 200:
                raise AuthenticationError(
                    message="Failed to refresh Google Calendar access token"
                )
            
            token_data = response.json()
            expires_in = token_data.get("expires_in", 3600)
            token_expiry = datetime.now(timezone.utc) + timedelta(seconds=expires_in)
            
            await self.token_repo.update_access_token(
                user_id=user_id,
                access_token=token_data["access_token"],
                token_expiry=token_expiry,
            )
            
            return token_data["access_token"]

    async def _get_valid_access_token(self, user_id: uuid.UUID) -> str:
        """Get a valid access token, refreshing if necessary."""
        token = await self.token_repo.get_token(user_id)
        if not token:
            raise AuthenticationError(
                message="Google Calendar not connected. Please connect your calendar first."
            )
        
        # Check if token is expired or about to expire (within 5 minutes)
        if token.token_expiry:
            buffer = timedelta(minutes=5)
            if datetime.now(timezone.utc) >= token.token_expiry - buffer:
                if token.refresh_token:
                    return await self._refresh_access_token(user_id, token.refresh_token)
                else:
                    raise AuthenticationError(
                        message="Google Calendar token expired. Please reconnect your calendar."
                    )
        
        return token.access_token

    async def get_connection_status(self, user_id: uuid.UUID) -> GoogleCalendarStatus:
        """Get Google Calendar connection status.
        
        Args:
            user_id: User ID
            
        Returns:
            GoogleCalendarStatus with connection info
        """
        token = await self.token_repo.get_token(user_id)
        if not token:
            return GoogleCalendarStatus(connected=False, token_expiry=None)
        
        return GoogleCalendarStatus(
            connected=True,
            token_expiry=token.token_expiry,
        )

    async def disconnect(self, user_id: uuid.UUID) -> bool:
        """Disconnect Google Calendar.
        
        Args:
            user_id: User ID
            
        Returns:
            True if disconnected, False if not connected
        """
        # Delete all calendar syncs for this user
        syncs = await self.sync_repo.get_user_syncs(user_id)
        for sync in syncs:
            await self.sync_repo.delete_sync(sync)
        
        # Delete the token
        return await self.token_repo.delete_token(user_id)

    # ========================================================================
    # Calendar Event Methods (Requirements 4.2, 4.3, 4.4)
    # ========================================================================

    async def create_event(
        self,
        user_id: uuid.UUID,
        exam_id: uuid.UUID,
    ) -> CalendarEventResponse:
        """Create a Google Calendar event for an exam.
        
        Requirement 4.2: Create a Google Calendar event with exam details
        
        Args:
            user_id: User ID
            exam_id: Exam ID
            
        Returns:
            CalendarEventResponse with event details
            
        Raises:
            NotFoundError: If exam not found
            AuthenticationError: If calendar not connected
            GoogleCalendarError: If API call fails
        """
        # Check if already synced
        existing_sync = await self.sync_repo.get_sync(user_id, exam_id)
        if existing_sync:
            # Update instead of create
            return await self.update_event(user_id, exam_id)
        
        # Get exam details
        exam = await self.exam_repo.get_exam_by_id(exam_id)
        if not exam:
            raise NotFoundError(message="Exam not found")
        
        # Get valid access token
        access_token = await self._get_valid_access_token(user_id)
        
        # Build event data
        event_data = self._build_event_data(exam)
        
        # Create event with retry
        google_event_id = await _retry_with_backoff(
            self._create_calendar_event,
            access_token,
            event_data,
        )
        
        # Save sync record
        sync = await self.sync_repo.create_sync(
            user_id=user_id,
            exam_id=exam_id,
            google_event_id=google_event_id,
        )
        
        return CalendarEventResponse(
            id=sync.id,
            exam_id=sync.exam_id,
            google_event_id=sync.google_event_id,
            synced_at=sync.synced_at,
        )

    async def update_event(
        self,
        user_id: uuid.UUID,
        exam_id: uuid.UUID,
    ) -> CalendarEventResponse:
        """Update a Google Calendar event for an exam.
        
        Requirement 4.3: Update the corresponding Google Calendar event
        
        Args:
            user_id: User ID
            exam_id: Exam ID
            
        Returns:
            CalendarEventResponse with updated event details
            
        Raises:
            NotFoundError: If exam or sync not found
            AuthenticationError: If calendar not connected
            GoogleCalendarError: If API call fails
        """
        # Get sync record
        sync = await self.sync_repo.get_sync(user_id, exam_id)
        if not sync:
            raise NotFoundError(message="Exam not synced to calendar")
        
        # Get exam details
        exam = await self.exam_repo.get_exam_by_id(exam_id)
        if not exam:
            raise NotFoundError(message="Exam not found")
        
        # Get valid access token
        access_token = await self._get_valid_access_token(user_id)
        
        # Build event data
        event_data = self._build_event_data(exam)
        
        # Update event with retry
        await _retry_with_backoff(
            self._update_calendar_event,
            access_token,
            sync.google_event_id,
            event_data,
        )
        
        # Update sync record
        sync = await self.sync_repo.update_sync(sync)
        
        return CalendarEventResponse(
            id=sync.id,
            exam_id=sync.exam_id,
            google_event_id=sync.google_event_id,
            synced_at=sync.synced_at,
        )

    async def delete_event(
        self,
        user_id: uuid.UUID,
        exam_id: uuid.UUID,
    ) -> bool:
        """Delete a Google Calendar event for an exam.
        
        Requirement 4.4: Delete the Google Calendar event
        
        Args:
            user_id: User ID
            exam_id: Exam ID
            
        Returns:
            True if deleted successfully
            
        Raises:
            NotFoundError: If sync not found
            AuthenticationError: If calendar not connected
            GoogleCalendarError: If API call fails
        """
        # Get sync record
        sync = await self.sync_repo.get_sync(user_id, exam_id)
        if not sync:
            raise NotFoundError(message="Exam not synced to calendar")
        
        # Get valid access token
        access_token = await self._get_valid_access_token(user_id)
        
        # Delete event with retry
        await _retry_with_backoff(
            self._delete_calendar_event,
            access_token,
            sync.google_event_id,
        )
        
        # Delete sync record
        await self.sync_repo.delete_sync(sync)
        
        return True

    async def get_sync_status(
        self,
        user_id: uuid.UUID,
        exam_id: uuid.UUID,
    ) -> CalendarSyncResponse:
        """Get calendar sync status for an exam.
        
        Args:
            user_id: User ID
            exam_id: Exam ID
            
        Returns:
            CalendarSyncResponse with sync status
        """
        sync = await self.sync_repo.get_sync(user_id, exam_id)
        
        if not sync:
            return CalendarSyncResponse(
                exam_id=exam_id,
                is_synced=False,
                google_event_id=None,
                synced_at=None,
            )
        
        return CalendarSyncResponse(
            exam_id=exam_id,
            is_synced=True,
            google_event_id=sync.google_event_id,
            synced_at=sync.synced_at,
        )

    # ========================================================================
    # Private Helper Methods
    # ========================================================================

    def _build_event_data(self, exam: Exam) -> dict[str, Any]:
        """Build Google Calendar event data from exam."""
        # Use exam_date if available, otherwise registration_end
        event_date = exam.exam_date or exam.registration_end
        if not event_date:
            event_date = date.today() + timedelta(days=30)  # Default to 30 days from now
        
        # Build description
        description_parts = []
        if exam.description:
            description_parts.append(exam.description)
        if exam.organization:
            description_parts.append(f"Organization: {exam.organization}")
        if exam.registration_start and exam.registration_end:
            description_parts.append(
                f"Registration: {exam.registration_start} to {exam.registration_end}"
            )
        if exam.source_url:
            description_parts.append(f"More info: {exam.source_url}")
        
        description = "\n\n".join(description_parts) if description_parts else None
        
        # Build event
        event = {
            "summary": f"Exam: {exam.name}",
            "description": description,
            "start": {
                "date": event_date.isoformat(),
            },
            "end": {
                "date": event_date.isoformat(),
            },
            "reminders": {
                "useDefault": False,
                "overrides": [
                    {"method": "popup", "minutes": 1440},  # 1 day before
                    {"method": "popup", "minutes": 10080},  # 7 days before
                ],
            },
        }
        
        return event

    async def _create_calendar_event(
        self,
        access_token: str,
        event_data: dict[str, Any],
    ) -> str:
        """Create a calendar event via Google Calendar API."""
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{GOOGLE_CALENDAR_API_BASE}/calendars/primary/events",
                json=event_data,
                headers={
                    "Authorization": f"Bearer {access_token}",
                    "Content-Type": "application/json",
                },
            )
            
            if response.status_code not in [200, 201]:
                raise GoogleCalendarError(
                    message=f"Failed to create calendar event: {response.text}"
                )
            
            return response.json()["id"]

    async def _update_calendar_event(
        self,
        access_token: str,
        event_id: str,
        event_data: dict[str, Any],
    ) -> None:
        """Update a calendar event via Google Calendar API."""
        async with httpx.AsyncClient() as client:
            response = await client.put(
                f"{GOOGLE_CALENDAR_API_BASE}/calendars/primary/events/{event_id}",
                json=event_data,
                headers={
                    "Authorization": f"Bearer {access_token}",
                    "Content-Type": "application/json",
                },
            )
            
            if response.status_code != 200:
                raise GoogleCalendarError(
                    message=f"Failed to update calendar event: {response.text}"
                )

    async def _delete_calendar_event(
        self,
        access_token: str,
        event_id: str,
    ) -> None:
        """Delete a calendar event via Google Calendar API."""
        async with httpx.AsyncClient() as client:
            response = await client.delete(
                f"{GOOGLE_CALENDAR_API_BASE}/calendars/primary/events/{event_id}",
                headers={
                    "Authorization": f"Bearer {access_token}",
                },
            )
            
            # 204 No Content or 410 Gone (already deleted) are both acceptable
            if response.status_code not in [200, 204, 410]:
                raise GoogleCalendarError(
                    message=f"Failed to delete calendar event: {response.text}"
                )
