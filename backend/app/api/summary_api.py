import tempfile
import shutil
from fastapi import File, UploadFile, Form, HTTPException, status,Depends
from fastapi.responses import StreamingResponse
from uuid import UUID, uuid4
from datetime import datetime, timezone
from typing import Annotated, AsyncGenerator
from fastapi import APIRouter, UploadFile, HTTPException
from sqlalchemy import select, update, func, String, cast
from sqlalchemy.dialects.postgresql import JSONB, ARRAY
from sqlalchemy.ext.asyncio import AsyncSession
from app.services.summary_agent.ingestion_pipeline import stream_embed_and_summarise
from app.services.summary_agent.summary_agent import stream_get_answer_and_persist
from app.utils import get_current_usr
from app.core.database import get_db
from app.models import User, Space 
from app.schemas import SummaryRequest
  
router = APIRouter(prefix="/api/summary", tags=["Summary"])

@router.post("/uploadfile")
async def upload_summary(
    current_user: Annotated[User, Depends(get_current_usr)], 
    session: Annotated[AsyncSession, Depends(get_db)],
    file: UploadFile = File(...), 
    space_id: UUID = Form(...)
) -> StreamingResponse:
    
    # 1. Verify the Space exists
    space_query = select(Space).where(Space.id == space_id, Space.user_id == current_user.id)
    space = (await session.scalars(space_query)).one_or_none()
    
    if not space:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Space couldn't be found"
        )
        
    # 2. Save the uploaded file to a temporary location
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
        shutil.copyfileobj(file.file, tmp)
        tmp_path = tmp.name

    filename = file.filename or "uploaded_document.pdf"
    
    # 3. Update the space status to 'processing'
    try:
        update_status_query = (
            update(Space)
            .where(Space.id == space_id, Space.user_id == current_user.id)
            .values(
                data=func.jsonb_set(
                    Space.data,
                    cast(["status"], ARRAY(String)),
                    cast('"processing"', JSONB), # Fixed JSON string formatting
                    True  
                ),
                updated_at=func.now(),
                upload_status="chat"
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
    
    # 4. Return the streaming response (This replaces the Background Task)
    return StreamingResponse(
        stream_embed_and_summarise(filename, tmp_path, space.id, current_user.id),
        media_type="text/event_stream",
        headers={
            "Cache-Control": "no-cache, no-transform",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )
            
@router.post("/{space_id}/query")
async def answer_query(
    space_id: UUID, 
    body: SummaryRequest, 
    current_user: Annotated[User, Depends(get_current_usr)], 
    session: Annotated[AsyncSession, Depends(get_db)]
) -> StreamingResponse:
    
    # 1. Verify Space exists
    space_query = select(Space).where(Space.id == space_id, Space.user_id == current_user.id)
    space = (await session.scalars(space_query)).one_or_none()
    
    if not space:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Space couldn't be found"
        )
        
    # 2. Persist the User's message to the database immediately
    user_message = {
        "id": str(uuid4()),
        "role": "user",
        "content": body.user_input,
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    
    try:
        update_user_message = (
            update(Space)
            .where(Space.id == space_id, Space.user_id == current_user.id)
            .values(
                data=func.jsonb_insert(
                    Space.data, 
                    cast(["messages", "-1"], ARRAY(String)),
                    cast(user_message, JSONB),
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
        
    stream_generator: AsyncGenerator[str, None] = stream_get_answer_and_persist(
        user_input=body.user_input,
        user_id=current_user.id,
        space_id=space_id,
        thread_id=str(space.thread_id)
    )

    # 3. Return the Streaming Response
    return StreamingResponse(
        stream_generator,
        media_type="text/event_stream",
        headers={
            "Cache-Control": "no-cache, no-transform",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )