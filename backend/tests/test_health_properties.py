"""Property-based tests for health module.

Uses Hypothesis to verify universal properties across all valid inputs.

**Validates: Requirements 14.1**
"""

import string
from datetime import datetime, timezone, date
from uuid import uuid4
from unittest.mock import AsyncMock, MagicMock

import pytest
from hypothesis import given, strategies as st, settings, assume
from pydantic import ValidationError

from app.schemas.health import (
    HealthRecordCategory,
    HealthRecordCreate,
    HealthRecordUpdate,
    HealthRecordResponse,
    HealthRecordFilters,
)


# ============================================================================
# Hypothesis Strategies for Health Record Data
# ============================================================================

@st.composite
def valid_health_categories(draw):
    """Generate valid health record categories.
    
    Valid categories are: prescription, lab_report, scan, vaccine, insurance
    """
    return draw(st.sampled_from(HealthRecordCategory.ALL))


@st.composite
def invalid_health_categories(draw):
    """Generate invalid health record categories.
    
    These are strings that are NOT in the valid category list.
    """
    invalid_categories = [
        "invalid",
        "medical",
        "report",
        "document",
        "health",
        "record",
        "test",
        "checkup",
        "diagnosis",
        "treatment",
        "medication",
        "PRESCRIPTION",  # Case-sensitive - uppercase should be invalid
        "Lab_Report",    # Case-sensitive - mixed case should be invalid
        "SCAN",          # Case-sensitive - uppercase should be invalid
        "",              # Empty string
        " ",             # Whitespace
        "prescription ",  # Trailing space
        " prescription",  # Leading space
    ]
    return draw(st.sampled_from(invalid_categories))


@st.composite
def valid_health_record_titles(draw):
    """Generate valid health record titles (1-255 characters)."""
    chars = string.ascii_letters + string.digits + " -_."
    length = draw(st.integers(min_value=1, max_value=100))
    
    # Start with a letter
    first_char = draw(st.sampled_from(string.ascii_letters))
    
    if length == 1:
        return first_char
    
    rest = draw(st.text(alphabet=chars, min_size=length - 1, max_size=length - 1))
    title = first_char + rest
    
    # Clean up consecutive spaces
    while "  " in title:
        title = title.replace("  ", " ")
    
    return title.strip()[:255] or first_char


@st.composite
def valid_content_types(draw):
    """Generate valid MIME content types for health records."""
    return draw(st.sampled_from([
        "application/pdf",
        "image/jpeg",
        "image/png",
        "application/msword",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ]))


@st.composite
def valid_file_sizes(draw):
    """Generate valid file sizes (positive integers)."""
    return draw(st.integers(min_value=1, max_value=100_000_000))  # Up to 100MB


@st.composite
def valid_health_record_dates(draw):
    """Generate valid health record dates."""
    today = date.today()
    min_date = date(2000, 1, 1)  # Reasonable minimum date for health records
    return draw(st.dates(min_value=min_date, max_value=today))


@st.composite
def valid_health_record_create_data(draw):
    """Generate valid health record creation data."""
    return {
        "category": draw(valid_health_categories()),
        "title": draw(valid_health_record_titles()),
        "content_type": draw(valid_content_types()),
        "file_size": draw(valid_file_sizes()),
        "record_date": draw(st.one_of(st.none(), valid_health_record_dates())),
        "doctor_name": draw(st.one_of(st.none(), valid_health_record_titles())),
        "hospital_name": draw(st.one_of(st.none(), valid_health_record_titles())),
    }


# ============================================================================
# Property 30: Health Record Categorization
# ============================================================================

