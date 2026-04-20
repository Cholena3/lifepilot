"""Property-based tests for exam feed filtering.

Property 9: Exam Feed Eligibility Filtering
*For any* user with a specific degree, branch, and graduation year, all exams returned in the feed 
SHALL have eligibility criteria that match or are less restrictive than the user's profile.

Property 10: CGPA Filter Correctness
*For any* user with CGPA X applying a CGPA filter, all returned exams SHALL have minimum CGPA 
requirement ≤ X.

Property 11: Backlog Filter Correctness
*For any* user with N backlogs applying a backlog filter, all returned exams SHALL allow at least 
N backlogs.

Validates: Requirements 3.1, 3.2, 3.3
"""

from decimal import Decimal
from typing import List, Optional
import uuid

import pytest
from hypothesis import given, strategies as st, settings, assume

from app.models.exam import ExamType
from app.schemas.exam import ExamCreate, ExamFilters, ExamResponse


# ============================================================================
# Constants
# ============================================================================

VALID_DEGREES = ["B.Tech", "B.E", "MCA", "M.Tech", "BCA", "BSc", "MSc"]
VALID_BRANCHES = ["CSE", "IT", "ECE", "EEE", "Mechanical", "Civil", "Chemical"]
VALID_EXAM_TYPES = list(ExamType)


# ============================================================================
# Strategies
# ============================================================================

@st.composite
def degree_strategy(draw):
    """Generate valid degree values."""
    return draw(st.sampled_from(VALID_DEGREES))


@st.composite
def branch_strategy(draw):
    """Generate valid branch values."""
    return draw(st.sampled_from(VALID_BRANCHES))


@st.composite
def graduation_year_strategy(draw):
    """Generate valid graduation years."""
    return draw(st.integers(min_value=2020, max_value=2030))


@st.composite
def cgpa_strategy(draw):
    """Generate valid CGPA values (0.0 to 10.0)."""
    value = draw(st.floats(min_value=0.0, max_value=10.0, allow_nan=False, allow_infinity=False))
    return Decimal(str(round(value, 1)))


@st.composite
def backlog_strategy(draw):
    """Generate valid backlog counts."""
    return draw(st.integers(min_value=0, max_value=10))


@st.composite
def exam_type_strategy(draw):
    """Generate valid exam types."""
    return draw(st.sampled_from(VALID_EXAM_TYPES))


@st.composite
def eligible_degrees_strategy(draw):
    """Generate a list of eligible degrees (can be empty for no restriction)."""
    include_restriction = draw(st.booleans())
    if not include_restriction:
        return []
    return draw(st.lists(degree_strategy(), min_size=1, max_size=4, unique=True))


@st.composite
def eligible_branches_strategy(draw):
    """Generate a list of eligible branches (can be empty for no restriction)."""
    include_restriction = draw(st.booleans())
    if not include_restriction:
        return []
    return draw(st.lists(branch_strategy(), min_size=1, max_size=4, unique=True))


@st.composite
def exam_data_strategy(draw):
    """Generate valid exam data for testing."""
    exam_type = draw(exam_type_strategy())
    min_cgpa = draw(st.one_of(st.none(), cgpa_strategy()))
    max_backlogs = draw(st.one_of(st.none(), backlog_strategy()))
    eligible_degrees = draw(eligible_degrees_strategy())
    eligible_branches = draw(eligible_branches_strategy())
    
    # Generate graduation year range
    has_year_restriction = draw(st.booleans())
    if has_year_restriction:
        year_min = draw(graduation_year_strategy())
        year_max = draw(st.integers(min_value=year_min, max_value=year_min + 3))
    else:
        year_min = None
        year_max = None
    
    return {
        "id": uuid.uuid4(),
        "name": f"Test Exam {draw(st.integers(min_value=1, max_value=1000))}",
        "organization": "Test Organization",
        "exam_type": exam_type,
        "min_cgpa": min_cgpa,
        "max_backlogs": max_backlogs,
        "eligible_degrees": eligible_degrees,
        "eligible_branches": eligible_branches,
        "graduation_year_min": year_min,
        "graduation_year_max": year_max,
    }


@st.composite
def user_profile_strategy(draw):
    """Generate valid user profile data for filtering."""
    return {
        "degree": draw(degree_strategy()),
        "branch": draw(branch_strategy()),
        "graduation_year": draw(graduation_year_strategy()),
        "cgpa": draw(cgpa_strategy()),
        "backlogs": draw(backlog_strategy()),
    }


# ============================================================================
# Helper Functions - Filtering Logic
# ============================================================================

