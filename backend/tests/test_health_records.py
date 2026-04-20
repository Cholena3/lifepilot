"""Tests for health record management endpoints.

Validates: Requirements 14.1, 14.2, 14.5
"""

import pytest
from datetime import date
from uuid import uuid4

from app.schemas.health import (
    HealthRecordCategory,
    HealthRecordCreate,
    HealthRecordUpdate,
    FamilyMemberCreate,
    FamilyMemberUpdate,
)


class TestHealthRecordCategories:
    """Tests for health record category validation."""
    
    def test_valid_categories(self):
        """Test that all expected categories are defined.
        
        Validates: Requirements 14.1
        """
        expected_categories = ["prescription", "lab_report", "scan", "vaccine", "insurance"]
        assert HealthRecordCategory.ALL == expected_categories
    
    def test_category_validation_accepts_valid(self):
        """Test that valid categories are accepted in schema.
        
        Validates: Requirements 14.1
        """
        for category in HealthRecordCategory.ALL:
            data = HealthRecordCreate(
                category=category,
                title="Test Record",
                content_type="application/pdf",
                file_size=1024,
            )
            assert data.category == category
    
    def test_category_validation_rejects_invalid(self):
        """Test that invalid categories are rejected.
        
        Validates: Requirements 14.1
        """
        with pytest.raises(ValueError) as exc_info:
            HealthRecordCreate(
                category="invalid_category",
                title="Test Record",
                content_type="application/pdf",
                file_size=1024,
            )
        assert "Category must be one of" in str(exc_info.value)


class TestFamilyMemberSchemas:
    """Tests for family member schema validation."""
    
    def test_family_member_create_valid(self):
        """Test creating a valid family member.
        
        Validates: Requirements 14.2
        """
        data = FamilyMemberCreate(
            name="John Doe",
            relationship="spouse",
            date_of_birth=date(1990, 1, 15),
            gender="male",
        )
        assert data.name == "John Doe"
        assert data.relationship == "spouse"
        assert data.date_of_birth == date(1990, 1, 15)
        assert data.gender == "male"
    
    def test_family_member_create_minimal(self):
        """Test creating a family member with minimal data.
        
        Validates: Requirements 14.2
        """
        data = FamilyMemberCreate(
            name="Jane Doe",
            relationship="child",
        )
        assert data.name == "Jane Doe"
        assert data.relationship == "child"
        assert data.date_of_birth is None
        assert data.gender is None
    
    def test_family_member_create_empty_name_rejected(self):
        """Test that empty name is rejected."""
        with pytest.raises(ValueError):
            FamilyMemberCreate(
                name="",
                relationship="spouse",
            )
    
    def test_family_member_update_partial(self):
        """Test partial update of family member."""
        data = FamilyMemberUpdate(name="Updated Name")
        assert data.name == "Updated Name"
        assert data.relationship is None
        assert data.date_of_birth is None