class TestHealthRecordCategorizationProperty:
    """Property 30: Health Record Categorization.
    
    **Validates: Requirements 14.1**
    
    For any health record uploaded with category C (prescription, lab report, scan,
    vaccine, or insurance), the record SHALL be stored with that category and
    retrievable by filtering on C.
    """
    
    @given(category=valid_health_categories())
    @settings(max_examples=20, deadline=None)
    def test_valid_categories_are_accepted(self, category: str):
        """For any valid category C, creating a health record with category C
        SHALL succeed.
        
        **Validates: Requirements 14.1**
        
        This test verifies that:
        1. All valid categories (prescription, lab_report, scan, vaccine, insurance)
           are accepted by the schema
        2. The category is correctly stored in the created record
        """
        # Create health record with the valid category
        health_record = HealthRecordCreate(
            category=category,
            title="Test Health Record",
            content_type="application/pdf",
            file_size=1024,
        )
        
        # Verify the category was accepted and stored correctly
        assert health_record.category == category, (
            f"Category should be '{category}', got '{health_record.category}'"
        )
    
    @given(invalid_category=invalid_health_categories())
    @settings(max_examples=20, deadline=None)
    def test_invalid_categories_are_rejected(self, invalid_category: str):
        """For any invalid category, creating a health record SHALL fail
        with a validation error.
        
        **Validates: Requirements 14.1**
        
        This test verifies that:
        1. Invalid categories are rejected by the schema
        2. A validation error is raised with appropriate message
        """
        with pytest.raises(ValidationError) as exc_info:
            HealthRecordCreate(
                category=invalid_category,
                title="Test Health Record",
                content_type="application/pdf",
                file_size=1024,
            )
        
        # Verify the error message mentions category validation
        error_str = str(exc_info.value)
        assert "category" in error_str.lower() or "Category must be one of" in error_str, (
            f"Error should mention category validation, got: {error_str}"
        )
    
    @given(record_data=valid_health_record_create_data())
    @settings(max_examples=20, deadline=None)
    def test_category_preserved_through_schema_round_trip(self, record_data: dict):
        """For any valid health record data with category C, creating the record
        and converting to response SHALL preserve the category.
        
        **Validates: Requirements 14.1**
        
        This test verifies that:
        1. Category is preserved when creating a HealthRecordCreate
        2. Category is preserved when converting to HealthRecordResponse
        3. The round-trip maintains data integrity
        """
        user_id = uuid4()
        record_id = uuid4()
        original_category = record_data["category"]
        
        # Create health record using the schema
        create_data = HealthRecordCreate(**record_data)
        
        # Verify category is preserved in create schema
        assert create_data.category == original_category, (
            f"Category should be '{original_category}' in create schema, "
            f"got '{create_data.category}'"
        )
        
        # Simulate creating a response (as would happen after database save)
        response = HealthRecordResponse(
            id=record_id,
            user_id=user_id,
            category=create_data.category,
            title=create_data.title,
            file_path=f"health_records/{user_id}/{record_id}.pdf",
            content_type=create_data.content_type,
            file_size=create_data.file_size,
            family_member_id=create_data.family_member_id,
            record_date=create_data.record_date,
            doctor_name=create_data.doctor_name,
            hospital_name=create_data.hospital_name,
            notes=create_data.notes,
            ocr_text=None,
            extracted_data=None,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        
        # Verify category is preserved in response
        assert response.category == original_category, (
            f"Category should be '{original_category}' in response, "
            f"got '{response.category}'"
        )
    
    @given(category=valid_health_categories())
    @settings(max_examples=20, deadline=None)
    def test_category_filter_accepts_valid_categories(self, category: str):
        """For any valid category C, filtering health records by C SHALL be accepted.
        
        **Validates: Requirements 14.1**
        
        This test verifies that:
        1. Valid categories can be used in filter schemas
        2. The filter correctly stores the category for querying
        """
        # Create filter with the valid category
        filters = HealthRecordFilters(category=category)
        
        # Verify the category was accepted
        assert filters.category == category, (
            f"Filter category should be '{category}', got '{filters.category}'"
        )
    
    @given(invalid_category=invalid_health_categories())
    @settings(max_examples=20, deadline=None)
    def test_category_filter_rejects_invalid_categories(self, invalid_category: str):
        """For any invalid category, filtering health records SHALL fail
        with a validation error.
        
        **Validates: Requirements 14.1**
        
        This test verifies that:
        1. Invalid categories are rejected in filter schemas
        2. A validation error is raised
        """
        with pytest.raises(ValidationError) as exc_info:
            HealthRecordFilters(category=invalid_category)
        
        # Verify the error mentions category validation
        error_str = str(exc_info.value)
        assert "category" in error_str.lower() or "Category must be one of" in error_str, (
            f"Error should mention category validation, got: {error_str}"
        )
    
    @given(category=valid_health_categories())
    @settings(max_examples=20, deadline=None)
    def test_category_update_accepts_valid_categories(self, category: str):
        """For any valid category C, updating a health record to category C
        SHALL be accepted.
        
        **Validates: Requirements 14.1**
        
        This test verifies that:
        1. Valid categories can be used in update schemas
        2. The update correctly stores the new category
        """
        # Create update with the valid category
        update_data = HealthRecordUpdate(category=category)
        
        # Verify the category was accepted
        assert update_data.category == category, (
            f"Update category should be '{category}', got '{update_data.category}'"
        )
    
    @given(invalid_category=invalid_health_categories())
    @settings(max_examples=20, deadline=None)
    def test_category_update_rejects_invalid_categories(self, invalid_category: str):
        """For any invalid category, updating a health record SHALL fail
        with a validation error.
        
        **Validates: Requirements 14.1**
        
        This test verifies that:
        1. Invalid categories are rejected in update schemas
        2. A validation error is raised
        """
        with pytest.raises(ValidationError) as exc_info:
            HealthRecordUpdate(category=invalid_category)
        
        # Verify the error mentions category validation
        error_str = str(exc_info.value)
        assert "category" in error_str.lower() or "Category must be one of" in error_str, (
            f"Error should mention category validation, got: {error_str}"
        )
    
    def test_all_valid_categories_are_defined(self):
        """Verify that all expected categories are defined in HealthRecordCategory.
        
        **Validates: Requirements 14.1**
        
        This test verifies that:
        1. All five required categories are defined
        2. No extra categories are present
        """
        expected_categories = {"prescription", "lab_report", "scan", "vaccine", "insurance"}
        actual_categories = set(HealthRecordCategory.ALL)
        
        assert actual_categories == expected_categories, (
            f"Expected categories {expected_categories}, got {actual_categories}"
        )
    
    @given(
        category1=valid_health_categories(),
        category2=valid_health_categories(),
    )
    @settings(max_examples=20, deadline=None)
    def test_category_can_be_updated_to_any_valid_category(
        self,
        category1: str,
        category2: str,
    ):
        """For any health record with category C1, updating to any valid category C2
        SHALL succeed.
        
        **Validates: Requirements 14.1**
        
        This test verifies that:
        1. A health record can be created with any valid category
        2. The category can be updated to any other valid category
        3. Both the original and updated categories are preserved correctly
        """
        user_id = uuid4()
        record_id = uuid4()
        
        # Create initial health record with category1
        create_data = HealthRecordCreate(
            category=category1,
            title="Test Health Record",
            content_type="application/pdf",
            file_size=1024,
        )
        
        assert create_data.category == category1, (
            f"Initial category should be '{category1}', got '{create_data.category}'"
        )
        
        # Create update to change to category2
        update_data = HealthRecordUpdate(category=category2)
        
        assert update_data.category == category2, (
            f"Update category should be '{category2}', got '{update_data.category}'"
        )
        
        # Simulate the updated response
        response = HealthRecordResponse(
            id=record_id,
            user_id=user_id,
            category=update_data.category,  # Updated category
            title=create_data.title,
            file_path=f"health_records/{user_id}/{record_id}.pdf",
            content_type=create_data.content_type,
            file_size=create_data.file_size,
            family_member_id=None,
            record_date=None,
            doctor_name=None,
            hospital_name=None,
            notes=None,
            ocr_text=None,
            extracted_data=None,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        
        # Verify the updated category is preserved
        assert response.category == category2, (
            f"Response category should be '{category2}' after update, "
            f"got '{response.category}'"
        )