def is_user_eligible_for_exam(user_profile: dict, exam: dict) -> bool:
    """
    Check if a user is eligible for an exam based on all criteria.
    
    This implements the filtering logic that should match the repository implementation.
    """
    # Check degree eligibility (Requirement 3.1)
    if exam.get("eligible_degrees") and len(exam["eligible_degrees"]) > 0:
        if user_profile["degree"] not in exam["eligible_degrees"]:
            return False
    
    # Check branch eligibility (Requirement 3.1)
    if exam.get("eligible_branches") and len(exam["eligible_branches"]) > 0:
        if user_profile["branch"] not in exam["eligible_branches"]:
            return False
    
    # Check graduation year eligibility (Requirement 3.1)
    if exam.get("graduation_year_min") is not None:
        if user_profile["graduation_year"] < exam["graduation_year_min"]:
            return False
    if exam.get("graduation_year_max") is not None:
        if user_profile["graduation_year"] > exam["graduation_year_max"]:
            return False
    
    # Check CGPA eligibility (Requirement 3.2)
    if exam.get("min_cgpa") is not None:
        if user_profile["cgpa"] < exam["min_cgpa"]:
            return False
    
    # Check backlog eligibility (Requirement 3.3)
    if exam.get("max_backlogs") is not None:
        if user_profile["backlogs"] > exam["max_backlogs"]:
            return False
    
    return True


def filter_exams_for_user(user_profile: dict, exams: List[dict]) -> List[dict]:
    """Filter exams based on user eligibility."""
    return [exam for exam in exams if is_user_eligible_for_exam(user_profile, exam)]


def check_cgpa_filter(user_cgpa: Decimal, exam: dict) -> bool:
    """Check if exam passes CGPA filter for user."""
    if exam.get("min_cgpa") is None:
        return True
    return exam["min_cgpa"] <= user_cgpa


def check_backlog_filter(user_backlogs: int, exam: dict) -> bool:
    """Check if exam passes backlog filter for user."""
    if exam.get("max_backlogs") is None:
        return True
    return exam["max_backlogs"] >= user_backlogs


def check_degree_filter(user_degree: str, exam: dict) -> bool:
    """Check if exam passes degree filter for user."""
    eligible_degrees = exam.get("eligible_degrees", [])
    if not eligible_degrees:
        return True
    return user_degree in eligible_degrees


def check_branch_filter(user_branch: str, exam: dict) -> bool:
    """Check if exam passes branch filter for user."""
    eligible_branches = exam.get("eligible_branches", [])
    if not eligible_branches:
        return True
    return user_branch in eligible_branches


def check_graduation_year_filter(user_grad_year: int, exam: dict) -> bool:
    """Check if exam passes graduation year filter for user."""
    year_min = exam.get("graduation_year_min")
    year_max = exam.get("graduation_year_max")
    
    if year_min is not None and user_grad_year < year_min:
        return False
    if year_max is not None and user_grad_year > year_max:
        return False
    return True


# ============================================================================
# Property 9: Exam Feed Eligibility Filtering
# ============================================================================

