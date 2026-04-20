"""Database-backed document service for managing documents.

Provides functionality for document CRUD operations, version tracking,
and full-text search.

Validates: Requirements 6.7
"""

from typing import List, Optional
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError
from app.models.document import Document
from app.repositories.document import DocumentRepository
from app.schemas.document import (
    DocumentCreate,
    DocumentUpdate,
    DocumentResponse,
    DocumentSearchResponse,
    DocumentSearchQuery,
    PaginatedResponse,
    VersionHistoryResponse,
    DocumentVersionResponse,
)


class DocumentDBService:
    """Database-backed service for document management operations.
    
    Validates: Requirements 6.7
    """
    
    def __init__(self, db: AsyncSession) -> None:
        """Initialize service with database session.
        
        Args:
            db: Async database session
        """
        self.db = db
        self.repo = DocumentRepository(db)
    
    async def create_document(
        self,
        user_id: UUID,
        data: DocumentCreate,
        file_path: str,
        encryption_key: str,
    ) -> DocumentResponse:
        """Create a new document with initial version.
        
        Args:
            user_id: ID of the user creating the document
            data: Document creation data
            file_path: Path to the stored file
            encryption_key: Encryption key for the file
            
        Returns:
            DocumentResponse with created document data
        """
        document = await self.repo.create_document(
            user_id=user_id,
            data=data,
            file_path=file_path,
            encryption_key=encryption_key,
        )
        return DocumentResponse.model_validate(document)
    
    async def get_document(
        self,
        user_id: UUID,
        document_id: UUID,
    ) -> DocumentResponse:
        """Get a document by ID.
        
        Args:
            user_id: User's UUID (for ownership verification)
            document_id: Document's UUID
            
        Returns:
            DocumentResponse with document data
            
        Raises:
            NotFoundError: If document not found or not owned by user
        """
        document = await self.repo.get_document_by_id(document_id, user_id)
        if not document:
            raise NotFoundError(resource="Document", identifier=str(document_id))
        return DocumentResponse.model_validate(document)
    
    async def list_documents(
        self,
        user_id: UUID,
        category: Optional[str] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> PaginatedResponse[DocumentResponse]:
        """List documents for a user with optional filtering.
        
        Args:
            user_id: User's UUID
            category: Optional category filter
            page: Page number (1-indexed)
            page_size: Number of results per page
            
        Returns:
            PaginatedResponse with list of documents
        """
        offset = (page - 1) * page_size
        
        documents = await self.repo.get_documents_by_user(
            user_id=user_id,
            category=category,
            limit=page_size,
            offset=offset,
        )
        
        # Get total count for pagination
        # For simplicity, we'll estimate based on returned results
        # In production, you'd want a separate count query
        total = len(documents) + offset
        if len(documents) == page_size:
            # There might be more results
            total = offset + page_size + 1  # Indicate there's at least one more
        
        items = [DocumentResponse.model_validate(doc) for doc in documents]
        
        return PaginatedResponse.create(
            items=items,
            total=total,
            page=page,
            page_size=page_size,
        )
    
    async def search(
        self,
        user_id: UUID,
        query: str,
        category: Optional[str] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> PaginatedResponse[DocumentSearchResponse]:
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
            page: Page number (1-indexed)
            page_size: Number of results per page
            
        Returns:
            PaginatedResponse with list of matching documents
        """
        offset = (page - 1) * page_size
        
        # Get search results
        documents = await self.repo.search_documents(
            user_id=user_id,
            query=query,
            category=category,
            limit=page_size,
            offset=offset,
        )
        
        # Get total count for pagination
        total = await self.repo.count_search_results(
            user_id=user_id,
            query=query,
            category=category,
        )
        
        items = [DocumentSearchResponse.model_validate(doc) for doc in documents]
        
        return PaginatedResponse.create(
            items=items,
            total=total,
            page=page,
            page_size=page_size,
        )
    
    async def update_document(
        self,
        user_id: UUID,
        document_id: UUID,
        data: DocumentUpdate,
        new_file_path: Optional[str] = None,
    ) -> DocumentResponse:
        """Update a document, creating a new version if file content changes.
        
        Args:
            user_id: User's UUID (for ownership verification)
            document_id: Document's UUID
            data: Update data
            new_file_path: Path to new file if content changed
            
        Returns:
            DocumentResponse with updated document data
            
        Raises:
            NotFoundError: If document not found or not owned by user
        """
        document = await self.repo.get_document_by_id(document_id, user_id)
        if not document:
            raise NotFoundError(resource="Document", identifier=str(document_id))
        
        updated_document = await self.repo.update_document(
            document=document,
            data=data,
            new_file_path=new_file_path,
        )
        
        return DocumentResponse.model_validate(updated_document)
    
    async def update_ocr_text(
        self,
        user_id: UUID,
        document_id: UUID,
        ocr_text: str,
    ) -> DocumentResponse:
        """Update the OCR text for a document.
        
        Validates: Requirements 6.7, 7.2
        
        Args:
            user_id: User's UUID (for ownership verification)
            document_id: Document's UUID
            ocr_text: Extracted OCR text
            
        Returns:
            DocumentResponse with updated document data
            
        Raises:
            NotFoundError: If document not found or not owned by user
        """
        document = await self.repo.get_document_by_id(document_id, user_id)
        if not document:
            raise NotFoundError(resource="Document", identifier=str(document_id))
        
        updated_document = await self.repo.update_ocr_text(
            document=document,
            ocr_text=ocr_text,
        )
        
        return DocumentResponse.model_validate(updated_document)
    
    async def delete_document(
        self,
        user_id: UUID,
        document_id: UUID,
    ) -> None:
        """Delete a document and all its versions.
        
        Args:
            user_id: User's UUID (for ownership verification)
            document_id: Document's UUID
            
        Raises:
            NotFoundError: If document not found or not owned by user
        """
        document = await self.repo.get_document_by_id(document_id, user_id)
        if not document:
            raise NotFoundError(resource="Document", identifier=str(document_id))
        
        await self.repo.delete_document(document)
    
    async def get_version_history(
        self,
        user_id: UUID,
        document_id: UUID,
    ) -> VersionHistoryResponse:
        """Get the version history for a document.
        
        Args:
            user_id: User's UUID (for ownership verification)
            document_id: Document's UUID
            
        Returns:
            VersionHistoryResponse with all versions
            
        Raises:
            NotFoundError: If document not found or not owned by user
        """
        document = await self.repo.get_document_by_id(document_id, user_id)
        if not document:
            raise NotFoundError(resource="Document", identifier=str(document_id))
        
        versions = await self.repo.get_version_history(document_id)
        
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
            for v in versions
        ]
        
        return VersionHistoryResponse(
            document_id=document_id,
            total_versions=len(version_responses),
            versions=version_responses,
        )
