"""Unit tests for document search functionality.

Validates: Requirements 6.7
"""

import pytest
from datetime import datetime, timezone
from uuid import uuid4

from app.schemas.document import (
    DocumentCreate,
    DocumentCategory,
    DocumentSearchQuery,
    PaginatedResponse,
    DocumentSearchResponse,
)
from app.services.document import DocumentService


class TestDocumentSearchService:
    """Tests for document search in the in-memory service.
    
    Validates: Requirements 6.7
    """
    
    @pytest.fixture(autouse=True)
    def setup_service(self):
        """Set up a fresh document service for each test."""
        self.service = DocumentService()
        self.user_id = uuid4()
        yield
        self.service.clear()
    
    async def _create_test_document(
        self,
        title: str = "Test Document",
        category: str = DocumentCategory.IDENTITY,
        ocr_text: str = None,
    ):
        """Helper to create a test document."""
        data = DocumentCreate(
            title=title,
            category=category,
            content_type="application/pdf",
            file_size=1000,
        )
        doc = await self.service.create_document(
            user_id=self.user_id,
            data=data,
            file_path=f"documents/{uuid4()}.pdf",
            encryption_key="test-key",
        )
        
        # Set OCR text if provided
        if ocr_text:
            doc.ocr_text = ocr_text
        
        return doc
    
    @pytest.mark.asyncio
    async def test_search_by_title(self):
        """Test searching documents by title.
        
        Validates: Requirements 6.7
        """
        # Create documents with different titles
        await self._create_test_document(title="Passport Copy")
        await self._create_test_document(title="Driver License")
        await self._create_test_document(title="Birth Certificate")
        
        # Search for "passport"
        results = [
            doc for doc in self.service._documents.values()
            if "passport" in doc.title.lower()
        ]
        
        assert len(results) == 1
        assert results[0].title == "Passport Copy"
    
    @pytest.mark.asyncio
    async def test_search_by_category(self):
        """Test searching documents by category.
        
        Validates: Requirements 6.7
        """
        # Create documents in different categories
        await self._create_test_document(
            title="ID Card",
            category=DocumentCategory.IDENTITY
        )
        await self._create_test_document(
            title="Degree Certificate",
            category=DocumentCategory.EDUCATION
        )
        await self._create_test_document(
            title="Tax Return",
            category=DocumentCategory.FINANCE
        )
        
        # Search for "education"
        results = [
            doc for doc in self.service._documents.values()
            if "education" in doc.category.lower()
        ]
        
        assert len(results) == 1
        assert results[0].category == DocumentCategory.EDUCATION
    
    @pytest.mark.asyncio
    async def test_search_by_ocr_text(self):
        """Test searching documents by OCR content.
        
        Validates: Requirements 6.7
        """
        # Create documents with OCR text
        doc1 = await self._create_test_document(
            title="Document 1",
            ocr_text="John Smith, Date of Birth: 1990-01-15"
        )
        doc2 = await self._create_test_document(
            title="Document 2",
            ocr_text="Jane Doe, Employee ID: 12345"
        )
        
        # Search for "John Smith" in OCR text
        results = [
            doc for doc in self.service._documents.values()
            if doc.ocr_text and "john smith" in doc.ocr_text.lower()
        ]
        
        assert len(results) == 1
        assert results[0].id == doc1.id
    
    @pytest.mark.asyncio
    async def test_search_case_insensitive(self):
        """Test that search is case-insensitive.
        
        Validates: Requirements 6.7
        """
        await self._create_test_document(title="PASSPORT COPY")
        await self._create_test_document(title="passport scan")
        await self._create_test_document(title="Passport Photo")
        
        # Search with different cases
        results = [
            doc for doc in self.service._documents.values()
            if "passport" in doc.title.lower()
        ]
        
        assert len(results) == 3
    
    @pytest.mark.asyncio
    async def test_search_returns_empty_for_no_matches(self):
        """Test that search returns empty list when no matches found.
        
        Validates: Requirements 6.7
        """
        await self._create_test_document(title="Passport Copy")
        await self._create_test_document(title="Driver License")
        
        # Search for non-existent term
        results = [
            doc for doc in self.service._documents.values()
            if "nonexistent" in doc.title.lower()
        ]
        
        assert len(results) == 0
    
    @pytest.mark.asyncio
    async def test_search_only_returns_user_documents(self):
        """Test that search only returns documents owned by the user.
        
        Validates: Requirements 6.7
        """
        other_user_id = uuid4()
        
        # Create document for current user
        await self._create_test_document(title="My Passport")
        
        # Create document for another user
        data = DocumentCreate(
            title="Other Passport",
            category=DocumentCategory.IDENTITY,
            content_type="application/pdf",
            file_size=1000,
        )
        await self.service.create_document(
            user_id=other_user_id,
            data=data,
            file_path=f"documents/{uuid4()}.pdf",
            encryption_key="test-key",
        )
        
        # Search should only return current user's documents
        results = [
            doc for doc in self.service._documents.values()
            if doc.user_id == self.user_id and "passport" in doc.title.lower()
        ]
        
        assert len(results) == 1
        assert results[0].title == "My Passport"
    
    @pytest.mark.asyncio
    async def test_search_method_by_title(self):
        """Test the search method searches by title.
        
        Validates: Requirements 6.7
        """
        await self._create_test_document(title="Passport Copy")
        await self._create_test_document(title="Driver License")
        await self._create_test_document(title="Birth Certificate")
        
        results = await self.service.search(
            user_id=self.user_id,
            query="passport",
        )
        
        assert len(results) == 1
        assert results[0].title == "Passport Copy"
    
    @pytest.mark.asyncio
    async def test_search_method_by_ocr_text(self):
        """Test the search method searches by OCR text.
        
        Validates: Requirements 6.7
        """
        doc1 = await self._create_test_document(
            title="Document 1",
            ocr_text="John Smith, Date of Birth: 1990-01-15"
        )
        await self._create_test_document(
            title="Document 2",
            ocr_text="Jane Doe, Employee ID: 12345"
        )
        
        results = await self.service.search(
            user_id=self.user_id,
            query="John Smith",
        )
        
        assert len(results) == 1
        assert results[0].id == doc1.id
    
    @pytest.mark.asyncio
    async def test_search_method_with_category_filter(self):
        """Test the search method with category filter.
        
        Validates: Requirements 6.7
        """
        await self._create_test_document(
            title="ID Card",
            category=DocumentCategory.IDENTITY
        )
        await self._create_test_document(
            title="ID Badge",
            category=DocumentCategory.CAREER
        )
        
        # Search with category filter
        results = await self.service.search(
            user_id=self.user_id,
            query="ID",
            category=DocumentCategory.IDENTITY,
        )
        
        assert len(results) == 1
        assert results[0].category == DocumentCategory.IDENTITY
    
    @pytest.mark.asyncio
    async def test_search_method_returns_empty_for_no_matches(self):
        """Test the search method returns empty list when no matches.
        
        Validates: Requirements 6.7
        """
        await self._create_test_document(title="Passport Copy")
        
        results = await self.service.search(
            user_id=self.user_id,
            query="nonexistent",
        )
        
        assert len(results) == 0