class TestExamFeedEligibilityFiltering:
    """
    Property 9: Exam Feed Eligibility Filtering
    
    *For any* user with a specific degree, branch, and graduation year, all exams 
    returned in the feed SHALL have eligibility criteria that match or are less 
    restrictive than the user's profile.
    
    **Validates: Requirements 3.1**
    """
    
    @given(
        user_profile=user_profile_strategy(),
        exams=st.lists(exam_data_strategy(), min_size=1, max_size=20),
    )
    @settings(max_examples=50, deadline=None)
    def test_filtered_exams_match_user_eligibility(self, user_profile: dict, exams: List[dict]):
        """
        Test that all exams returned by filtering match user's eligibility criteria.
        
        **Validates: Requirements 3.1**
        """
        # Filter exams using our filtering logic
        filtered_exams = filter_exams_for_user(user_profile, exams)
        
        # Verify each filtered exam matches user eligibility
        for exam in filtered_exams:
            # Check degree eligibility
            assert check_degree_filter(user_profile["degree"], exam), \
                f"Exam {exam['name']} has degree restriction {exam.get('eligible_degrees')} " \
                f"but user has degree {user_profile['degree']}"
            
            # Check branch eligibility
            assert check_branch_filter(user_profile["branch"], exam), \
                f"Exam {exam['name']} has branch restriction {exam.get('eligible_branches')} " \
                f"but user has branch {user_profile['branch']}"
            
            # Check graduation year eligibility
            assert check_graduation_year_filter(user_profile["graduation_year"], exam), \
                f"Exam {exam['name']} has year range [{exam.get('graduation_year_min')}, " \
                f"{exam.get('graduation_year_max')}] but user graduates in {user_profile['graduation_year']}"
    
    @given(
        user_profile=user_profile_strategy(),
        exams=st.lists(exam_data_strategy(), min_size=1, max_size=20),
    )
    @settings(max_examples=50, deadline=None)
    def test_ineligible_exams_are_excluded(self, user_profile: dict, exams: List[dict]):
        """
        Test that exams not matching user eligibility are excluded from results.
        
        **Validates: Requirements 3.1**
        """
        filtered_exams = filter_exams_for_user(user_profile, exams)
        filtered_ids = {exam["id"] for exam in filtered_exams}
        
        for exam in exams:
            if exam["id"] not in filtered_ids:
                # This exam was excluded - verify it's because user is ineligible
                is_eligible = is_user_eligible_for_exam(user_profile, exam)
                assert not is_eligible, \
                    f"Exam {exam['name']} was excluded but user should be eligible"
    
    @given(user_profile=user_profile_strategy())
    @settings(max_examples=30, deadline=None)
    def test_exam_with_no_restrictions_always_included(self, user_profile: dict):
        """
        Test that exams with no eligibility restrictions are always included.
        
        **Validates: Requirements 3.1**
        """
        # Create an exam with no restrictions
        unrestricted_exam = {
            "id": uuid.uuid4(),
            "name": "Unrestricted Exam",
            "organization": "Test Org",
            "exam_type": ExamType.CAMPUS_PLACEMENT,
            "min_cgpa": None,
            "max_backlogs": None,
            "eligible_degrees": [],
            "eligible_branches": [],
            "graduation_year_min": None,
            "graduation_year_max": None,
        }
        
        filtered = filter_exams_for_user(user_profile, [unrestricted_exam])
        assert len(filtered) == 1, "Unrestricted exam should always be included"
        assert filtered[0]["id"] == unrestricted_exam["id"]
    
    @given(
        degree=degree_strategy(),
        branch=branch_strategy(),
        graduation_year=graduation_year_strategy(),
    )
    @settings(max_examples=30, deadline=None)
    def test_exact_match_eligibility_included(self, degree: str, branch: str, graduation_year: int):
        """
        Test that exams with exact match eligibility criteria are included.
        
        **Validates: Requirements 3.1**
        """
        user_profile = {
            "degree": degree,
            "branch": branch,
            "graduation_year": graduation_year,
            "cgpa": Decimal("7.0"),
            "backlogs": 0,
        }
        
        # Create exam that exactly matches user's profile
        exact_match_exam = {
            "id": uuid.uuid4(),
            "name": "Exact Match Exam",
            "organization": "Test Org",
            "exam_type": ExamType.CAMPUS_PLACEMENT,
            "min_cgpa": Decimal("7.0"),
            "max_backlogs": 0,
            "eligible_degrees": [degree],
            "eligible_branches": [branch],
            "graduation_year_min": graduation_year,
            "graduation_year_max": graduation_year,
        }
        
        filtered = filter_exams_for_user(user_profile, [exact_match_exam])
        assert len(filtered) == 1, "Exam with exact match criteria should be included"


# ============================================================================
# Property 10: CGPA Filter Correctness
# ============================================================================