class TestHealthRecordSchemas:
    """Tests for health record schema validation."""
    
    def test_health_record_create_valid(self):
        """Test creating a valid health record.
        
        Validates: Requirements 14.1, 14.2
        """
        data = HealthRecordCreate(
            category="prescription",
            title="Blood Test Results",
            content_type="application/pdf",
            file_size=2048,
            record_date=date(2024, 1, 15),
            doctor_name="Dr. Smith",
            hospital_name="City Hospital",
            notes="Annual checkup results",
        )
        assert data.category == "prescription"
        assert data.title == "Blood Test Results"
        assert data.content_type == "application/pdf"
        assert data.file_size == 2048
        assert data.record_date == date(2024, 1, 15)
        assert data.doctor_name == "Dr. Smith"
        assert data.hospital_name == "City Hospital"
        assert data.notes == "Annual checkup results"
    
    def test_health_record_create_minimal(self):
        """Test creating a health record with minimal data.
        
        Validates: Requirements 14.1
        """
        data = HealthRecordCreate(
            category="lab_report",
            title="Lab Report",
            content_type="image/jpeg",
            file_size=512,
        )
        assert data.category == "lab_report"
        assert data.title == "Lab Report"
        assert data.family_member_id is None
        assert data.record_date is None
        assert data.doctor_name is None
    
    def test_health_record_create_with_family_member(self):
        """Test creating a health record for a family member.
        
        Validates: Requirements 14.2
        """
        family_member_id = uuid4()
        data = HealthRecordCreate(
            category="vaccine",
            title="COVID-19 Vaccine",
            content_type="application/pdf",
            file_size=1024,
            family_member_id=family_member_id,
        )
        assert data.family_member_id == family_member_id
    
    def test_health_record_create_empty_title_rejected(self):
        """Test that empty title is rejected."""
        with pytest.raises(ValueError):
            HealthRecordCreate(
                category="prescription",
                title="",
                content_type="application/pdf",
                file_size=1024,
            )
    
    def test_health_record_create_negative_file_size_rejected(self):
        """Test that negative file size is rejected."""
        with pytest.raises(ValueError):
            HealthRecordCreate(
                category="prescription",
                title="Test",
                content_type="application/pdf",
                file_size=-1,
            )
    
    def test_health_record_update_partial(self):
        """Test partial update of health record."""
        data = HealthRecordUpdate(
            title="Updated Title",
            doctor_name="Dr. Johnson",
        )
        assert data.title == "Updated Title"
        assert data.doctor_name == "Dr. Johnson"
        assert data.category is None
        assert data.notes is None
    
    def test_health_record_update_category_validation(self):
        """Test that category validation works in update schema."""
        # Valid category
        data = HealthRecordUpdate(category="scan")
        assert data.category == "scan"
        
        # Invalid category
        with pytest.raises(ValueError) as exc_info:
            HealthRecordUpdate(category="invalid")
        assert "Category must be one of" in str(exc_info.value)


class TestHealthRecordFilters:
    """Tests for health record filter schemas."""
    
    def test_filters_default_values(self):
        """Test default filter values."""
        from app.schemas.health import HealthRecordFilters
        
        filters = HealthRecordFilters()
        assert filters.category is None
        assert filters.family_member_id is None
        assert filters.start_date is None
        assert filters.end_date is None
        assert filters.page == 1
        assert filters.page_size == 20
    
    def test_filters_with_values(self):
        """Test filters with custom values."""
        from app.schemas.health import HealthRecordFilters
        
        family_member_id = uuid4()
        filters = HealthRecordFilters(
            category="prescription",
            family_member_id=family_member_id,
            start_date=date(2024, 1, 1),
            end_date=date(2024, 12, 31),
            page=2,
            page_size=50,
        )
        assert filters.category == "prescription"
        assert filters.family_member_id == family_member_id
        assert filters.start_date == date(2024, 1, 1)
        assert filters.end_date == date(2024, 12, 31)
        assert filters.page == 2
        assert filters.page_size == 50
    
    def test_filters_invalid_category(self):
        """Test that invalid category is rejected in filters."""
        from app.schemas.health import HealthRecordFilters
        
        with pytest.raises(ValueError) as exc_info:
            HealthRecordFilters(category="invalid")
        assert "Category must be one of" in str(exc_info.value)
    
    def test_filters_page_validation(self):
        """Test page number validation."""
        from app.schemas.health import HealthRecordFilters
        
        with pytest.raises(ValueError):
            HealthRecordFilters(page=0)
    
    def test_filters_page_size_validation(self):
        """Test page size validation."""
        from app.schemas.health import HealthRecordFilters
        
        with pytest.raises(ValueError):
            HealthRecordFilters(page_size=0)
        
        with pytest.raises(ValueError):
            HealthRecordFilters(page_size=101)


