"""Property-based tests for document module.

Uses Hypothesis to verify universal properties across all valid inputs.

**Validates: Requirements 6.6**
"""

import string
from datetime import datetime, timezone, timedelta
from uuid import uuid4

import pytest
from hypothesis import given, strategies as st, settings, assume
from pydantic import ValidationError

from app.schemas.document import (
    DocumentCreate,
    DocumentUpdate,
    DocumentCategory,
    DocumentVersionResponse,
    VersionHistoryResponse,
)
from app.services.document import DocumentService


# ============================================================================
# Hypothesis Strategies for Document Data
# ============================================================================

@st.composite
def valid_document_titles(draw):
    """Generate valid document titles (1-255 characters)."""
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
def valid_categories(draw):
    """Generate valid document categories."""
    return draw(st.sampled_from(DocumentCategory.ALL))


@st.composite
def valid_content_types(draw):
    """Generate valid MIME content types."""
    return draw(st.sampled_from([
        "application/pdf",
        "image/jpeg",
        "image/png",
        "application/msword",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "text/plain",
    ]))


@st.composite
def valid_file_sizes(draw):
    """Generate valid file sizes (positive integers)."""
    return draw(st.integers(min_value=1, max_value=100_000_000))  # Up to 100MB


@st.composite
def valid_file_paths(draw):
    """Generate valid file paths."""
    chars = string.ascii_lowercase + string.digits
    filename = draw(st.text(alphabet=chars, min_size=5, max_size=20))
    extension = draw(st.sampled_from(["pdf", "jpg", "png", "doc", "txt"]))
    return f"documents/{filename}.{extension}"


@st.composite
def valid_document_create_data(draw):
    """Generate valid document creation data."""
    return {
        "title": draw(valid_document_titles()),
        "category": draw(valid_categories()),
        "content_type": draw(valid_content_types()),
        "file_size": draw(valid_file_sizes()),
    }


@st.composite
def valid_document_update_data(draw):
    """Generate valid document update data with new file."""
    return {
        "title": draw(valid_document_titles()),
        "content_type": draw(valid_content_types()),
        "file_size": draw(valid_file_sizes()),
    }


@st.composite
def update_counts(draw):
    """Generate number of updates to perform (0-10)."""
    return draw(st.integers(min_value=0, max_value=10))


# ============================================================================
# Property 14: Document Version History
# ============================================================================

