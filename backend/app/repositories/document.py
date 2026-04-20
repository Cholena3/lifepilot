"""Document repository for database operations.

Validates: Requirements 6.7
"""

from typing import List, Optional
from uuid import UUID

from sqlalchemy import or_, select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.document import Document, DocumentVersion
from app.schemas.document import DocumentCreate, DocumentUpdate


class DocumentRepository:
    """Repository for Document database operations.
    
    Validates: Requirements 6.7
    """
    
    def __init__(self, db: AsyncSession) -> None:
        """Initialize repository with database session.
        
        Args:
            db: Async database session
        """
        self.db = db
    
    async def create_document(
        self,
        user_id: UUID,
        data: DocumentCreate,
        file_path: str,
        encryption_key: str,
    ) -> Document:
        """Create a new document.
        
        Args:
            user_id: User's UUID
            data: Document creation data
            file_path: Path to the stored file
            encryption_key: Encryption key for the file
            
        Returns:
            Created Document model instance
        """
        document = Document(
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
        )
        self.db.add(document)
        await self.db.flush()
        await self.db.refresh(document)
        
        # Create initial version
        version = DocumentVersion(
            document_id=document.id,
            version_number=1,
            file_path=file_path,
            file_size=data.file_size,
            content_type=data.content_type,
        )
        self.db.add(version)
        await self.db.flush()
        
        return document
    
    async def get_document_by_id(
        self,
        document_id: UUID,
        user_id: Optional[UUID] = None,
    ) -> Optional[Document]:
        """Get a document by ID.
        
        Args:
            document_id: Document's UUID
            user_id: Optional user ID to filter by ownership
            
        Returns:
            Document if found, None otherwise
        """
        stmt = select(Document).where(Document.id == document_id)
        if user_id is not None:
            stmt = stmt.where(Document.user_id == user_id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()
    
    async def get_documents_by_user(
        self,
        user_id: UUID,
        category: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> List[Document]:
        """Get all documents for a user with optional filtering.
        
        Args:
            user_id: User's UUID
            category: Optional category filter
            limit: Maximum number of results
            offset: Number of results to skip
            
        Returns:
            List of Document model instances
        """
        stmt = select(Document).where(Document.user_id == user_id)
        
        if category is not None:
            stmt = stmt.where(Document.category == category)
        
        stmt = stmt.order_by(Document.updated_at.desc())
        stmt = stmt.limit(limit).offset(offset)
        
        result = await self.db.execute(stmt)
        return list(result.scalars().all())
    
    async def search_documents(
        self,
        user_id: UUID,
        query: str,
        category: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
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
            limit: Maximum number of results
            offset: Number of results to skip
            
        Returns:
            List of matching Document model instances
        """
        # Normalize the search query
        search_term = f"%{query.lower()}%"
        
        # Build the search query with ILIKE for case-insensitive matching
        stmt = select(Document).where(
            Document.user_id == user_id,
            or_(
                func.lower(Document.title).like(search_term),
                func.lower(Document.category).like(search_term),
                func.lower(Document.ocr_text).like(search_term),
            )
        )
        
        # Apply category filter if provided
        if category is not None:
            stmt = stmt.where(Document.category == category)
        
        # Order by relevance (title matches first, then by updated_at)
        # Using a simple ordering - title matches are typically more relevant
        stmt = stmt.order_by(Document.updated_at.desc())
        stmt = stmt.limit(limit).offset(offset)
        
        result = await self.db.execute(stmt)
        return list(result.scalars().all())
    
    async def count_search_results(
        self,
        user_id: UUID,
        query: str,
        category: Optional[str] = None,
    ) -> int:
        """Count total search results for pagination.
        
        Args:
            user_id: User's UUID
            query: Search query string
            category: Optional category filter
            
        Returns:
            Total count of matching documents
        """
        search_term = f"%{query.lower()}%"
        
        stmt = select(func.count(Document.id)).where(
            Document.user_id == user_id,
            or_(
                func.lower(Document.title).like(search_term),
                func.lower(Document.category).like(search_term),
                func.lower(Document.ocr_text).like(search_term),
            )
        )
        
        if category is not None:
            stmt = stmt.where(Document.category == category)
        
        result = await self.db.execute(stmt)
        return result.scalar() or 0
    
    async def update_document(
        self,
        document: Document,
        data: DocumentUpdate,
        new_file_path: Optional[str] = None,
    ) -> Document:
        """Update a document, optionally creating a new version.
        
        Args:
            document: Existing Document model instance
            data: Document update data
            new_file_path: Path to new file if content changed
            
        Returns:
            Updated Document model instance
        """
        # Update metadata
        update_data = data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            if field not in ("content_type", "file_size") or new_file_path is not None:
                setattr(document, field, value)
        
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
                document_id=document.id,
                version_number=document.current_version,
                file_path=new_file_path,
                file_size=data.file_size or document.file_size,
                content_type=data.content_type or document.content_type,
            )
            self.db.add(version)
        
        await self.db.flush()
        await self.db.refresh(document)
        return document
    
    async def update_ocr_text(
        self,
        document: Document,
        ocr_text: str,
    ) -> Document:
        """Update the OCR text for a document.
        
        Validates: Requirements 6.7, 7.2
        
        Args:
            document: Document model instance
            ocr_text: Extracted OCR text
            
        Returns:
            Updated Document model instance
        """
        document.ocr_text = ocr_text
        await self.db.flush()
        await self.db.refresh(document)
        return document
    
    async def delete_document(self, document: Document) -> None:
        """Delete a document and all its versions.
        
        Args:
            document: Document model instance to delete
        """
        await self.db.delete(document)
        await self.db.flush()
    
    async def get_version_history(
        self,
        document_id: UUID,
    ) -> List[DocumentVersion]:
        """Get all versions of a document.
        
        Args:
            document_id: Document's UUID
            
        Returns:
            List of DocumentVersion model instances ordered by version number
        """
        stmt = (
            select(DocumentVersion)
            .where(DocumentVersion.document_id == document_id)
            .order_by(DocumentVersion.version_number)
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())
