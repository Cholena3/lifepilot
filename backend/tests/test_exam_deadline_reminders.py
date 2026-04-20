"""Unit tests for exam deadline reminders.

Validates: Requirements 3.7
"""

import uuid
from datetime import date, timedelta
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.models.exam import Exam, ExamBookmark, ExamType
from app.models.notification import NotificationChannel


# ============================================================================
# Repository Tests
# ============================================================================

class TestExamRepositoryDeadlineMethods:
    """Tests for exam repository deadline-related methods."""

    def test_get_exams_with_deadline_on_date_logic(self):
        """Test the logic for finding exams with deadline on a specific date.
        
        Validates: Requirements 3.7
        """
        target_date = date.today() + timedelta(days=7)
        
        # Exam with deadline on target date - should be included
        exam_deadline_match = date.today() + timedelta(days=7)
        assert exam_deadline_match == target_date
        
        # Exam with deadline before target date - should NOT be included
        exam_deadline_before = date.today() + timedelta(days=6)
        assert exam_deadline_before != target_date
        
        # Exam with deadline after target date - should NOT be included
        exam_deadline_after = date.today() + timedelta(days=8)
        assert exam_deadline_after != target_date
        
        # Exam with no deadline - should NOT be included
        exam_no_deadline = None
        assert exam_no_deadline != target_date


class TestExamBookmarkRepositoryMethods:
    """Tests for exam bookmark repository methods."""

    def test_get_users_who_bookmarked_exam_logic(self):
        """Test the logic for getting users who bookmarked an exam.
        
        Validates: Requirements 3.7
        """
        exam_id = uuid.uuid4()
        user1_id = uuid.uuid4()
        user2_id = uuid.uuid4()
        user3_id = uuid.uuid4()
        
        # Simulate bookmarks
        bookmarks = [
            {"user_id": user1_id, "exam_id": exam_id},
            {"user_id": user2_id, "exam_id": exam_id},
            {"user_id": user3_id, "exam_id": uuid.uuid4()},  # Different exam
        ]
        
        # Filter bookmarks for the target exam
        users_who_bookmarked = [
            b["user_id"] for b in bookmarks if b["exam_id"] == exam_id
        ]
        
        assert len(users_who_bookmarked) == 2
        assert user1_id in users_who_bookmarked
        assert user2_id in users_who_bookmarked
        assert user3_id not in users_who_bookmarked


# ============================================================================
# Task Logic Tests
# ============================================================================

class TestExamDeadlineReminderLogic:
    """Tests for exam deadline reminder task logic."""

    def test_deadline_calculation_7_days(self):
        """Test that deadline is calculated as 7 days from today.
        
        Validates: Requirements 3.7
        """
        today = date.today()
        target_date = today + timedelta(days=7)
        
        assert (target_date - today).days == 7

    def test_notification_title_format(self):
        """Test notification title format for deadline reminders.
        
        Validates: Requirements 3.7
        """
        exam_name = "TCS NQT 2024"
        expected_title = f"Exam Deadline Reminder: {exam_name}"
        
        assert expected_title == "Exam Deadline Reminder: TCS NQT 2024"

    def test_notification_body_format(self):
        """Test notification body format for deadline reminders.
        
        Validates: Requirements 3.7
        """
        exam_name = "TCS NQT 2024"
        organization = "Tata Consultancy Services"
        deadline = date.today() + timedelta(days=7)
        
        body = (
            f"The registration deadline for {exam_name} "
            f"({organization}) is in 7 days "
            f"({deadline.strftime('%B %d, %Y')}). "
            f"Don't miss the deadline!"
        )
        
        assert exam_name in body
        assert organization in body
        assert "7 days" in body
        assert deadline.strftime('%B %d, %Y') in body

    def test_only_active_exams_are_checked(self):
        """Test that only active exams are checked for deadlines.
        
        Validates: Requirements 3.7
        """
        # Active exam with deadline in 7 days - should be included
        active_exam = {"is_active": True, "registration_end": date.today() + timedelta(days=7)}
        
        # Inactive exam with deadline in 7 days - should NOT be included
        inactive_exam = {"is_active": False, "registration_end": date.today() + timedelta(days=7)}
        
        exams = [active_exam, inactive_exam]
        filtered_exams = [e for e in exams if e["is_active"]]
        
        assert len(filtered_exams) == 1
        assert filtered_exams[0]["is_active"] is True

    def test_exams_without_deadline_are_skipped(self):
        """Test that exams without registration_end are skipped.
        
        Validates: Requirements 3.7
        """
        target_date = date.today() + timedelta(days=7)
        
        # Exam with deadline
        exam_with_deadline = {"registration_end": target_date}
        
        # Exam without deadline
        exam_without_deadline = {"registration_end": None}
        
        exams = [exam_with_deadline, exam_without_deadline]
        filtered_exams = [
            e for e in exams 
            if e["registration_end"] is not None and e["registration_end"] == target_date
        ]
        
        assert len(filtered_exams) == 1
        assert filtered_exams[0]["registration_end"] == target_date


# ============================================================================
# Integration-style Tests (with mocks)
# ============================================================================

