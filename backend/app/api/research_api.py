from fastapi import APIRouter, HTTPException, Depends, status
from fastapi.responses import StreamingResponse
from sqlalchemy import select, update, func
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Annotated, AsyncGenerator
from datetime import datetime, timezone
from psycopg_pool import AsyncConnectionPool
from uuid import UUID, uuid4
from app.schemas import  ResearchOutput
from app.services import stream_and_persist_research, get_and_persist_research
from app.utils import get_current_usr
from app.models import User, Space
from app.core.database import get_db, get_checkpointer_pool

router = APIRouter(prefix="/research", tags=["Research"])
 
@router.post("/stream")
async def get_streamed_research(user_input: str, space_id: UUID, current_user: Annotated[User, Depends(get_current_usr)], session: Annotated[AsyncSession, Depends(get_db)], pool: Annotated[AsyncConnectionPool, Depends(get_checkpointer_pool)]) -> StreamingResponse:
    space_query = select(Space.thread_id).where(Space.id == space_id)
    thread_id = (await session.scalars(space_query)).one_or_none()

    if not thread_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Space not found or unauthorized"
        )

    new_message = {
        "id": str(uuid4()),
        "role": "user",
        "contet": user_input,
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    
    try:
        update_messages_query = (
            update(Space)
            .where(Space.id == space_id)
            .values(
                data=func.jsonb_insert(
                    Space.data,
                    "{messages, -1}",
                    func.to_jsonb(new_message),
                    True
                ),
                updated_at=func.now()
            )
        )
            
        await session.execute(update_messages_query)
        await session.commit()
    except Exception as db_err:
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to save user message: {str(db_err)}"
        )
        
    
    stream_generator: AsyncGenerator[str,None] = stream_and_persist_research(
        user_input=user_input,
        thread_id=str(thread_id),
        space_id=space_id,
        user_id=current_user.id,
        db=session
    )
    
    return StreamingResponse(
        stream_generator, 
        media_type="text/event_stream",
        headers={
            "Cache-Control": "no-cache, no-transform",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"  # Critical for Nginx proxy streaming!
        }
    )

@router.post("", response_model=ResearchOutput)
async def create_research_report(user_input: str, space_id: UUID, current_user: Annotated[User, Depends(get_current_usr)], session: Annotated[AsyncSession, Depends(get_db)]) -> ResearchOutput:
    space_query = select(Space.thread_id).where(
        Space.id == space_id, 
        Space.user_id == current_user.id
    )
    thread_id = (await session.scalars(space_query)).one_or_none()

    if not thread_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Space not found or unauthorized"
        )

    new_message = {
        "id": str(uuid4()),
        "role": "user",
        "content": user_input,
        "created_at": datetime.now(timezone.utc).isoformat()
    }

    try:
        update_user_msg_query = (
            update(Space)
            .where(Space.id == space_id, Space.user_id == current_user.id)
            .values(
                data=func.jsonb_insert(
                    Space.data,
                    "{messages, -1}",
                    func.to_jsonb(new_message),
                    True
                ),
                updated_at=func.now()
            )
        )
        await session.execute(update_user_msg_query)
        await session.commit()
    except Exception as db_err:
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to save user message: {str(db_err)}"
        )

    report_content = await get_and_persist_research(
        user_input=user_input,
        thread_id=str(thread_id),
        space_id=space_id,
        user_id=current_user.id,
        db=session
    )

    return ResearchOutput(research_report=report_content)      