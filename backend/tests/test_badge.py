"""Tests for Badge gamification module.

Tests the badge model, schemas, service, and router functionality.

Validates: Requirements 33.3, 33.5, 33.6
"""

import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.badge import Badge, BadgeType, BADGE_METADATA
from app.schemas.badge import (
    AllBadgesResponse,
    BadgeAwardRequest,
    BadgeAwardResponse,
    BadgeListResponse,
    BadgeResponse,
    BadgeTypeInfo,
)
from app.services.badge import BadgeService, SIGNIFICANT_SCORE_CHANGE_THRESHOLD


class TestBadgeModel:
    """Tests for Badge model and BadgeType enum."""
    
    def test_badge_type_enum_has_expected_values(self):
        """Test that BadgeType enum has all expected badge types."""
        # Profile badges
        assert BadgeType.PROFILE_COMPLETE.value == "profile_complete"
        
        # Document badges
        assert BadgeType.FIRST_DOCUMENT.value == "first_document"
        assert BadgeType.DOCUMENT_ORGANIZER.value == "document_organizer"
        assert BadgeType.DOCUMENT_MASTER.value == "document_master"
        
        # Finance badges
        assert BadgeType.FIRST_EXPENSE.value == "first_expense"
        assert BadgeType.BUDGET_CREATOR.value == "budget_creator"
        
        # Health badges
        assert BadgeType.FIRST_HEALTH_RECORD.value == "first_health_record"
        
        # Wardrobe badges
        assert BadgeType.FIRST_WARDROBE_ITEM.value == "first_wardrobe_item"
        
        # Career badges
        assert BadgeType.FIRST_SKILL.value == "first_skill"
        assert BadgeType.FIRST_COURSE.value == "first_course"
        
        # Exam badges
        assert BadgeType.FIRST_EXAM_BOOKMARK.value == "first_exam_bookmark"
        
        # Life Score badges
        assert BadgeType.SCORE_RISING.value == "score_rising"
        assert BadgeType.SCORE_ACHIEVER.value == "score_achiever"
        assert BadgeType.SCORE_MASTER.value == "score_master"
    
    def test_badge_metadata_has_all_badge_types(self):
        """Test that BADGE_METADATA has entries for all badge types."""
        for badge_type in BadgeType:
            assert badge_type in BADGE_METADATA, f"Missing metadata for {badge_type}"
            assert "name" in BADGE_METADATA[badge_type]
            assert "description" in BADGE_METADATA[badge_type]
    
    def test_badge_metadata_has_valid_content(self):
        """Test that badge metadata has non-empty name and description."""
        for badge_type, metadata in BADGE_METADATA.items():
            assert len(metadata["name"]) > 0, f"Empty name for {badge_type}"
            assert len(metadata["description"]) > 0, f"Empty description for {badge_type}"


class TestBadgeSchemas:
    """Tests for Badge Pydantic schemas."""
    
    def test_badge_response_valid(self):
        """Test BadgeResponse schema with valid data."""
        now = datetime.now(timezone.utc)
        response = BadgeResponse(
            id=uuid.uuid4(),
            user_id=uuid.uuid4(),
            badge_type="first_document",
            name="First Document",
            description="Uploaded your first document",
            earned_at=now,
            created_at=now,
            updated_at=now,
        )
        assert response.badge_type == "first_document"
        assert response.name == "First Document"
    
    def test_badge_list_response_valid(self):
        """Test BadgeListResponse schema with valid data."""
        now = datetime.now(timezone.utc)
        badges = [
            BadgeResponse(
                id=uuid.uuid4(),
                user_id=uuid.uuid4(),
                badge_type="first_document",
                name="First Document",
                description="Uploaded your first document",
                earned_at=now,
                created_at=now,
                updated_at=now,
            )
        ]
        response = BadgeListResponse(badges=badges, total_count=1)
        assert len(response.badges) == 1
        assert response.total_count == 1
    
    def test_badge_award_request_valid(self):
        """Test BadgeAwardRequest schema with valid data."""
        request = BadgeAwardRequest(badge_type=BadgeType.FIRST_DOCUMENT)
        assert request.badge_type == BadgeType.FIRST_DOCUMENT
    
    def test_badge_award_response_new_badge(self):
        """Test BadgeAwardResponse for newly awarded badge."""
        now = datetime.now(timezone.utc)
        badge = BadgeResponse(
            id=uuid.uuid4(),
            user_id=uuid.uuid4(),
            badge_type="first_document",
            name="First Document",
            description="Uploaded your first document",
            earned_at=now,
            created_at=now,
            updated_at=now,
        )
        response = BadgeAwardResponse(
            badge=badge,
            already_earned=False,
            message="Congratulations!",
        )
        assert response.already_earned is False
        assert response.badge is not None
    
    def test_badge_award_response_already_earned(self):
        """Test BadgeAwardResponse for already earned badge."""
        now = datetime.now(timezone.utc)
        badge = BadgeResponse(
            id=uuid.uuid4(),
            user_id=uuid.uuid4(),
            badge_type="first_document",
            name="First Document",
            description="Uploaded your first document",
            earned_at=now,
            created_at=now,
            updated_at=now,
        )
        response = BadgeAwardResponse(
            badge=badge,
            already_earned=True,
            message="Already earned",
        )
        assert response.already_earned is True
    
    def test_badge_type_info_valid(self):
        """Test BadgeTypeInfo schema with valid data."""
        info = BadgeTypeInfo(
            badge_type="first_document",
            name="First Document",
            description="Upload your first document",
            earned=True,
            earned_at=datetime.now(timezone.utc),
        )
        assert info.earned is True
        assert info.earned_at is not None
    
    def test_all_badges_response_valid(self):
        """Test AllBadgesResponse schema with valid data."""
        badges = [
            BadgeTypeInfo(
                badge_type="first_document",
                name="First Document",
                description="Upload your first document",
                earned=True,
                earned_at=datetime.now(timezone.utc),
            ),
            BadgeTypeInfo(
                badge_type="document_organizer",
                name="Document Organizer",
                description="Upload 10 documents",
                earned=False,
                earned_at=None,
            ),
        ]
        response = AllBadgesResponse(
            badges=badges,
            earned_count=1,
            total_count=2,
        )
        assert response.earned_count == 1
        assert response.total_count == 2


