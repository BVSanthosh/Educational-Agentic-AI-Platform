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
from app.schemas import DocumentFull

router = APIRouter(prefix="/api/documents", tags=["Documents"])

@router.get("/{document_id}", response_model=DocumentFull)
async def get_document(
    document_id: UUID,
    current_user: Annotated[User, Depends(get_current_usr)],
    session: Annotated[AsyncSession, Depends(get_db)],
):
    query = select(Document).where(
        Document.id == document_id, 
        Document.user_id == current_user.id
    )
    document = (await session.scalars(query)).one_or_none()
  
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")

    markdown_text = await read_document_from_s3(document.file_path)

    return DocumentFull(
        id=document.id,
        filename=document.filename,
        content=markdown_text,
    )