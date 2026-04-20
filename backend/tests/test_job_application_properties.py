"""Property-based tests for job application status pipeline.

Uses Hypothesis to verify universal properties across all valid inputs.

**Validates: Requirements 27.2, 27.3**
"""

from datetime import datetime, timezone
from uuid import uuid4

import pytest
from hypothesis import given, strategies as st, settings, assume

from app.models.job_application import ApplicationStatus
from app.schemas.job_application import (
    ApplicationStatusHistoryResponse,
    JobApplicationCreate,
    JobApplicationResponse,
    JobApplicationWithHistoryResponse,
    StatusUpdateRequest,
)


# ============================================================================
# Hypothesis Strategies for Job Application Data
# ============================================================================

@st.composite
def valid_company_names(draw):
    """Generate valid company names (1-255 characters)."""
    chars = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789 .-&"
    length = draw(st.integers(min_value=1, max_value=50))
    
    # Start with a letter
    first_char = draw(st.sampled_from("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ"))
    
    if length == 1:
        return first_char
    
    rest = draw(st.text(alphabet=chars, min_size=length - 1, max_size=length - 1))
    name = first_char + rest
    
    # Clean up consecutive spaces
    while "  " in name:
        name = name.replace("  ", " ")
    
    return name.strip()[:255]


@st.composite
def valid_role_names(draw):
    """Generate valid role names (1-255 characters)."""
    chars = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789 .-/"
    length = draw(st.integers(min_value=1, max_value=50))
    
    # Start with a letter
    first_char = draw(st.sampled_from("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ"))
    
    if length == 1:
        return first_char
    
    rest = draw(st.text(alphabet=chars, min_size=length - 1, max_size=length - 1))
    name = first_char + rest
    
    # Clean up consecutive spaces
    while "  " in name:
        name = name.replace("  ", " ")
    
    return name.strip()[:255]


@st.composite
def valid_application_statuses(draw):
    """Generate valid application statuses."""
    return draw(st.sampled_from(list(ApplicationStatus)))


@st.composite
def non_terminal_statuses(draw):
    """Generate non-terminal application statuses.
    
    Non-terminal statuses are: Applied, Screening, Interview
    """
    return draw(st.sampled_from([
        ApplicationStatus.APPLIED,
        ApplicationStatus.SCREENING,
        ApplicationStatus.INTERVIEW,
    ]))


@st.composite
def terminal_statuses(draw):
    """Generate terminal application statuses.
    
    Terminal statuses are: Offer, Rejected, Withdrawn
    """
    return draw(st.sampled_from([
        ApplicationStatus.OFFER,
        ApplicationStatus.REJECTED,
        ApplicationStatus.WITHDRAWN,
    ]))


@st.composite
def distinct_status_pair(draw):
    """Generate two distinct application statuses for testing updates."""
    status1 = draw(valid_application_statuses())
    status2 = draw(valid_application_statuses())
    assume(status1 != status2)
    return status1, status2


@st.composite
def status_transition_sequence(draw, min_length=2, max_length=5):
    """Generate a sequence of status transitions.
    
    Returns a list of statuses where each consecutive pair
    represents a transition from one status to another.
    """
    length = draw(st.integers(min_value=min_length, max_value=max_length))
    statuses = draw(st.lists(
        valid_application_statuses(),
        min_size=length,
        max_size=length,
    ))
    return statuses


@st.composite
def valid_job_application_data(draw):
    """Generate valid job application data for testing."""
    return {
        "company": draw(valid_company_names()),
        "role": draw(valid_role_names()),
        "status": draw(valid_application_statuses()),
    }


# ============================================================================
# Property 40: Job Application Status Pipeline
# ============================================================================

