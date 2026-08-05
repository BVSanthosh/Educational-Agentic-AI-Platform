import tempfile
import shutil
from fastapi import Depends, HTTPException, status
from uuid import UUID, uuid4
from datetime import datetime, timezone
from typing import Annotated
from fastapi import APIRouter, UploadFile, BackgroundTasks, HTTPException
from sqlalchemy import select, update, func
from sqlalchemy.ext.asyncio import AsyncSession
from app.services.summary_agent.ingestion_pipeline import embed_and_summarise
from app.services.summary_agent.summary_agent import get_answer_and_persist
from app.utils import get_current_usr
from app.core.database import get_db
from app.models import User,Space
 
router = APIRouter(prefix="/summary", tags=["Summary"])

@router.post("/uploadfile")
async def upload_summary(file: UploadFile, space_id: UUID, background_task: BackgroundTasks, current_user: Annotated[User, Depends(get_current_usr)], session: Annotated[AsyncSession, Depends(get_db)]):
    space_query = select(Space).where(Space.id == space_id, Space.user_id == current_user.id)
    space = (await session.scalars(space_query)).one_or_none()
    
    if not space:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Space couldn't be found"
        )
        
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
        shutil.copyfileobj(file.file, tmp)
        tmp_path = tmp.name

    filename = file.filename or "uploaded_document.pdf"
    
    try:
        update_status_query = (
            update(Space)
            .where(Space.id == space_id, Space.user_id == current_user.id)
            .values(
                data=func.jsonb_set(
                    Space.data,
                    "{status}",
                    func.to_jsonb("processing"),
                    True
                ),
                updated_at=func.now()
            )
        )
        
        await session.execute(update_status_query)
        await session.commit()
    except Exception as db_err:
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update processing status: {str(db_err)}",
        )
    
    background_task.add_task(
        embed_and_summarise, 
        filename,
        tmp_path,
        space.id,
        current_user.id
    )
    
    return {
        "space_id": space.id,
        "status": "processing",
        "message": "File uploaded and processing started." 
    }
    
@router.get("/{space_id}/status")
async def get_space_status(space_id: UUID, current_user: Annotated[User, Depends(get_current_usr)], session: Annotated[AsyncSession, Depends(get_db)]):
    space_query = select(Space).where(Space.id == space_id, Space.user_id == current_user.id)
    space = (await session.scalars(space_query)).one_or_none()
    
    if not space:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Space couldn't be found"
        )
    
    return {
        "space_id": space.id,
        "status": space.data.get("status", ""),
        "messages": space.data.get("messages", [])
    }
            
@router.post("/query")
async def answer_query(query: str, space_id: UUID, current_user: Annotated[User, Depends(get_current_usr)], session: Annotated[AsyncSession, Depends(get_db)]):
    space_query = select(Space).where(Space.id == space_id, Space.user_id == current_user.id)
    space = (await session.scalars(space_query)).one_or_none()
    
    if not space:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Space couldn't be found"
        )
        
    user_message = {
        "id": uuid4(),
        "role": "user",
        "content": query,
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    
    try:
        update_user_message = (
            update(Space)
            .where(Space.id == space_id, Space.user_id == current_user.id)
            .values(
                data=func.set_jsonb(
                    Space.data,
                    {"messages", -1},
                    func.to_jsonb(user_message),
                    True
                ),
                updated_at=func.now()
            )
        )
        await session.execute(update_user_message)
        await session.commit()
    except Exception as db_err:
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to persist user input: {str(db_err)}"
        )

    response = await get_answer_and_persist(
        query, 
        current_user.id, 
        space_id, 
        session
    )
    
    return response