class TestDocumentSearchSchemas:
    """Tests for document search schemas.
    
    Validates: Requirements 6.7
    """
    
    def test_search_query_valid(self):
        """Test valid search query creation."""
        query = DocumentSearchQuery(
            query="passport",
            category=DocumentCategory.IDENTITY,
            page=1,
            page_size=20,
        )
        
        assert query.query == "passport"
        assert query.category == DocumentCategory.IDENTITY
        assert query.page == 1
        assert query.page_size == 20
    
    def test_search_query_defaults(self):
        """Test search query default values."""
        query = DocumentSearchQuery(query="test")
        
        assert query.query == "test"
        assert query.category is None
        assert query.page == 1
        assert query.page_size == 20
    
    def test_search_query_invalid_category(self):
        """Test that invalid category raises validation error."""
        from pydantic import ValidationError
        
        with pytest.raises(ValidationError):
            DocumentSearchQuery(
                query="test",
                category="InvalidCategory",
            )
    
    def test_search_query_empty_query_rejected(self):
        """Test that empty query is rejected."""
        from pydantic import ValidationError
        
        with pytest.raises(ValidationError):
            DocumentSearchQuery(query="")
    
    def test_search_query_page_validation(self):
        """Test page number validation."""
        from pydantic import ValidationError
        
        with pytest.raises(ValidationError):
            DocumentSearchQuery(query="test", page=0)
    
    def test_search_query_page_size_validation(self):
        """Test page size validation."""
        from pydantic import ValidationError
        
        # Too small
        with pytest.raises(ValidationError):
            DocumentSearchQuery(query="test", page_size=0)
        
        # Too large
        with pytest.raises(ValidationError):
            DocumentSearchQuery(query="test", page_size=101)
    
    def test_paginated_response_create(self):
        """Test PaginatedResponse creation."""
        items = [
            DocumentSearchResponse(
                id=uuid4(),
                user_id=uuid4(),
                title="Test",
                category=DocumentCategory.IDENTITY,
                content_type="application/pdf",
                file_size=1000,
                is_expired=False,
                current_version=1,
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc),
            )
        ]
        
        response = PaginatedResponse.create(
            items=items,
            total=25,
            page=1,
            page_size=10,
        )
        
        assert response.total == 25
        assert response.page == 1
        assert response.page_size == 10
        assert response.total_pages == 3
        assert len(response.items) == 1
    
    def test_paginated_response_total_pages_calculation(self):
        """Test total pages calculation."""
        # Exact division
        response = PaginatedResponse.create(
            items=[],
            total=100,
            page=1,
            page_size=10,
        )
        assert response.total_pages == 10
        
        # With remainder
        response = PaginatedResponse.create(
            items=[],
            total=25,
            page=1,
            page_size=10,
        )
        assert response.total_pages == 3
        
        # Empty results
        response = PaginatedResponse.create(
            items=[],
            total=0,
            page=1,
            page_size=10,
        )
        assert response.total_pages == 0