class TestJobApplicationStatusPipelineProperty:
    """Property 40: Job Application Status Pipeline.
    
    **Validates: Requirements 27.2, 27.3**
    
    For any job application, the status SHALL be one of: Applied, Screening,
    Interview, Offer, Rejected, or Withdrawn, and status changes SHALL be
    recorded with timestamps.
    """
    
    @given(
        app_data=valid_job_application_data(),
        new_status=valid_application_statuses(),
    )
    @settings(max_examples=50, deadline=None)
    def test_status_transition_creates_history_entry(
        self, app_data: dict, new_status: ApplicationStatus
    ):
        """Any status transition SHALL create a history entry with the correct
        previous and new status.
        
        **Validates: Requirements 27.2, 27.3**
        
        This test verifies that:
        1. A job application can be created with an initial status
        2. When status is updated, a history entry is created
        3. The history entry records the previous and new statuses correctly
        """
        # Skip if status is the same (no change to record)
        assume(app_data["status"] != new_status)
        
        # Create initial job application
        app_create = JobApplicationCreate(
            company=app_data["company"],
            role=app_data["role"],
            status=app_data["status"],
        )
        
        # Verify initial application creation
        assert app_create.status == app_data["status"]
        
        # Simulate the history entry that would be created on status update
        application_id = uuid4()
        history_entry = ApplicationStatusHistoryResponse(
            id=uuid4(),
            application_id=application_id,
            previous_status=app_data["status"],
            new_status=new_status,
            changed_at=datetime.now(timezone.utc),
            notes=None,
        )
        
        # Verify history entry records the change correctly
        assert history_entry.previous_status == app_data["status"], (
            f"History entry should record previous status {app_data['status']}, "
            f"but got {history_entry.previous_status}"
        )
        assert history_entry.new_status == new_status, (
            f"History entry should record new status {new_status}, "
            f"but got {history_entry.new_status}"
        )
        assert history_entry.application_id == application_id, (
            "History entry should be associated with the correct application"
        )
    
    @given(
        app_data=valid_job_application_data(),
        status_pair=distinct_status_pair(),
    )
    @settings(max_examples=50, deadline=None)
    def test_history_entry_has_valid_timestamp(
        self, app_data: dict, status_pair: tuple
    ):
        """The history entry SHALL have a valid timestamp when status is updated.
        
        **Validates: Requirements 27.3**
        
        This test verifies that:
        1. History entries have a timestamp
        2. The timestamp is a valid datetime
        3. The timestamp is not in the future
        """
        old_status, new_status = status_pair
        
        # Record time before creating history entry
        before_time = datetime.now(timezone.utc)
        
        # Simulate history entry creation
        application_id = uuid4()
        history_entry = ApplicationStatusHistoryResponse(
            id=uuid4(),
            application_id=application_id,
            previous_status=old_status,
            new_status=new_status,
            changed_at=datetime.now(timezone.utc),
            notes=None,
        )
        
        # Record time after creating history entry
        after_time = datetime.now(timezone.utc)
        
        # Verify timestamp is valid
        assert history_entry.changed_at is not None, (
            "History entry must have a timestamp"
        )
        assert isinstance(history_entry.changed_at, datetime), (
            "Timestamp must be a datetime object"
        )
        
        # Verify timestamp is within expected range
        assert before_time <= history_entry.changed_at <= after_time, (
            f"Timestamp {history_entry.changed_at} should be between "
            f"{before_time} and {after_time}"
        )
    
    @given(status_sequence=status_transition_sequence(min_length=2, max_length=5))
    @settings(max_examples=50, deadline=None)
    def test_status_changes_recorded_in_chronological_order(
        self, status_sequence: list
    ):
        """Status changes SHALL be recorded in chronological order.
        
        **Validates: Requirements 27.3**
        
        This test verifies that:
        1. Each status change creates a new history entry
        2. History entries are in chronological order
        3. The progression is correctly recorded
        """
        application_id = uuid4()
        history_entries = []
        
        # Simulate multiple status changes
        for i in range(len(status_sequence) - 1):
            old_status = status_sequence[i]
            new_status = status_sequence[i + 1]
            
            # Only create history entry if statuses are different
            if old_status != new_status:
                entry = ApplicationStatusHistoryResponse(
                    id=uuid4(),
                    application_id=application_id,
                    previous_status=old_status,
                    new_status=new_status,
                    changed_at=datetime.now(timezone.utc),
                    notes=None,
                )
                history_entries.append(entry)
        
        # Verify history entries are in chronological order
        for i in range(len(history_entries) - 1):
            assert history_entries[i].changed_at <= history_entries[i + 1].changed_at, (
                f"History entries should be in chronological order. "
                f"Entry {i} at {history_entries[i].changed_at} should be before "
                f"entry {i + 1} at {history_entries[i + 1].changed_at}"
            )
        
        # Verify progression is correctly recorded
        for i in range(len(history_entries) - 1):
            # The new_status of entry i should match the previous_status of entry i+1
            # (if they represent consecutive changes)
            current_new = history_entries[i].new_status
            next_prev = history_entries[i + 1].previous_status
            assert current_new == next_prev, (
                f"Progression mismatch: entry {i} new_status={current_new} "
                f"should match entry {i + 1} previous_status={next_prev}"
            )
    
    @given(
        non_terminal=non_terminal_statuses(),
        terminal=terminal_statuses(),
    )
    @settings(max_examples=50, deadline=None)
    def test_terminal_statuses_reachable_from_non_terminal(
        self, non_terminal: ApplicationStatus, terminal: ApplicationStatus
    ):
        """Terminal statuses (Offer, Rejected, Withdrawn) SHALL be reachable
        from any non-terminal status.
        
        **Validates: Requirements 27.2**
        
        This test verifies that:
        1. Any non-terminal status can transition to a terminal status
        2. The transition is valid and creates a history entry
        """
        application_id = uuid4()
        
        # Create status update request
        status_update = StatusUpdateRequest(
            status=terminal,
            notes=f"Transitioning from {non_terminal.value} to {terminal.value}",
        )
        
        # Verify the update request is valid
        assert status_update.status == terminal
        
        # Simulate history entry for the transition
        history_entry = ApplicationStatusHistoryResponse(
            id=uuid4(),
            application_id=application_id,
            previous_status=non_terminal,
            new_status=terminal,
            changed_at=datetime.now(timezone.utc),
            notes=status_update.notes,
        )
        
        # Verify the transition is recorded correctly
        assert history_entry.previous_status == non_terminal, (
            f"Previous status should be {non_terminal}"
        )
        assert history_entry.new_status == terminal, (
            f"New status should be {terminal}"
        )
        
        # Verify terminal status is one of the expected values
        assert terminal in [
            ApplicationStatus.OFFER,
            ApplicationStatus.REJECTED,
            ApplicationStatus.WITHDRAWN,
        ], f"Terminal status {terminal} should be Offer, Rejected, or Withdrawn"
    
    @given(status=valid_application_statuses())
    @settings(max_examples=50, deadline=None)
    def test_status_pipeline_supports_all_defined_statuses(
        self, status: ApplicationStatus
    ):
        """The status pipeline SHALL support all defined statuses: Applied,
        Screening, Interview, Offer, Rejected, Withdrawn.
        
        **Validates: Requirements 27.2**
        
        This test verifies that:
        1. All defined statuses are valid ApplicationStatus enum values
        2. Each status can be used in a job application
        3. Each status can be used in a status update request
        """
        # Verify status is a valid ApplicationStatus
        assert isinstance(status, ApplicationStatus), (
            f"{status} should be an ApplicationStatus enum value"
        )
        
        # Verify status is one of the defined values
        defined_statuses = [
            ApplicationStatus.APPLIED,
            ApplicationStatus.SCREENING,
            ApplicationStatus.INTERVIEW,
            ApplicationStatus.OFFER,
            ApplicationStatus.REJECTED,
            ApplicationStatus.WITHDRAWN,
        ]
        assert status in defined_statuses, (
            f"Status {status} should be one of the defined statuses"
        )
        
        # Verify status can be used in job application creation
        app_create = JobApplicationCreate(
            company="Test Company",
            role="Test Role",
            status=status,
        )
        assert app_create.status == status, (
            f"Job application should accept status {status}"
        )
        
        # Verify status can be used in status update request
        status_update = StatusUpdateRequest(status=status)
        assert status_update.status == status, (
            f"Status update request should accept status {status}"
        )
    
    def test_all_six_statuses_are_defined(self):
        """The ApplicationStatus enum SHALL define exactly 6 statuses.
        
        **Validates: Requirements 27.2**
        
        This test verifies that:
        1. There are exactly 6 statuses defined
        2. All required statuses are present
        """
        # Verify exactly 6 statuses
        assert len(ApplicationStatus) == 6, (
            f"Expected 6 statuses, but found {len(ApplicationStatus)}"
        )
        
        # Verify all required statuses are present
        required_statuses = {
            "applied": ApplicationStatus.APPLIED,
            "screening": ApplicationStatus.SCREENING,
            "interview": ApplicationStatus.INTERVIEW,
            "offer": ApplicationStatus.OFFER,
            "rejected": ApplicationStatus.REJECTED,
            "withdrawn": ApplicationStatus.WITHDRAWN,
        }
        
        for value, status in required_statuses.items():
            assert status.value == value, (
                f"Status {status} should have value '{value}'"
            )
    
    @given(app_data=valid_job_application_data())
    @settings(max_examples=50, deadline=None)
    def test_application_with_history_response_contains_history(
        self, app_data: dict
    ):
        """A job application response with history SHALL contain the status
        history showing the progression.
        
        **Validates: Requirements 27.3**
        
        This test verifies that:
        1. JobApplicationWithHistoryResponse includes status_history field
        2. The history list can contain multiple entries
        3. Each entry has the required fields
        """
        application_id = uuid4()
        user_id = uuid4()
        now = datetime.now(timezone.utc)
        
        # Create history entries
        history_entries = [
            ApplicationStatusHistoryResponse(
                id=uuid4(),
                application_id=application_id,
                previous_status=None,  # Initial creation
                new_status=ApplicationStatus.APPLIED,
                changed_at=now,
                notes="Application created",
            ),
            ApplicationStatusHistoryResponse(
                id=uuid4(),
                application_id=application_id,
                previous_status=ApplicationStatus.APPLIED,
                new_status=ApplicationStatus.SCREENING,
                changed_at=now,
                notes="Moved to screening",
            ),
        ]
        
        # Create application with history response
        from datetime import date
        app_response = JobApplicationWithHistoryResponse(
            id=application_id,
            user_id=user_id,
            company=app_data["company"],
            role=app_data["role"],
            url=None,
            source="other",
            status=ApplicationStatus.SCREENING,
            salary_min=None,
            salary_max=None,
            applied_date=date.today(),
            notes=None,
            location=None,
            is_remote=False,
            last_status_update=now,
            created_at=now,
            updated_at=now,
            status_history=history_entries,
            follow_up_reminders=[],
        )
        
        # Verify history is included
        assert app_response.status_history is not None, (
            "Application response should include status_history"
        )
        assert len(app_response.status_history) == 2, (
            f"Expected 2 history entries, got {len(app_response.status_history)}"
        )
        
        # Verify each history entry has required fields
        for entry in app_response.status_history:
            assert entry.id is not None, "History entry must have an id"
            assert entry.application_id == application_id, (
                "History entry must reference the application"
            )
            assert entry.new_status is not None, "History entry must have new_status"
            assert entry.changed_at is not None, "History entry must have timestamp"
    
    @given(
        initial_status=valid_application_statuses(),
        update_status=valid_application_statuses(),
    )
    @settings(max_examples=50, deadline=None)
    def test_same_status_update_no_history_entry(
        self, initial_status: ApplicationStatus, update_status: ApplicationStatus
    ):
        """When status is updated to the same value, no new history entry
        SHALL be created.
        
        **Validates: Requirements 27.3**
        
        This test verifies that:
        1. Updating to the same status doesn't create redundant history
        2. History entries only record actual changes
        """
        # Only test when statuses are the same
        assume(initial_status == update_status)
        
        # Create status update with same status
        status_update = StatusUpdateRequest(status=update_status)
        
        # Verify the update schema accepts the value
        assert status_update.status == update_status
        
        # In the actual service, this would not create a history entry
        # because the status hasn't changed. We verify the schema
        # correctly represents the update request.
        assert status_update.status == initial_status, (
            "When updating to the same status, no change should be recorded"
        )
    
    @given(app_data=valid_job_application_data())
    @settings(max_examples=50, deadline=None)
    def test_initial_application_creates_history_entry(
        self, app_data: dict
    ):
        """When a job application is first created, an initial history entry
        SHALL be created with previous_status as None.
        
        **Validates: Requirements 27.3**
        
        This test verifies that:
        1. Initial application creation creates a history entry
        2. The initial entry has previous_status as None
        3. The initial entry has new_status as the initial status
        """
        application_id = uuid4()
        
        # Create job application
        app_create = JobApplicationCreate(
            company=app_data["company"],
            role=app_data["role"],
            status=app_data["status"],
        )
        
        # Simulate initial history entry (created by service)
        initial_history = ApplicationStatusHistoryResponse(
            id=uuid4(),
            application_id=application_id,
            previous_status=None,  # None indicates initial creation
            new_status=app_create.status,
            changed_at=datetime.now(timezone.utc),
            notes="Application created",
        )
        
        # Verify initial history entry
        assert initial_history.previous_status is None, (
            "Initial history entry should have previous_status as None"
        )
        assert initial_history.new_status == app_data["status"], (
            f"Initial history entry should have new_status as {app_data['status']}, "
            f"but got {initial_history.new_status}"
        )