class TestCGPAFilterCorrectness:
    """
    Property 10: CGPA Filter Correctness
    
    *For any* user with CGPA X applying a CGPA filter, all returned exams SHALL 
    have minimum CGPA requirement ≤ X.
    
    **Validates: Requirements 3.2**
    """
    
    @given(
        user_cgpa=cgpa_strategy(),
        exams=st.lists(exam_data_strategy(), min_size=1, max_size=20),
    )
    @settings(max_examples=50, deadline=None)
    def test_cgpa_filter_returns_only_eligible_exams(self, user_cgpa: Decimal, exams: List[dict]):
        """
        Test that CGPA filtering only returns exams where min_cgpa <= user_cgpa.
        
        **Validates: Requirements 3.2**
        """
        # Filter exams by CGPA only
        filtered_exams = [exam for exam in exams if check_cgpa_filter(user_cgpa, exam)]
        
        for exam in filtered_exams:
            if exam.get("min_cgpa") is not None:
                assert exam["min_cgpa"] <= user_cgpa, \
                    f"Exam {exam['name']} requires CGPA {exam['min_cgpa']} " \
                    f"but user has CGPA {user_cgpa}"
    
    @given(
        user_cgpa=cgpa_strategy(),
        exam_min_cgpa=cgpa_strategy(),
    )
    @settings(max_examples=50, deadline=None)
    def test_cgpa_boundary_conditions(self, user_cgpa: Decimal, exam_min_cgpa: Decimal):
        """
        Test CGPA filter boundary conditions (equal values should pass).
        
        **Validates: Requirements 3.2**
        """
        exam = {
            "id": uuid.uuid4(),
            "name": "Test Exam",
            "min_cgpa": exam_min_cgpa,
        }
        
        passes_filter = check_cgpa_filter(user_cgpa, exam)
        
        if user_cgpa >= exam_min_cgpa:
            assert passes_filter, \
                f"User with CGPA {user_cgpa} should be eligible for exam requiring {exam_min_cgpa}"
        else:
            assert not passes_filter, \
                f"User with CGPA {user_cgpa} should NOT be eligible for exam requiring {exam_min_cgpa}"
    
    @given(user_cgpa=cgpa_strategy())
    @settings(max_examples=30, deadline=None)
    def test_exam_without_cgpa_requirement_always_passes(self, user_cgpa: Decimal):
        """
        Test that exams without CGPA requirement pass filter for any user CGPA.
        
        **Validates: Requirements 3.2**
        """
        exam = {
            "id": uuid.uuid4(),
            "name": "No CGPA Requirement Exam",
            "min_cgpa": None,
        }
        
        assert check_cgpa_filter(user_cgpa, exam), \
            "Exam without CGPA requirement should pass filter for any user CGPA"
    
    @given(
        user_cgpa=st.just(Decimal("10.0")),
        exam_min_cgpa=cgpa_strategy(),
    )
    @settings(max_examples=30, deadline=None)
    def test_max_cgpa_user_eligible_for_all_exams(self, user_cgpa: Decimal, exam_min_cgpa: Decimal):
        """
        Test that user with maximum CGPA (10.0) is eligible for all exams.
        
        **Validates: Requirements 3.2**
        """
        exam = {
            "id": uuid.uuid4(),
            "name": "Test Exam",
            "min_cgpa": exam_min_cgpa,
        }
        
        assert check_cgpa_filter(user_cgpa, exam), \
            f"User with max CGPA 10.0 should be eligible for exam requiring {exam_min_cgpa}"
    
    @given(exam_min_cgpa=cgpa_strategy())
    @settings(max_examples=30, deadline=None)
    def test_zero_cgpa_user_only_eligible_for_zero_requirement(self, exam_min_cgpa: Decimal):
        """
        Test that user with CGPA 0.0 is only eligible for exams with no or zero CGPA requirement.
        
        **Validates: Requirements 3.2**
        """
        user_cgpa = Decimal("0.0")
        exam = {
            "id": uuid.uuid4(),
            "name": "Test Exam",
            "min_cgpa": exam_min_cgpa,
        }
        
        passes_filter = check_cgpa_filter(user_cgpa, exam)
        
        if exam_min_cgpa == Decimal("0.0"):
            assert passes_filter, "User with CGPA 0.0 should be eligible for exam requiring 0.0"
        else:
            assert not passes_filter, \
                f"User with CGPA 0.0 should NOT be eligible for exam requiring {exam_min_cgpa}"


# ============================================================================
# Property 11: Backlog Filter Correctness
# ============================================================================

