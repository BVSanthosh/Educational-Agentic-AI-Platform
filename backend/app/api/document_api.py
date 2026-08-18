# app/routers/documents.py
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Annotated
from uuid import UUID
from app.models import Document, User
from app.core.database import get_db
from app.utils.deps import get_current_usr
from app.utils.s3_client import read_document_from_s3
from app.schemas import DocumentResponse

router = APIRouter(prefix="/api/documents", tags=["Documents"])

@router.get("/{document_id}", response_model=DocumentResponse)
async def get_document(
    document_id: UUID,
    current_user: Annotated[User, Depends(get_current_usr)],
    session: Annotated[AsyncSession, Depends(get_db)],
) -> DocumentResponse:
    # 1. Fetch document metadata and verify access
    query = select(Document).where(
        Document.id == document_id, 
        Document.user_id == current_user.id
    )
    document = (await session.scalars(query)).one_or_none()

    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found or unauthorized access."
        )

    # 2. Fetch full file content from S3
    try:
        markdown_text = await read_document_from_s3(document.file_path)
    except Exception as err:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to read file from storage: {str(err)}"
        )

    # 3. Return single JSON response with metadata and text
    return DocumentResponse(
        id=document.id,
        filename=document.filename,
        file_size_bytes=document.file_size_bytes,
        mime_type=document.mime_type,
        created_at=document.created_at,
        content=markdown_text,
    )