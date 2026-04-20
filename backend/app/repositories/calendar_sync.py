"""Repository for Google Calendar sync operations.

Implements Requirements 4.1-4.5 for exam calendar integration.
"""

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.calendar_sync import CalendarSync, GoogleCalendarToken


class GoogleCalendarTokenRepository:
    """Repository for Google Calendar OAuth tokens.
    
    Requirement 4.1: Store OAuth tokens securely
    """

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_token(self, user_id: uuid.UUID) -> Optional[GoogleCalendarToken]:
        """Get user's Google Calendar token."""
        result = await self.session.execute(
            select(GoogleCalendarToken).where(GoogleCalendarToken.user_id == user_id)
        )
        return result.scalar_one_or_none()

    async def create_token(
        self,
        user_id: uuid.UUID,
        access_token: str,
        refresh_token: Optional[str],
        token_expiry: Optional[datetime],
        scope: Optional[str] = None,
    ) -> GoogleCalendarToken:
        """Create or update user's Google Calendar token."""
        existing = await self.get_token(user_id)
        
        if existing:
            existing.access_token = access_token
            existing.refresh_token = refresh_token or existing.refresh_token
            existing.token_expiry = token_expiry
            existing.scope = scope
            await self.session.commit()
            await self.session.refresh(existing)
            return existing
        
        token = GoogleCalendarToken(
            user_id=user_id,
            access_token=access_token,
            refresh_token=refresh_token,
            token_expiry=token_expiry,
            scope=scope,
        )
        self.session.add(token)
        await self.session.commit()
        await self.session.refresh(token)
        return token

    async def update_access_token(
        self,
        user_id: uuid.UUID,
        access_token: str,
        token_expiry: Optional[datetime],
    ) -> Optional[GoogleCalendarToken]:
        """Update user's access token after refresh."""
        token = await self.get_token(user_id)
        if not token:
            return None
        
        token.access_token = access_token
        token.token_expiry = token_expiry
        await self.session.commit()
        await self.session.refresh(token)
        return token

    async def delete_token(self, user_id: uuid.UUID) -> bool:
        """Delete user's Google Calendar token (disconnect)."""
        token = await self.get_token(user_id)
        if not token:
            return False
        
        await self.session.delete(token)
        await self.session.commit()
        return True


class CalendarSyncRepository:
    """Repository for calendar sync records.
    
    Requirements 4.2, 4.3, 4.4: Track synced calendar events
    """

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_sync(
        self,
        user_id: uuid.UUID,
        exam_id: uuid.UUID,
    ) -> Optional[CalendarSync]:
        """Get calendar sync record for a user and exam."""
        result = await self.session.execute(
            select(CalendarSync).where(
                CalendarSync.user_id == user_id,
                CalendarSync.exam_id == exam_id,
            )
        )
        return result.scalar_one_or_none()

    async def get_sync_by_event_id(
        self,
        user_id: uuid.UUID,
        google_event_id: str,
    ) -> Optional[CalendarSync]:
        """Get calendar sync record by Google event ID."""
        result = await self.session.execute(
            select(CalendarSync).where(
                CalendarSync.user_id == user_id,
                CalendarSync.google_event_id == google_event_id,
            )
        )
        return result.scalar_one_or_none()

    async def get_user_syncs(
        self,
        user_id: uuid.UUID,
    ) -> list[CalendarSync]:
        """Get all calendar syncs for a user."""
        result = await self.session.execute(
            select(CalendarSync).where(CalendarSync.user_id == user_id)
        )
        return list(result.scalars().all())

    async def create_sync(
        self,
        user_id: uuid.UUID,
        exam_id: uuid.UUID,
        google_event_id: str,
    ) -> CalendarSync:
        """Create a calendar sync record."""
        sync = CalendarSync(
            user_id=user_id,
            exam_id=exam_id,
            google_event_id=google_event_id,
        )
        self.session.add(sync)
        await self.session.commit()
        await self.session.refresh(sync)
        return sync

    async def update_sync(
        self,
        sync: CalendarSync,
        google_event_id: Optional[str] = None,
    ) -> CalendarSync:
        """Update a calendar sync record."""
        if google_event_id:
            sync.google_event_id = google_event_id
        sync.synced_at = datetime.utcnow()
        await self.session.commit()
        await self.session.refresh(sync)
        return sync

    async def delete_sync(self, sync: CalendarSync) -> None:
        """Delete a calendar sync record."""
        await self.session.delete(sync)
        await self.session.commit()

    async def delete_sync_by_exam(
        self,
        user_id: uuid.UUID,
        exam_id: uuid.UUID,
    ) -> bool:
        """Delete calendar sync for a specific exam."""
        sync = await self.get_sync(user_id, exam_id)
        if not sync:
            return False
        
        await self.session.delete(sync)
        await self.session.commit()
        return True