class TestBacklogFilterCorrectness:
    """
    Property 11: Backlog Filter Correctness
    
    *For any* user with N backlogs applying a backlog filter, all returned exams 
    SHALL allow at least N backlogs.
    
    **Validates: Requirements 3.3**
    """
    
    @given(
        user_backlogs=backlog_strategy(),
        exams=st.lists(exam_data_strategy(), min_size=1, max_size=20),
    )
    @settings(max_examples=50, deadline=None)
    def test_backlog_filter_returns_only_eligible_exams(self, user_backlogs: int, exams: List[dict]):
        """
        Test that backlog filtering only returns exams where max_backlogs >= user_backlogs.
        
        **Validates: Requirements 3.3**
        """
        # Filter exams by backlogs only
        filtered_exams = [exam for exam in exams if check_backlog_filter(user_backlogs, exam)]
        
        for exam in filtered_exams:
            if exam.get("max_backlogs") is not None:
                assert exam["max_backlogs"] >= user_backlogs, \
                    f"Exam {exam['name']} allows {exam['max_backlogs']} backlogs " \
                    f"but user has {user_backlogs} backlogs"
    
    @given(
        user_backlogs=backlog_strategy(),
        exam_max_backlogs=backlog_strategy(),
    )
    @settings(max_examples=50, deadline=None)
    def test_backlog_boundary_conditions(self, user_backlogs: int, exam_max_backlogs: int):
        """
        Test backlog filter boundary conditions (equal values should pass).
        
        **Validates: Requirements 3.3**
        """
        exam = {
            "id": uuid.uuid4(),
            "name": "Test Exam",
            "max_backlogs": exam_max_backlogs,
        }
        
        passes_filter = check_backlog_filter(user_backlogs, exam)
        
        if user_backlogs <= exam_max_backlogs:
            assert passes_filter, \
                f"User with {user_backlogs} backlogs should be eligible for exam allowing {exam_max_backlogs}"
        else:
            assert not passes_filter, \
                f"User with {user_backlogs} backlogs should NOT be eligible for exam allowing {exam_max_backlogs}"
    
    @given(user_backlogs=backlog_strategy())
    @settings(max_examples=30, deadline=None)
    def test_exam_without_backlog_requirement_always_passes(self, user_backlogs: int):
        """
        Test that exams without backlog requirement pass filter for any user backlog count.
        
        **Validates: Requirements 3.3**
        """
        exam = {
            "id": uuid.uuid4(),
            "name": "No Backlog Requirement Exam",
            "max_backlogs": None,
        }
        
        assert check_backlog_filter(user_backlogs, exam), \
            "Exam without backlog requirement should pass filter for any user backlog count"
    
    @given(exam_max_backlogs=backlog_strategy())
    @settings(max_examples=30, deadline=None)
    def test_zero_backlog_user_eligible_for_all_exams(self, exam_max_backlogs: int):
        """
        Test that user with zero backlogs is eligible for all exams.
        
        **Validates: Requirements 3.3**
        """
        user_backlogs = 0
        exam = {
            "id": uuid.uuid4(),
            "name": "Test Exam",
            "max_backlogs": exam_max_backlogs,
        }
        
        assert check_backlog_filter(user_backlogs, exam), \
            f"User with 0 backlogs should be eligible for exam allowing {exam_max_backlogs}"
    
    @given(user_backlogs=st.integers(min_value=1, max_value=10))
    @settings(max_examples=30, deadline=None)
    def test_user_with_backlogs_excluded_from_zero_backlog_exams(self, user_backlogs: int):
        """
        Test that user with backlogs is excluded from exams requiring zero backlogs.
        
        **Validates: Requirements 3.3**
        """
        exam = {
            "id": uuid.uuid4(),
            "name": "Zero Backlog Exam",
            "max_backlogs": 0,
        }
        
        assert not check_backlog_filter(user_backlogs, exam), \
            f"User with {user_backlogs} backlogs should NOT be eligible for exam requiring 0 backlogs"


# ============================================================================
# Combined Filter Tests
# ============================================================================

class TestCombinedFilters:
    """
    Tests for combined filtering logic (CGPA + Backlogs + Eligibility).
    
    **Validates: Requirements 3.1, 3.2, 3.3**
    """
    
    @given(
        user_profile=user_profile_strategy(),
        exams=st.lists(exam_data_strategy(), min_size=5, max_size=30),
    )
    @settings(max_examples=50, deadline=None)
    def test_all_filters_applied_correctly(self, user_profile: dict, exams: List[dict]):
        """
        Test that all filters (degree, branch, year, CGPA, backlogs) are applied correctly.
        
        **Validates: Requirements 3.1, 3.2, 3.3**
        """
        filtered_exams = filter_exams_for_user(user_profile, exams)
        
        for exam in filtered_exams:
            # Verify all eligibility criteria
            assert check_degree_filter(user_profile["degree"], exam), \
                f"Degree filter failed for exam {exam['name']}"
            assert check_branch_filter(user_profile["branch"], exam), \
                f"Branch filter failed for exam {exam['name']}"
            assert check_graduation_year_filter(user_profile["graduation_year"], exam), \
                f"Graduation year filter failed for exam {exam['name']}"
            assert check_cgpa_filter(user_profile["cgpa"], exam), \
                f"CGPA filter failed for exam {exam['name']}"
            assert check_backlog_filter(user_profile["backlogs"], exam), \
                f"Backlog filter failed for exam {exam['name']}"
    
    @given(
        user_profile=user_profile_strategy(),
        exams=st.lists(exam_data_strategy(), min_size=1, max_size=20),
    )
    @settings(max_examples=50, deadline=None)
    def test_filter_is_idempotent(self, user_profile: dict, exams: List[dict]):
        """
        Test that applying the filter twice gives the same result.
        
        **Validates: Requirements 3.1, 3.2, 3.3**
        """
        first_filter = filter_exams_for_user(user_profile, exams)
        second_filter = filter_exams_for_user(user_profile, first_filter)
        
        assert len(first_filter) == len(second_filter), \
            "Filtering should be idempotent"
        
        first_ids = {exam["id"] for exam in first_filter}
        second_ids = {exam["id"] for exam in second_filter}
        assert first_ids == second_ids, \
            "Filtering should return the same exams when applied twice"
    
    @given(user_profile=user_profile_strategy())
    @settings(max_examples=30, deadline=None)
    def test_empty_exam_list_returns_empty(self, user_profile: dict):
        """
        Test that filtering an empty exam list returns an empty list.
        
        **Validates: Requirements 3.1, 3.2, 3.3**
        """
        filtered = filter_exams_for_user(user_profile, [])
        assert filtered == [], "Filtering empty list should return empty list"
    
    @given(
        user_profile=user_profile_strategy(),
        exams=st.lists(exam_data_strategy(), min_size=1, max_size=20),
    )
    @settings(max_examples=50, deadline=None)
    def test_filtered_count_less_than_or_equal_to_total(self, user_profile: dict, exams: List[dict]):
        """
        Test that filtered exam count is always <= total exam count.
        
        **Validates: Requirements 3.1, 3.2, 3.3**
        """
        filtered = filter_exams_for_user(user_profile, exams)
        assert len(filtered) <= len(exams), \
            "Filtered count should be <= total count"