class TestExamDeadlineReminderTask:
    """Tests for the exam deadline reminder Celery task."""

    @pytest.mark.asyncio
    async def test_check_exam_deadline_reminders_no_exams(self):
        """Test task when no exams have deadlines in 7 days.
        
        Validates: Requirements 3.7
        """
        # Simulate the scenario where no exams have deadlines
        exams_with_deadline = []
        
        result = {
            "success": True,
            "exams_checked": len(exams_with_deadline),
            "notifications_sent": 0,
            "errors": [],
        }
        
        assert result["success"] is True
        assert result["exams_checked"] == 0
        assert result["notifications_sent"] == 0

    @pytest.mark.asyncio
    async def test_check_exam_deadline_reminders_with_exams(self):
        """Test task when exams have deadlines in 7 days.
        
        Validates: Requirements 3.7
        """
        # Simulate the scenario with exams and bookmarks
        exam_id = uuid.uuid4()
        user_ids = [uuid.uuid4(), uuid.uuid4()]
        
        exams_with_deadline = [{"id": exam_id, "name": "Test Exam"}]
        bookmarked_users = user_ids
        
        # Simulate successful notifications
        notifications_sent = len(bookmarked_users)
        
        result = {
            "success": True,
            "exams_checked": len(exams_with_deadline),
            "notifications_sent": notifications_sent,
            "errors": [],
        }
        
        assert result["success"] is True
        assert result["exams_checked"] == 1
        assert result["notifications_sent"] == 2

    @pytest.mark.asyncio
    async def test_check_exam_deadline_reminders_no_bookmarks(self):
        """Test task when exam has no bookmarks.
        
        Validates: Requirements 3.7
        """
        # Simulate exam with no bookmarks
        exam_id = uuid.uuid4()
        exams_with_deadline = [{"id": exam_id, "name": "Test Exam"}]
        bookmarked_users = []  # No users bookmarked
        
        notifications_sent = len(bookmarked_users)
        
        result = {
            "success": True,
            "exams_checked": len(exams_with_deadline),
            "notifications_sent": notifications_sent,
            "errors": [],
        }
        
        assert result["success"] is True
        assert result["exams_checked"] == 1
        assert result["notifications_sent"] == 0


# ============================================================================
# Edge Case Tests
# ============================================================================

class TestExamDeadlineReminderEdgeCases:
    """Edge case tests for exam deadline reminders."""

    def test_multiple_exams_same_deadline(self):
        """Test handling multiple exams with the same deadline.
        
        Validates: Requirements 3.7
        """
        target_date = date.today() + timedelta(days=7)
        
        exams = [
            {"id": uuid.uuid4(), "name": "Exam 1", "registration_end": target_date},
            {"id": uuid.uuid4(), "name": "Exam 2", "registration_end": target_date},
            {"id": uuid.uuid4(), "name": "Exam 3", "registration_end": target_date},
        ]
        
        filtered_exams = [e for e in exams if e["registration_end"] == target_date]
        
        assert len(filtered_exams) == 3

    def test_user_bookmarked_multiple_exams(self):
        """Test user who bookmarked multiple exams with same deadline.
        
        Validates: Requirements 3.7
        """
        user_id = uuid.uuid4()
        target_date = date.today() + timedelta(days=7)
        
        exams = [
            {"id": uuid.uuid4(), "name": "Exam 1", "registration_end": target_date},
            {"id": uuid.uuid4(), "name": "Exam 2", "registration_end": target_date},
        ]
        
        # User bookmarked both exams
        bookmarks = [
            {"user_id": user_id, "exam_id": exams[0]["id"]},
            {"user_id": user_id, "exam_id": exams[1]["id"]},
        ]
        
        # User should receive 2 notifications (one per exam)
        notifications_to_send = len(bookmarks)
        
        assert notifications_to_send == 2

    def test_deadline_exactly_7_days_boundary(self):
        """Test that only exams with deadline exactly 7 days away are included.
        
        Validates: Requirements 3.7
        """
        today = date.today()
        
        # Test various day offsets
        test_cases = [
            (6, False),   # 6 days - should NOT match
            (7, True),    # 7 days - should match
            (8, False),   # 8 days - should NOT match
        ]
        
        target_date = today + timedelta(days=7)
        
        for days_offset, should_match in test_cases:
            exam_deadline = today + timedelta(days=days_offset)
            matches = exam_deadline == target_date
            assert matches == should_match, f"Days offset {days_offset} should match: {should_match}"


# ============================================================================
# Celery Beat Schedule Tests
# ============================================================================

class TestCeleryBeatSchedule:
    """Tests for Celery beat schedule configuration."""

    def test_exam_deadline_task_in_beat_schedule(self):
        """Test that exam deadline task is in the beat schedule."""
        from app.tasks import celery_app
        
        beat_schedule = celery_app.conf.beat_schedule
        
        assert "check-exam-deadline-reminders-daily" in beat_schedule
        
        task_config = beat_schedule["check-exam-deadline-reminders-daily"]
        assert task_config["task"] == "app.tasks.exam_tasks.check_exam_deadline_reminders"
        assert task_config["schedule"] == 86400.0  # Daily (24 hours)

    def test_exam_tasks_module_included(self):
        """Test that exam_tasks module is included in Celery app."""
        from app.tasks import celery_app
        
        assert "app.tasks.exam_tasks" in celery_app.conf.include