class TestDocumentVersionHistoryProperty:
    """Property 14: Document Version History.
    
    **Validates: Requirements 6.6**
    
    For any document updated N times, the version history SHALL contain exactly
    N+1 versions (including original) with correct timestamps in chronological order.
    """
    
    @pytest.fixture(autouse=True)
    def setup_service(self):
        """Set up a fresh document service for each test."""
        self.service = DocumentService()
        yield
        self.service.clear()
    
    @given(
        doc_data=valid_document_create_data(),
        num_updates=update_counts(),
    )
    @settings(max_examples=10, deadline=None)
    @pytest.mark.asyncio
    async def test_version_count_equals_updates_plus_one(
        self,
        doc_data: dict,
        num_updates: int,
    ):
        """For any document updated N times, the version history SHALL contain
        exactly N+1 versions.
        
        **Validates: Requirements 6.6**
        
        This test verifies that:
        1. Creating a document creates version 1
        2. Each update creates a new version
        3. Total versions = number of updates + 1 (original)
        """
        user_id = uuid4()
        
        # Create the document
        create_data = DocumentCreate(**doc_data)
        file_path = f"documents/{uuid4()}.pdf"
        encryption_key = "test-encryption-key"
        
        document = await self.service.create_document(
            user_id=user_id,
            data=create_data,
            file_path=file_path,
            encryption_key=encryption_key,
        )
        
        # Perform N updates
        for i in range(num_updates):
            update_data = DocumentUpdate(
                title=f"Updated Title {i + 1}",
                content_type="application/pdf",
                file_size=1000 * (i + 2),
            )
            new_file_path = f"documents/{uuid4()}.pdf"
            
            await self.service.update_document(
                document_id=document.id,
                data=update_data,
                new_file_path=new_file_path,
            )
        
        # Get version history
        history = await self.service.get_version_history(document.id)
        
        # Verify version count
        expected_versions = num_updates + 1
        assert history.total_versions == expected_versions, (
            f"Expected {expected_versions} versions after {num_updates} updates, "
            f"but got {history.total_versions}"
        )
        assert len(history.versions) == expected_versions, (
            f"Expected {expected_versions} version records, "
            f"but got {len(history.versions)}"
        )
    
    @given(
        doc_data=valid_document_create_data(),
        num_updates=st.integers(min_value=1, max_value=10),
    )
    @settings(max_examples=10, deadline=None)
    @pytest.mark.asyncio
    async def test_versions_in_chronological_order(
        self,
        doc_data: dict,
        num_updates: int,
    ):
        """For any document with multiple versions, retrieving version history
        SHALL return all versions in chronological order.
        
        **Validates: Requirements 6.6**
        
        This test verifies that:
        1. Versions are ordered by version_number (ascending)
        2. Version numbers are sequential (1, 2, 3, ...)
        3. Timestamps are in non-decreasing order
        """
        user_id = uuid4()
        
        # Create the document
        create_data = DocumentCreate(**doc_data)
        file_path = f"documents/{uuid4()}.pdf"
        encryption_key = "test-encryption-key"
        
        document = await self.service.create_document(
            user_id=user_id,
            data=create_data,
            file_path=file_path,
            encryption_key=encryption_key,
        )
        
        # Perform N updates
        for i in range(num_updates):
            update_data = DocumentUpdate(
                title=f"Updated Title {i + 1}",
                content_type="application/pdf",
                file_size=1000 * (i + 2),
            )
            new_file_path = f"documents/{uuid4()}.pdf"
            
            await self.service.update_document(
                document_id=document.id,
                data=update_data,
                new_file_path=new_file_path,
            )
        
        # Get version history
        history = await self.service.get_version_history(document.id)
        
        # Verify versions are in chronological order by version number
        for i, version in enumerate(history.versions):
            expected_version_number = i + 1
            assert version.version_number == expected_version_number, (
                f"Expected version {expected_version_number} at index {i}, "
                f"but got version {version.version_number}"
            )
        
        # Verify timestamps are in non-decreasing order
        for i in range(1, len(history.versions)):
            prev_timestamp = history.versions[i - 1].created_at
            curr_timestamp = history.versions[i].created_at
            assert curr_timestamp >= prev_timestamp, (
                f"Version {i + 1} timestamp ({curr_timestamp}) should be >= "
                f"version {i} timestamp ({prev_timestamp})"
            )
    
    @given(doc_data=valid_document_create_data())
    @settings(max_examples=10, deadline=None)
    @pytest.mark.asyncio
    async def test_initial_version_has_correct_timestamp(
        self,
        doc_data: dict,
    ):
        """For any newly created document, version 1 SHALL have a timestamp
        equal to or after the creation time.
        
        **Validates: Requirements 6.6**
        
        This test verifies that:
        1. Initial version (version 1) is created with the document
        2. The timestamp is set correctly at creation time
        """
        user_id = uuid4()
        before_creation = datetime.now(timezone.utc)
        
        # Create the document
        create_data = DocumentCreate(**doc_data)
        file_path = f"documents/{uuid4()}.pdf"
        encryption_key = "test-encryption-key"
        
        document = await self.service.create_document(
            user_id=user_id,
            data=create_data,
            file_path=file_path,
            encryption_key=encryption_key,
        )
        
        after_creation = datetime.now(timezone.utc)
        
        # Get version history
        history = await self.service.get_version_history(document.id)
        
        # Verify initial version exists
        assert len(history.versions) == 1, "Should have exactly 1 version after creation"
        
        initial_version = history.versions[0]
        assert initial_version.version_number == 1, "Initial version should be version 1"
        
        # Verify timestamp is within expected range
        # Allow small tolerance for timing
        tolerance = timedelta(seconds=5)
        assert initial_version.created_at >= before_creation - tolerance, (
            f"Version timestamp {initial_version.created_at} should be >= "
            f"{before_creation - tolerance}"
        )
        assert initial_version.created_at <= after_creation + tolerance, (
            f"Version timestamp {initial_version.created_at} should be <= "
            f"{after_creation + tolerance}"
        )
    
    @given(
        doc_data=valid_document_create_data(),
        update_data=valid_document_update_data(),
    )
    @settings(max_examples=10, deadline=None)
    @pytest.mark.asyncio
    async def test_each_version_has_correct_metadata(
        self,
        doc_data: dict,
        update_data: dict,
    ):
        """For any document version, the version SHALL store the correct
        file metadata (path, size, content type).
        
        **Validates: Requirements 6.6**
        
        This test verifies that:
        1. Each version stores its own file path
        2. Each version stores its own file size
        3. Each version stores its own content type
        """
        user_id = uuid4()
        
        # Create the document
        create_data = DocumentCreate(**doc_data)
        initial_file_path = f"documents/initial_{uuid4()}.pdf"
        encryption_key = "test-encryption-key"
        
        document = await self.service.create_document(
            user_id=user_id,
            data=create_data,
            file_path=initial_file_path,
            encryption_key=encryption_key,
        )
        
        # Update the document
        update_schema = DocumentUpdate(**update_data)
        updated_file_path = f"documents/updated_{uuid4()}.pdf"
        
        await self.service.update_document(
            document_id=document.id,
            data=update_schema,
            new_file_path=updated_file_path,
        )
        
        # Get version history
        history = await self.service.get_version_history(document.id)
        
        # Verify version 1 metadata
        version1 = history.versions[0]
        assert version1.file_path == initial_file_path, (
            f"Version 1 file_path should be {initial_file_path}, "
            f"got {version1.file_path}"
        )
        assert version1.file_size == doc_data["file_size"], (
            f"Version 1 file_size should be {doc_data['file_size']}, "
            f"got {version1.file_size}"
        )
        assert version1.content_type == doc_data["content_type"], (
            f"Version 1 content_type should be {doc_data['content_type']}, "
            f"got {version1.content_type}"
        )
        
        # Verify version 2 metadata
        version2 = history.versions[1]
        assert version2.file_path == updated_file_path, (
            f"Version 2 file_path should be {updated_file_path}, "
            f"got {version2.file_path}"
        )
        assert version2.file_size == update_data["file_size"], (
            f"Version 2 file_size should be {update_data['file_size']}, "
            f"got {version2.file_size}"
        )
        assert version2.content_type == update_data["content_type"], (
            f"Version 2 content_type should be {update_data['content_type']}, "
            f"got {version2.content_type}"
        )
    
    @given(
        doc_data=valid_document_create_data(),
        num_updates=st.integers(min_value=2, max_value=5),
    )
    @settings(max_examples=10, deadline=None)
    @pytest.mark.asyncio
    async def test_version_numbers_are_sequential(
        self,
        doc_data: dict,
        num_updates: int,
    ):
        """For any document with multiple versions, version numbers SHALL be
        sequential starting from 1.
        
        **Validates: Requirements 6.6**
        
        This test verifies that:
        1. Version numbers start at 1
        2. Version numbers increment by 1 for each update
        3. No gaps in version numbers
        """
        user_id = uuid4()
        
        # Create the document
        create_data = DocumentCreate(**doc_data)
        file_path = f"documents/{uuid4()}.pdf"
        encryption_key = "test-encryption-key"
        
        document = await self.service.create_document(
            user_id=user_id,
            data=create_data,
            file_path=file_path,
            encryption_key=encryption_key,
        )
        
        # Perform N updates
        for i in range(num_updates):
            update_data = DocumentUpdate(
                title=f"Updated Title {i + 1}",
                content_type="application/pdf",
                file_size=1000 * (i + 2),
            )
            new_file_path = f"documents/{uuid4()}.pdf"
            
            await self.service.update_document(
                document_id=document.id,
                data=update_data,
                new_file_path=new_file_path,
            )
        
        # Get version history
        history = await self.service.get_version_history(document.id)
        
        # Verify version numbers are sequential
        expected_version_numbers = list(range(1, num_updates + 2))
        actual_version_numbers = [v.version_number for v in history.versions]
        
        assert actual_version_numbers == expected_version_numbers, (
            f"Expected version numbers {expected_version_numbers}, "
            f"but got {actual_version_numbers}"
        )
    
    @given(doc_data=valid_document_create_data())
    @settings(max_examples=10, deadline=None)
    @pytest.mark.asyncio
    async def test_document_current_version_matches_latest(
        self,
        doc_data: dict,
    ):
        """For any document, the current_version field SHALL match the highest
        version number in the history.
        
        **Validates: Requirements 6.6**
        
        This test verifies that:
        1. Document's current_version is updated on each update
        2. current_version matches the latest version in history
        """
        user_id = uuid4()
        
        # Create the document
        create_data = DocumentCreate(**doc_data)
        file_path = f"documents/{uuid4()}.pdf"
        encryption_key = "test-encryption-key"
        
        document = await self.service.create_document(
            user_id=user_id,
            data=create_data,
            file_path=file_path,
            encryption_key=encryption_key,
        )
        
        # Verify initial current_version
        assert document.current_version == 1, "Initial current_version should be 1"
        
        # Perform updates and verify current_version after each
        for i in range(3):
            update_data = DocumentUpdate(
                title=f"Updated Title {i + 1}",
                content_type="application/pdf",
                file_size=1000 * (i + 2),
            )
            new_file_path = f"documents/{uuid4()}.pdf"
            
            updated_doc = await self.service.update_document(
                document_id=document.id,
                data=update_data,
                new_file_path=new_file_path,
            )
            
            expected_version = i + 2
            assert updated_doc.current_version == expected_version, (
                f"After update {i + 1}, current_version should be {expected_version}, "
                f"but got {updated_doc.current_version}"
            )
            
            # Verify history matches
            history = await self.service.get_version_history(document.id)
            latest_version = max(v.version_number for v in history.versions)
            assert updated_doc.current_version == latest_version, (
                f"current_version ({updated_doc.current_version}) should match "
                f"latest version in history ({latest_version})"
            )