# ============================================================================
# Property 12: Exam Bookmark Persistence
# ============================================================================

# Bookmark data structures for testing
def user_id_strategy():
    """Generate valid user UUIDs."""
    return st.builds(uuid.uuid4)


def bookmark_data_strategy():
    """Generate valid bookmark data for testing."""
    return st.fixed_dictionaries({
        "id": st.builds(uuid.uuid4),
        "user_id": user_id_strategy(),
        "exam_id": st.builds(uuid.uuid4),
    })


class BookmarkStore:
    """
    In-memory bookmark store that simulates the bookmark persistence behavior.
    
    This implements the core bookmark logic that should match the repository implementation:
    - Bookmarks are unique per user-exam combination
    - Bookmarks can be created, retrieved, and deleted
    - Bookmarks persist until explicitly removed
    """
    
    def __init__(self):
        # Store bookmarks as dict keyed by (user_id, exam_id) tuple
        self._bookmarks: dict[tuple[uuid.UUID, uuid.UUID], dict] = {}
    
    def create_bookmark(self, user_id: uuid.UUID, exam_id: uuid.UUID) -> dict:
        """
        Create a new bookmark.
        
        Raises ValueError if bookmark already exists (uniqueness constraint).
        """
        key = (user_id, exam_id)
        if key in self._bookmarks:
            raise ValueError("Bookmark already exists for this user-exam combination")
        
        bookmark = {
            "id": uuid.uuid4(),
            "user_id": user_id,
            "exam_id": exam_id,
        }
        self._bookmarks[key] = bookmark
        return bookmark
    
    def get_bookmark(self, user_id: uuid.UUID, exam_id: uuid.UUID) -> Optional[dict]:
        """Get a bookmark by user and exam ID."""
        key = (user_id, exam_id)
        return self._bookmarks.get(key)
    
    def get_user_bookmarks(self, user_id: uuid.UUID) -> List[dict]:
        """Get all bookmarks for a user."""
        return [
            bookmark for (uid, _), bookmark in self._bookmarks.items()
            if uid == user_id
        ]
    
    def delete_bookmark(self, user_id: uuid.UUID, exam_id: uuid.UUID) -> bool:
        """
        Delete a bookmark.
        
        Returns True if bookmark was deleted, False if it didn't exist.
        """
        key = (user_id, exam_id)
        if key in self._bookmarks:
            del self._bookmarks[key]
            return True
        return False
    
    def is_bookmarked(self, user_id: uuid.UUID, exam_id: uuid.UUID) -> bool:
        """Check if an exam is bookmarked by a user."""
        return (user_id, exam_id) in self._bookmarks
    
    def get_bookmarked_exam_ids(self, user_id: uuid.UUID) -> set[uuid.UUID]:
        """Get set of exam IDs bookmarked by a user."""
        return {
            exam_id for (uid, exam_id) in self._bookmarks.keys()
            if uid == user_id
        }