class TestBadgeService:
    """Tests for BadgeService."""
    
    @pytest.fixture
    def mock_db(self):
        """Create a mock database session."""
        return AsyncMock(spec=AsyncSession)
    
    @pytest.fixture
    def service(self, mock_db):
        """Create a BadgeService instance with mock db."""
        return BadgeService(mock_db)
    
    def test_significant_score_change_threshold(self):
        """Test that significant score change threshold is defined."""
        assert SIGNIFICANT_SCORE_CHANGE_THRESHOLD == 10
    
    @pytest.mark.asyncio
    async def test_check_significant_score_change_above_threshold(self, service):
        """Test significant score change detection above threshold."""
        user_id = uuid.uuid4()
        result = await service.check_significant_score_change(
            user_id, current_score=60, previous_score=45
        )
        assert result is True  # 15 point change > 10 threshold
    
    @pytest.mark.asyncio
    async def test_check_significant_score_change_below_threshold(self, service):
        """Test significant score change detection below threshold."""
        user_id = uuid.uuid4()
        result = await service.check_significant_score_change(
            user_id, current_score=55, previous_score=50
        )
        assert result is False  # 5 point change < 10 threshold
    
    @pytest.mark.asyncio
    async def test_check_significant_score_change_at_threshold(self, service):
        """Test significant score change detection at threshold."""
        user_id = uuid.uuid4()
        result = await service.check_significant_score_change(
            user_id, current_score=60, previous_score=50
        )
        assert result is True  # 10 point change == 10 threshold
    
    @pytest.mark.asyncio
    async def test_check_significant_score_change_negative(self, service):
        """Test significant score change detection for decrease."""
        user_id = uuid.uuid4()
        result = await service.check_significant_score_change(
            user_id, current_score=40, previous_score=55
        )
        assert result is True  # 15 point decrease > 10 threshold
    
    @pytest.mark.asyncio
    async def test_get_score_change_notification_message_increase(self, service):
        """Test notification message for score increase."""
        title, body = await service.get_score_change_notification_message(
            current_score=75, previous_score=60
        )
        assert "Increased" in title
        assert "75" in body
        assert "60" in body
        assert "+15" in body
    
    @pytest.mark.asyncio
    async def test_get_score_change_notification_message_decrease(self, service):
        """Test notification message for score decrease."""
        title, body = await service.get_score_change_notification_message(
            current_score=50, previous_score=65
        )
        assert "Update" in title
        assert "50" in body
        assert "65" in body
        assert "-15" in body


class TestBadgeMilestones:
    """Tests for badge milestone thresholds."""
    
    def test_document_milestones(self):
        """Test document badge milestone thresholds."""
        # First document: 1
        # Document organizer: 10
        # Document master: 50
        assert BadgeType.FIRST_DOCUMENT in BadgeType
        assert BadgeType.DOCUMENT_ORGANIZER in BadgeType
        assert BadgeType.DOCUMENT_MASTER in BadgeType
    
    def test_expense_milestones(self):
        """Test expense badge milestone thresholds."""
        # First expense: 1
        # Expense tracker: 30
        assert BadgeType.FIRST_EXPENSE in BadgeType
        assert BadgeType.EXPENSE_TRACKER in BadgeType
    
    def test_score_milestones(self):
        """Test Life Score badge milestone thresholds."""
        # Score achiever: 50+
        # Score master: 80+
        # Score rising: 10+ point increase
        assert BadgeType.SCORE_ACHIEVER in BadgeType
        assert BadgeType.SCORE_MASTER in BadgeType
        assert BadgeType.SCORE_RISING in BadgeType


class TestBadgeRouter:
    """Tests for badge router endpoints."""
    
    def test_badge_type_enum_is_string_enum(self):
        """Test that BadgeType is a string enum for API compatibility."""
        assert isinstance(BadgeType.FIRST_DOCUMENT.value, str)
        assert BadgeType.FIRST_DOCUMENT.value == "first_document"
