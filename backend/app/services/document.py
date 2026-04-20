"""Document service for managing documents and version history.

Provides functionality for document CRUD operations, version tracking,
and full-text search.

Validates: Requirements 6.7
"""

from datetime import datetime, timezone
from typing import List, Optional
from uuid import UUID, uuid4

from app.models.document import Document, DocumentVersion
from app.schemas.document import (
    DocumentCreate,
    DocumentUpdate,
    DocumentResponse,
    DocumentVersionResponse,
    VersionHistoryResponse,
)


class DocumentService:
    """Service for managing documents and their versions.
    
    Handles document creation, updates (with versioning), retrieval
    of version history, and full-text search.
    
    Validates: Requirements 6.7
    """
    
    def __init__(self):
        """Initialize the document service."""
        # In-memory storage for testing purposes
        # In production, this would use a repository with database access
        self._documents: dict[UUID, Document] = {}
        self._versions: dict[UUID, List[DocumentVersion]] = {}
    
    async def create_document(
        self,
        user_id: UUID,
        data: DocumentCreate,
        file_path: str,
        encryption_key: str,
    ) -> Document:
        """Create a new document with initial version.
        
        Args:
            user_id: ID of the user creating the document
            data: Document creation data
            file_path: Path to the stored file
            encryption_key: Encryption key for the file
            
        Returns:
            The created document
        """
        doc_id = uuid4()
        now = datetime.now(timezone.utc)
        
        # Create the document
        document = Document(
            id=doc_id,
            user_id=user_id,
            title=data.title,
            category=data.category,
            file_path=file_path,
            content_type=data.content_type,
            file_size=data.file_size,
            encryption_key=encryption_key,
            expiry_date=data.expiry_date,
            is_expired=False,
            current_version=1,
            created_at=now,
            updated_at=now,
        )
        
        # Create the initial version
        version = DocumentVersion(
            id=uuid4(),
            document_id=doc_id,
            version_number=1,
            file_path=file_path,
            file_size=data.file_size,
            content_type=data.content_type,
            created_at=now,
        )
        
        # Store in memory
        self._documents[doc_id] = document
        self._versions[doc_id] = [version]
        
        return document
    
    async def update_document(
        self,
        document_id: UUID,
        data: DocumentUpdate,
        new_file_path: Optional[str] = None,
    ) -> Document:
        """Update a document, creating a new version if file content changes.
        
        Args:
            document_id: ID of the document to update
            data: Update data
            new_file_path: Path to new file if content changed
            
        Returns:
            The updated document
            
        Raises:
            ValueError: If document not found
        """
        if document_id not in self._documents:
            raise ValueError(f"Document {document_id} not found")
        
        document = self._documents[document_id]
        now = datetime.now(timezone.utc)
        
        # Update metadata
        if data.title is not None:
            document.title = data.title
        if data.category is not None:
            document.category = data.category
        if data.expiry_date is not None:
            document.expiry_date = data.expiry_date
        
        # If file content changed, create new version
        if new_file_path is not None:
            document.current_version += 1
            document.file_path = new_file_path
            
            if data.content_type is not None:
                document.content_type = data.content_type
            if data.file_size is not None:
                document.file_size = data.file_size
            
            # Create new version
            version = DocumentVersion(
                id=uuid4(),
                document_id=document_id,
                version_number=document.current_version,
                file_path=new_file_path,
                file_size=data.file_size or document.file_size,
                content_type=data.content_type or document.content_type,
                created_at=now,
            )
            
            self._versions[document_id].append(version)
        
        document.updated_at = now
        return document
    
    async def get_document(self, document_id: UUID) -> Optional[Document]:
        """Get a document by ID.
        
        Args:
            document_id: ID of the document
            
        Returns:
            The document if found, None otherwise
        """
        return self._documents.get(document_id)
    
    async def get_version_history(
        self,
        document_id: UUID,
    ) -> VersionHistoryResponse:
        """Get the version history for a document.
        
        Returns all versions in chronological order with timestamps.
        
        Args:
            document_id: ID of the document
            
        Returns:
            Version history response with all versions
            
        Raises:
            ValueError: If document not found
        """
        if document_id not in self._documents:
            raise ValueError(f"Document {document_id} not found")
        
        versions = self._versions.get(document_id, [])
        
        # Sort by version number (chronological order)
        sorted_versions = sorted(versions, key=lambda v: v.version_number)
        
        version_responses = [
            DocumentVersionResponse(
                id=v.id,
                document_id=v.document_id,
                version_number=v.version_number,
                file_path=v.file_path,
                file_size=v.file_size,
                content_type=v.content_type,
                created_at=v.created_at,
            )
            for v in sorted_versions
        ]
        
        return VersionHistoryResponse(
            document_id=document_id,
            total_versions=len(version_responses),
            versions=version_responses,
        )
    
    async def get_version(
        self,
        document_id: UUID,
        version_number: int,
    ) -> Optional[DocumentVersion]:
        """Get a specific version of a document.
        
        Args:
            document_id: ID of the document
            version_number: Version number to retrieve
            
        Returns:
            The version if found, None otherwise
        """
        if document_id not in self._versions:
            return None
        
        for version in self._versions[document_id]:
            if version.version_number == version_number:
                return version
        
        return None
    
    def clear(self):
        """Clear all documents and versions (for testing)."""
        self._documents.clear()
        self._versions.clear()
    
    async def search(
        self,
        user_id: UUID,
        query: str,
        category: Optional[str] = None,
    ) -> List[Document]:
        """Search documents by full-text search across metadata and OCR content.
        
        Validates: Requirements 6.7
        
        Searches across:
        - Document title
        - Document category
        - OCR extracted text
        
        Args:
            user_id: User's UUID
            query: Search query string
            category: Optional category filter
            
        Returns:
            List of matching Document model instances
        """
        query_lower = query.lower()
        results = []
        
        for doc in self._documents.values():
            # Only search user's own documents
            if doc.user_id != user_id:
                continue
            
            # Apply category filter if provided
            if category is not None and doc.category != category:
                continue
            
            # Search in title
            if query_lower in doc.title.lower():
                results.append(doc)
                continue
            
            # Search in category
            if query_lower in doc.category.lower():
                results.append(doc)
                continue
            
            # Search in OCR text
            if doc.ocr_text and query_lower in doc.ocr_text.lower():
                results.append(doc)
                continue
        
        # Sort by updated_at descending
        results.sort(key=lambda d: d.updated_at, reverse=True)
        
        return results


# Singleton instance for use across the application
document_service = DocumentService()