# ============================================================================
# Property 15: Document Search Indexing
# ============================================================================

@st.composite
def valid_searchable_text(draw):
    """Generate valid searchable text (non-empty, alphanumeric with spaces)."""
    chars = string.ascii_letters + string.digits + " "
    length = draw(st.integers(min_value=3, max_value=50))
    
    # Start with a letter
    first_char = draw(st.sampled_from(string.ascii_letters))
    
    if length == 1:
        return first_char
    
    rest = draw(st.text(alphabet=chars, min_size=length - 1, max_size=length - 1))
    text = first_char + rest
    
    # Clean up consecutive spaces
    while "  " in text:
        text = text.replace("  ", " ")
    
    return text.strip() or first_char


@st.composite
def valid_ocr_text(draw):
    """Generate valid OCR text content."""
    chars = string.ascii_letters + string.digits + " .,:-"
    length = draw(st.integers(min_value=10, max_value=200))
    
    # Start with a letter
    first_char = draw(st.sampled_from(string.ascii_letters))
    rest = draw(st.text(alphabet=chars, min_size=length - 1, max_size=length - 1))
    text = first_char + rest
    
    # Clean up consecutive spaces
    while "  " in text:
        text = text.replace("  ", " ")
    
    return text.strip() or first_char


class TestDocumentSearchIndexingProperty:
    """Property 15: Document Search Indexing.
    
    **Validates: Requirements 6.7, 7.6**
    
    For any document containing text T (either in metadata or OCR content),
    searching for T SHALL return that document in the results.
    """
    
    @pytest.fixture(autouse=True)
    def setup_service(self):
        """Set up a fresh document service for each test."""
        self.service = DocumentService()
        yield
        self.service.clear()
    
    @given(
        title=valid_searchable_text(),
        category=valid_categories(),
    )
    @settings(max_examples=20, deadline=None)
    @pytest.mark.asyncio
    async def test_documents_with_matching_title_are_found(
        self,
        title: str,
        category: str,
    ):
        """For any document with title T, searching for a substring of T
        SHALL return the document in results.
        
        **Validates: Requirements 6.7, 7.6**
        
        This test verifies that:
        1. Documents with matching title text are found by search
        2. Search matches substrings of the title
        """
        user_id = uuid4()
        
        # Create document with the generated title
        create_data = DocumentCreate(
            title=title,
            category=category,
            content_type="application/pdf",
            file_size=1000,
        )
        file_path = f"documents/{uuid4()}.pdf"
        
        document = await self.service.create_document(
            user_id=user_id,
            data=create_data,
            file_path=file_path,
            encryption_key="test-key",
        )
        
        # Search for the full title
        results = await self.service.search(
            user_id=user_id,
            query=title,
        )
        
        # Verify document is found
        result_ids = [doc.id for doc in results]
        assert document.id in result_ids, (
            f"Document with title '{title}' should be found when searching for '{title}'"
        )
        
        # Search for a substring of the title (if title is long enough)
        if len(title) >= 3:
            substring = title[:len(title) // 2 + 1]
            if substring.strip():
                results = await self.service.search(
                    user_id=user_id,
                    query=substring,
                )
                result_ids = [doc.id for doc in results]
                assert document.id in result_ids, (
                    f"Document with title '{title}' should be found when searching for substring '{substring}'"
                )
    
    @given(
        title=valid_document_titles(),
        ocr_text=valid_ocr_text(),
        category=valid_categories(),
    )
    @settings(max_examples=20, deadline=None)
    @pytest.mark.asyncio
    async def test_documents_with_matching_ocr_text_are_found(
        self,
        title: str,
        ocr_text: str,
        category: str,
    ):
        """For any document with OCR text T, searching for a substring of T
        SHALL return the document in results.
        
        **Validates: Requirements 6.7, 7.6**
        
        This test verifies that:
        1. Documents with matching OCR text are found by search
        2. Search matches substrings of the OCR content
        """
        user_id = uuid4()
        
        # Create document
        create_data = DocumentCreate(
            title=title,
            category=category,
            content_type="application/pdf",
            file_size=1000,
        )
        file_path = f"documents/{uuid4()}.pdf"
        
        document = await self.service.create_document(
            user_id=user_id,
            data=create_data,
            file_path=file_path,
            encryption_key="test-key",
        )
        
        # Set OCR text (simulating OCR processing)
        document.ocr_text = ocr_text
        
        # Extract a unique substring from OCR text for searching
        # Use a portion that's unlikely to match the title
        search_term = ocr_text[len(ocr_text) // 4:len(ocr_text) // 2 + 3]
        assume(len(search_term.strip()) >= 3)  # Ensure we have a valid search term
        search_term = search_term.strip()
        
        # Search for the OCR text substring
        results = await self.service.search(
            user_id=user_id,
            query=search_term,
        )
        
        # Verify document is found
        result_ids = [doc.id for doc in results]
        assert document.id in result_ids, (
            f"Document with OCR text containing '{search_term}' should be found"
        )
    
    @given(
        title=valid_searchable_text(),
        category=valid_categories(),
    )
    @settings(max_examples=20, deadline=None)
    @pytest.mark.asyncio
    async def test_search_is_case_insensitive(
        self,
        title: str,
        category: str,
    ):
        """For any document with text T, searching for T in different cases
        SHALL return the document in results.
        
        **Validates: Requirements 6.7, 7.6**
        
        This test verifies that:
        1. Search is case-insensitive
        2. Uppercase, lowercase, and mixed case queries all match
        """
        user_id = uuid4()
        
        # Create document with the generated title
        create_data = DocumentCreate(
            title=title,
            category=category,
            content_type="application/pdf",
            file_size=1000,
        )
        file_path = f"documents/{uuid4()}.pdf"
        
        document = await self.service.create_document(
            user_id=user_id,
            data=create_data,
            file_path=file_path,
            encryption_key="test-key",
        )
        
        # Search with uppercase
        results = await self.service.search(
            user_id=user_id,
            query=title.upper(),
        )
        result_ids = [doc.id for doc in results]
        assert document.id in result_ids, (
            f"Document should be found with uppercase query '{title.upper()}'"
        )
        
        # Search with lowercase
        results = await self.service.search(
            user_id=user_id,
            query=title.lower(),
        )
        result_ids = [doc.id for doc in results]
        assert document.id in result_ids, (
            f"Document should be found with lowercase query '{title.lower()}'"
        )
        
        # Search with mixed case (swap case)
        mixed_case = title.swapcase()
        results = await self.service.search(
            user_id=user_id,
            query=mixed_case,
        )
        result_ids = [doc.id for doc in results]
        assert document.id in result_ids, (
            f"Document should be found with mixed case query '{mixed_case}'"
        )
    
    @given(
        title=valid_searchable_text(),
        category=valid_categories(),
    )
    @settings(max_examples=20, deadline=None)
    @pytest.mark.asyncio
    async def test_only_users_own_documents_are_returned(
        self,
        title: str,
        category: str,
    ):
        """For any search query, only the user's own documents SHALL be returned.
        
        **Validates: Requirements 6.7, 7.6**
        
        This test verifies that:
        1. Search only returns documents owned by the searching user
        2. Other users' documents with matching text are not returned
        """
        user1_id = uuid4()
        user2_id = uuid4()
        
        # Create document for user 1
        create_data = DocumentCreate(
            title=title,
            category=category,
            content_type="application/pdf",
            file_size=1000,
        )
        
        doc1 = await self.service.create_document(
            user_id=user1_id,
            data=create_data,
            file_path=f"documents/{uuid4()}.pdf",
            encryption_key="test-key",
        )
        
        # Create document with same title for user 2
        doc2 = await self.service.create_document(
            user_id=user2_id,
            data=create_data,
            file_path=f"documents/{uuid4()}.pdf",
            encryption_key="test-key",
        )
        
        # User 1 searches - should only find their document
        results = await self.service.search(
            user_id=user1_id,
            query=title,
        )
        result_ids = [doc.id for doc in results]
        
        assert doc1.id in result_ids, "User 1 should find their own document"
        assert doc2.id not in result_ids, "User 1 should NOT find User 2's document"
        
        # User 2 searches - should only find their document
        results = await self.service.search(
            user_id=user2_id,
            query=title,
        )
        result_ids = [doc.id for doc in results]
        
        assert doc2.id in result_ids, "User 2 should find their own document"
        assert doc1.id not in result_ids, "User 2 should NOT find User 1's document"
    
    @given(
        title=valid_searchable_text(),
    )
    @settings(max_examples=20, deadline=None)
    @pytest.mark.asyncio
    async def test_category_filtering_works_correctly(
        self,
        title: str,
    ):
        """For any search with category filter, only documents in that category
        SHALL be returned.
        
        **Validates: Requirements 6.7, 7.6**
        
        This test verifies that:
        1. Category filtering restricts results to the specified category
        2. Documents in other categories with matching text are not returned
        """
        user_id = uuid4()
        
        # Create documents with same title in different categories
        categories = [DocumentCategory.IDENTITY, DocumentCategory.EDUCATION, DocumentCategory.FINANCE]
        created_docs = {}
        
        for cat in categories:
            create_data = DocumentCreate(
                title=title,
                category=cat,
                content_type="application/pdf",
                file_size=1000,
            )
            doc = await self.service.create_document(
                user_id=user_id,
                data=create_data,
                file_path=f"documents/{uuid4()}.pdf",
                encryption_key="test-key",
            )
            created_docs[cat] = doc
        
        # Search with category filter for each category
        for target_category in categories:
            results = await self.service.search(
                user_id=user_id,
                query=title,
                category=target_category,
            )
            result_ids = [doc.id for doc in results]
            
            # Should find document in target category
            assert created_docs[target_category].id in result_ids, (
                f"Document in category '{target_category}' should be found"
            )
            
            # Should NOT find documents in other categories
            for other_category in categories:
                if other_category != target_category:
                    assert created_docs[other_category].id not in result_ids, (
                        f"Document in category '{other_category}' should NOT be found "
                        f"when filtering by '{target_category}'"
                    )
    
    @given(
        title=valid_searchable_text(),
        ocr_text=valid_ocr_text(),
        category=valid_categories(),
    )
    @settings(max_examples=20, deadline=None)
    @pytest.mark.asyncio
    async def test_search_finds_document_by_either_title_or_ocr(
        self,
        title: str,
        ocr_text: str,
        category: str,
    ):
        """For any document with title T1 and OCR text T2, searching for either
        T1 or T2 SHALL return the document.
        
        **Validates: Requirements 6.7, 7.6**
        
        This test verifies that:
        1. Search matches against both title and OCR text
        2. A document can be found by either field
        """
        user_id = uuid4()
        
        # Ensure title and OCR text are different enough
        assume(title.lower() not in ocr_text.lower())
        assume(ocr_text.lower() not in title.lower())
        
        # Create document
        create_data = DocumentCreate(
            title=title,
            category=category,
            content_type="application/pdf",
            file_size=1000,
        )
        
        document = await self.service.create_document(
            user_id=user_id,
            data=create_data,
            file_path=f"documents/{uuid4()}.pdf",
            encryption_key="test-key",
        )
        
        # Set OCR text
        document.ocr_text = ocr_text
        
        # Search by title
        results = await self.service.search(
            user_id=user_id,
            query=title,
        )
        result_ids = [doc.id for doc in results]
        assert document.id in result_ids, (
            f"Document should be found when searching by title '{title}'"
        )
        
        # Search by OCR text
        results = await self.service.search(
            user_id=user_id,
            query=ocr_text[:20],  # Use first 20 chars of OCR text
        )
        result_ids = [doc.id for doc in results]
        assert document.id in result_ids, (
            f"Document should be found when searching by OCR text"
        )
    
    @given(
        doc_data=valid_document_create_data(),
    )
    @settings(max_examples=10, deadline=None)
    @pytest.mark.asyncio
    async def test_search_returns_empty_for_no_matches(
        self,
        doc_data: dict,
    ):
        """For any search query that doesn't match any document content,
        the search SHALL return an empty list.
        
        **Validates: Requirements 6.7, 7.6**
        
        This test verifies that:
        1. Non-matching queries return empty results
        2. No false positives are returned
        """
        user_id = uuid4()
        
        # Create a document
        create_data = DocumentCreate(**doc_data)
        
        await self.service.create_document(
            user_id=user_id,
            data=create_data,
            file_path=f"documents/{uuid4()}.pdf",
            encryption_key="test-key",
        )
        
        # Search for a term that definitely won't match
        non_matching_query = "xyznonexistentterm123456789"
        
        results = await self.service.search(
            user_id=user_id,
            query=non_matching_query,
        )
        
        assert len(results) == 0, (
            f"Search for non-matching query '{non_matching_query}' should return empty results"
        )