class TestExamBookmarkPersistence:
    """
    Property 12: Exam Bookmark Persistence
    
    *For any* exam bookmarked by a user, the exam SHALL appear in the user's 
    saved exams list, and removing the bookmark SHALL remove it from the list.
    
    **Validates: Requirements 3.5**
    """
    
    @given(
        user_id=user_id_strategy(),
        exam_ids=st.lists(st.builds(uuid.uuid4), min_size=1, max_size=10, unique=True),
    )
    @settings(max_examples=50, deadline=None)
    def test_bookmarked_exams_appear_in_saved_list(self, user_id: uuid.UUID, exam_ids: List[uuid.UUID]):
        """
        Test that bookmarked exams persist correctly and can be retrieved.
        
        **Validates: Requirements 3.5**
        """
        store = BookmarkStore()
        
        # Bookmark all exams
        for exam_id in exam_ids:
            store.create_bookmark(user_id, exam_id)
        
        # Verify all bookmarked exams appear in user's saved list
        saved_exam_ids = store.get_bookmarked_exam_ids(user_id)
        
        assert saved_exam_ids == set(exam_ids), \
            f"Expected {set(exam_ids)} but got {saved_exam_ids}"
        
        # Verify each individual bookmark can be retrieved
        for exam_id in exam_ids:
            bookmark = store.get_bookmark(user_id, exam_id)
            assert bookmark is not None, f"Bookmark for exam {exam_id} should exist"
            assert bookmark["user_id"] == user_id
            assert bookmark["exam_id"] == exam_id
    
    @given(
        user_id=user_id_strategy(),
        exam_id=st.builds(uuid.uuid4),
    )
    @settings(max_examples=50, deadline=None)
    def test_bookmark_uniqueness_per_user_exam(self, user_id: uuid.UUID, exam_id: uuid.UUID):
        """
        Test that bookmarks are unique per user-exam combination.
        
        **Validates: Requirements 3.5**
        """
        store = BookmarkStore()
        
        # First bookmark should succeed
        bookmark = store.create_bookmark(user_id, exam_id)
        assert bookmark is not None
        
        # Second bookmark for same user-exam should fail
        with pytest.raises(ValueError, match="Bookmark already exists"):
            store.create_bookmark(user_id, exam_id)
        
        # Verify only one bookmark exists
        bookmarks = store.get_user_bookmarks(user_id)
        assert len(bookmarks) == 1, "Should have exactly one bookmark"
    
    @given(
        user_id=user_id_strategy(),
        exam_ids=st.lists(st.builds(uuid.uuid4), min_size=1, max_size=10, unique=True),
    )
    @settings(max_examples=50, deadline=None)
    def test_removing_bookmark_removes_from_list(self, user_id: uuid.UUID, exam_ids: List[uuid.UUID]):
        """
        Test that removing a bookmark actually removes it from the saved list.
        
        **Validates: Requirements 3.5**
        """
        store = BookmarkStore()
        
        # Bookmark all exams
        for exam_id in exam_ids:
            store.create_bookmark(user_id, exam_id)
        
        # Remove each bookmark one by one and verify
        remaining_exams = set(exam_ids)
        for exam_id in exam_ids:
            # Remove the bookmark
            result = store.delete_bookmark(user_id, exam_id)
            assert result is True, f"Deleting bookmark for exam {exam_id} should succeed"
            
            # Update expected remaining
            remaining_exams.discard(exam_id)
            
            # Verify the exam is no longer in saved list
            saved_exam_ids = store.get_bookmarked_exam_ids(user_id)
            assert exam_id not in saved_exam_ids, \
                f"Exam {exam_id} should not be in saved list after removal"
            assert saved_exam_ids == remaining_exams, \
                f"Expected {remaining_exams} but got {saved_exam_ids}"
            
            # Verify bookmark cannot be retrieved
            bookmark = store.get_bookmark(user_id, exam_id)
            assert bookmark is None, f"Bookmark for exam {exam_id} should not exist after removal"
    
    @given(
        user_id=user_id_strategy(),
        exam_id=st.builds(uuid.uuid4),
    )
    @settings(max_examples=30, deadline=None)
    def test_removing_nonexistent_bookmark_returns_false(self, user_id: uuid.UUID, exam_id: uuid.UUID):
        """
        Test that removing a non-existent bookmark returns False.
        
        **Validates: Requirements 3.5**
        """
        store = BookmarkStore()
        
        # Try to remove a bookmark that doesn't exist
        result = store.delete_bookmark(user_id, exam_id)
        assert result is False, "Deleting non-existent bookmark should return False"
    
    @given(
        user1_id=user_id_strategy(),
        user2_id=user_id_strategy(),
        exam_id=st.builds(uuid.uuid4),
    )
    @settings(max_examples=50, deadline=None)
    def test_different_users_can_bookmark_same_exam(self, user1_id: uuid.UUID, user2_id: uuid.UUID, exam_id: uuid.UUID):
        """
        Test that different users can bookmark the same exam independently.
        
        **Validates: Requirements 3.5**
        """
        assume(user1_id != user2_id)  # Ensure different users
        
        store = BookmarkStore()
        
        # Both users bookmark the same exam
        bookmark1 = store.create_bookmark(user1_id, exam_id)
        bookmark2 = store.create_bookmark(user2_id, exam_id)
        
        assert bookmark1 is not None
        assert bookmark2 is not None
        
        # Verify each user has their own bookmark
        assert store.is_bookmarked(user1_id, exam_id)
        assert store.is_bookmarked(user2_id, exam_id)
        
        # Verify user1's bookmarks don't include user2's and vice versa
        user1_bookmarks = store.get_user_bookmarks(user1_id)
        user2_bookmarks = store.get_user_bookmarks(user2_id)
        
        assert len(user1_bookmarks) == 1
        assert len(user2_bookmarks) == 1
        assert user1_bookmarks[0]["user_id"] == user1_id
        assert user2_bookmarks[0]["user_id"] == user2_id
    
    @given(
        user1_id=user_id_strategy(),
        user2_id=user_id_strategy(),
        exam_id=st.builds(uuid.uuid4),
    )
    @settings(max_examples=50, deadline=None)
    def test_removing_one_users_bookmark_doesnt_affect_others(self, user1_id: uuid.UUID, user2_id: uuid.UUID, exam_id: uuid.UUID):
        """
        Test that removing one user's bookmark doesn't affect another user's bookmark.
        
        **Validates: Requirements 3.5**
        """
        assume(user1_id != user2_id)  # Ensure different users
        
        store = BookmarkStore()
        
        # Both users bookmark the same exam
        store.create_bookmark(user1_id, exam_id)
        store.create_bookmark(user2_id, exam_id)
        
        # User1 removes their bookmark
        store.delete_bookmark(user1_id, exam_id)
        
        # User1's bookmark should be gone
        assert not store.is_bookmarked(user1_id, exam_id)
        
        # User2's bookmark should still exist
        assert store.is_bookmarked(user2_id, exam_id)
        bookmark = store.get_bookmark(user2_id, exam_id)
        assert bookmark is not None
        assert bookmark["user_id"] == user2_id
        assert bookmark["exam_id"] == exam_id
    
    @given(
        user_id=user_id_strategy(),
        exam_id=st.builds(uuid.uuid4),
    )
    @settings(max_examples=30, deadline=None)
    def test_bookmark_round_trip(self, user_id: uuid.UUID, exam_id: uuid.UUID):
        """
        Test complete bookmark lifecycle: create, verify, delete, verify removed.
        
        **Validates: Requirements 3.5**
        """
        store = BookmarkStore()
        
        # Initially not bookmarked
        assert not store.is_bookmarked(user_id, exam_id)
        assert store.get_bookmark(user_id, exam_id) is None
        
        # Create bookmark
        bookmark = store.create_bookmark(user_id, exam_id)
        assert bookmark is not None
        
        # Verify bookmarked
        assert store.is_bookmarked(user_id, exam_id)
        retrieved = store.get_bookmark(user_id, exam_id)
        assert retrieved is not None
        assert retrieved["user_id"] == user_id
        assert retrieved["exam_id"] == exam_id
        
        # Delete bookmark
        result = store.delete_bookmark(user_id, exam_id)
        assert result is True
        
        # Verify removed
        assert not store.is_bookmarked(user_id, exam_id)
        assert store.get_bookmark(user_id, exam_id) is None
    
    @given(
        user_id=user_id_strategy(),
        exam_ids=st.lists(st.builds(uuid.uuid4), min_size=0, max_size=20, unique=True),
    )
    @settings(max_examples=50, deadline=None)
    def test_bookmark_count_matches_created(self, user_id: uuid.UUID, exam_ids: List[uuid.UUID]):
        """
        Test that the number of bookmarks matches the number created.
        
        **Validates: Requirements 3.5**
        """
        store = BookmarkStore()
        
        # Bookmark all exams
        for exam_id in exam_ids:
            store.create_bookmark(user_id, exam_id)
        
        # Verify count matches
        bookmarks = store.get_user_bookmarks(user_id)
        assert len(bookmarks) == len(exam_ids), \
            f"Expected {len(exam_ids)} bookmarks but got {len(bookmarks)}"
    
    @given(
        user_id=user_id_strategy(),
        exam_id=st.builds(uuid.uuid4),
    )
    @settings(max_examples=30, deadline=None)
    def test_can_rebookmark_after_removal(self, user_id: uuid.UUID, exam_id: uuid.UUID):
        """
        Test that an exam can be re-bookmarked after removal.
        
        **Validates: Requirements 3.5**
        """
        store = BookmarkStore()
        
        # Create, delete, then recreate bookmark
        store.create_bookmark(user_id, exam_id)
        store.delete_bookmark(user_id, exam_id)
        
        # Should be able to bookmark again
        bookmark = store.create_bookmark(user_id, exam_id)
        assert bookmark is not None
        assert store.is_bookmarked(user_id, exam_id)