class TestPaginatedResponses:
    """Tests for paginated response schemas."""
    
    def test_paginated_health_record_response_create(self):
        """Test creating a paginated health record response."""
        from app.schemas.health import PaginatedHealthRecordResponse, HealthRecordResponse
        from datetime import datetime
        
        items = []
        response = PaginatedHealthRecordResponse.create(
            items=items,
            total=0,
            page=1,
            page_size=20,
        )
        assert response.items == []
        assert response.total == 0
        assert response.page == 1
        assert response.page_size == 20
        assert response.total_pages == 0
    
    def test_paginated_response_total_pages_calculation(self):
        """Test total pages calculation."""
        from app.schemas.health import PaginatedHealthRecordResponse
        
        # 25 items with page size 10 = 3 pages
        response = PaginatedHealthRecordResponse.create(
            items=[],
            total=25,
            page=1,
            page_size=10,
        )
        assert response.total_pages == 3
        
        # 20 items with page size 10 = 2 pages
        response = PaginatedHealthRecordResponse.create(
            items=[],
            total=20,
            page=1,
            page_size=10,
        )
        assert response.total_pages == 2
        
        # 0 items = 0 pages
        response = PaginatedHealthRecordResponse.create(
            items=[],
            total=0,
            page=1,
            page_size=10,
        )
        assert response.total_pages == 0
    
    def test_paginated_family_member_response_create(self):
        """Test creating a paginated family member response."""
        from app.schemas.health import PaginatedFamilyMemberResponse
        
        response = PaginatedFamilyMemberResponse.create(
            items=[],
            total=5,
            page=1,
            page_size=10,
        )
        assert response.total == 5
        assert response.total_pages == 1


class TestTimelineSchemas:
    """Tests for health timeline schema validation.
    
    Validates: Requirements 14.5, 14.6
    """
    
    def test_timeline_entry_response_creation(self):
        """Test creating a timeline entry response."""
        from app.schemas.health import TimelineEntryResponse
        from datetime import datetime
        
        entry = TimelineEntryResponse(
            id=uuid4(),
            category="prescription",
            title="Blood Test",
            record_date=date(2024, 1, 15),
            doctor_name="Dr. Smith",
            hospital_name="City Hospital",
            family_member_id=None,
            family_member_name=None,
            created_at=datetime.now(),
        )
        assert entry.category == "prescription"
        assert entry.title == "Blood Test"
        assert entry.record_date == date(2024, 1, 15)
        assert entry.doctor_name == "Dr. Smith"
        assert entry.hospital_name == "City Hospital"
    
    def test_timeline_entry_with_family_member(self):
        """Test timeline entry with family member details."""
        from app.schemas.health import TimelineEntryResponse
        from datetime import datetime
        
        family_member_id = uuid4()
        entry = TimelineEntryResponse(
            id=uuid4(),
            category="vaccine",
            title="COVID-19 Vaccine",
            record_date=date(2024, 3, 10),
            doctor_name=None,
            hospital_name="Health Center",
            family_member_id=family_member_id,
            family_member_name="John Doe",
            created_at=datetime.now(),
        )
        assert entry.family_member_id == family_member_id
        assert entry.family_member_name == "John Doe"
    
    def test_health_timeline_response_create(self):
        """Test creating a health timeline response."""
        from app.schemas.health import HealthTimelineResponse, TimelineEntryResponse
        from datetime import datetime
        
        items = [
            TimelineEntryResponse(
                id=uuid4(),
                category="prescription",
                title="Test Record",
                record_date=date(2024, 1, 15),
                doctor_name=None,
                hospital_name=None,
                family_member_id=None,
                family_member_name=None,
                created_at=datetime.now(),
            )
        ]
        
        response = HealthTimelineResponse.create(
            items=items,
            total=1,
            page=1,
            page_size=20,
        )
        assert len(response.items) == 1
        assert response.total == 1
        assert response.page == 1
        assert response.page_size == 20
        assert response.total_pages == 1
    
    def test_health_timeline_response_pagination(self):
        """Test timeline response pagination calculation."""
        from app.schemas.health import HealthTimelineResponse
        
        # 25 items with page size 10 = 3 pages
        response = HealthTimelineResponse.create(
            items=[],
            total=25,
            page=1,
            page_size=10,
        )
        assert response.total_pages == 3
        
        # 0 items = 0 pages
        response = HealthTimelineResponse.create(
            items=[],
            total=0,
            page=1,
            page_size=10,
        )
        assert response.total_pages == 0
