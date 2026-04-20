"""Document router – upload, list, get, download, delete."""

import uuid
from typing import Annotated, Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, status
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import CurrentUser
from app.core import storage
from app.repositories.document import DocumentRepository
from app.schemas.document import (
    DocumentCategory,
    DocumentResponse,
    DocumentSearchResponse,
    PaginatedResponse,
    DocumentCreate,
    DocumentUpdate,
)

router = APIRouter()

MAX_FILE_SIZE = 20 * 1024 * 1024  # 20 MB


@router.post(
    "/upload",
    response_model=DocumentResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Upload a document",
)
async def upload_document(
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
    file: UploadFile = File(...),
    title: str = Form(...),
    category: str = Form(...),
    expiry_date: Optional[str] = Form(None),
) -> DocumentResponse:
    if category not in DocumentCategory.ALL:
        raise HTTPException(422, f"Category must be one of: {', '.join(DocumentCategory.ALL)}")

    file_data = await file.read()
    if len(file_data) > MAX_FILE_SIZE:
        raise HTTPException(413, "File too large. Maximum size is 20 MB.")
    if len(file_data) == 0:
        raise HTTPException(422, "Uploaded file is empty.")

    # Store on disk
    ext = (file.filename or "file").rsplit(".", 1)[-1] if file.filename else "bin"
    key = f"{current_user.id}/{uuid.uuid4().hex}.{ext}"
    await storage.upload_file(file_data, key, content_type=file.content_type or "application/octet-stream")

    # Persist metadata in DB
    from datetime import datetime, timezone
    parsed_expiry = None
    if expiry_date:
        try:
            parsed_expiry = datetime.fromisoformat(expiry_date).replace(tzinfo=timezone.utc)
        except ValueError:
            pass

    create_data = DocumentCreate(
        title=title,
        category=category,
        content_type=file.content_type or "application/octet-stream",
        file_size=len(file_data),
        expiry_date=parsed_expiry,
    )

    repo = DocumentRepository(db)
    doc = await repo.create_document(
        user_id=current_user.id,
        data=create_data,
        file_path=key,
        encryption_key="local",  # no encryption for local storage
    )
    await db.commit()
    await db.refresh(doc)
    return doc


@router.get(
    "",
    response_model=PaginatedResponse[DocumentResponse],
    summary="List documents",
)
async def list_documents(
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
    category: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
) -> PaginatedResponse[DocumentResponse]:
    repo = DocumentRepository(db)
    offset = (page - 1) * page_size

    if search:
        items = await repo.search_documents(current_user.id, search, category, page_size, offset)
        total = await repo.count_search_results(current_user.id, search, category)
    else:
        items = await repo.get_documents_by_user(current_user.id, category, page_size, offset)
        # For total count, fetch with large limit (simple approach without a separate count query)
        total = len(await repo.get_documents_by_user(current_user.id, category, limit=10000, offset=0))

    return PaginatedResponse.create(items=items, total=total, page=page, page_size=page_size)


@router.get(
    "/search",
    response_model=PaginatedResponse[DocumentSearchResponse],
    summary="Search documents",
)
async def search_documents(
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
    query: str = Query(..., min_length=1, max_length=500),
    category: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
) -> PaginatedResponse[DocumentSearchResponse]:
    if category and category not in DocumentCategory.ALL:
        raise HTTPException(422, f"Category must be one of: {', '.join(DocumentCategory.ALL)}")
    repo = DocumentRepository(db)
    offset = (page - 1) * page_size
    items = await repo.search_documents(current_user.id, query, category, page_size, offset)
    total = await repo.count_search_results(current_user.id, query, category)
    return PaginatedResponse.create(items=items, total=total, page=page, page_size=page_size)


@router.get(
    "/{document_id}",
    response_model=DocumentResponse,
    summary="Get document details",
)
async def get_document(
    document_id: uuid.UUID,
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> DocumentResponse:
    repo = DocumentRepository(db)
    doc = await repo.get_document_by_id(document_id, current_user.id)
    if not doc:
        raise HTTPException(404, "Document not found")
    return doc


@router.get(
    "/{document_id}/download",
    summary="Download document file",
)
async def download_document(
    document_id: uuid.UUID,
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    repo = DocumentRepository(db)
    doc = await repo.get_document_by_id(document_id, current_user.id)
    if not doc:
        raise HTTPException(404, "Document not found")

    try:
        file_data = await storage.download_file(doc.file_path)
    except FileNotFoundError:
        raise HTTPException(404, "File not found on disk")

    filename = doc.title.replace('"', "'")
    return Response(
        content=file_data,
        media_type=doc.content_type,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.delete(
    "/{document_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a document",
)
async def delete_document(
    document_id: uuid.UUID,
    current_user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    repo = DocumentRepository(db)
    doc = await repo.get_document_by_id(document_id, current_user.id)
    if not doc:
        raise HTTPException(404, "Document not found")

    # Delete file from disk
    await storage.delete_file(doc.file_path)

    # Delete DB record
    await repo.delete_document(doc)
    await db.commit()
