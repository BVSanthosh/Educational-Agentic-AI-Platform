from fastapi import APIRouter, HTTPException, Depends, status
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from psycopg_pool import AsyncConnectionPool
from sqlalchemy import select
from typing import AsyncGenerator, Annotated
from uuid import UUID
from app.schemas import ReferenceOutput
from app.utils import get_current_usr
from app.core.database import get_db, get_checkpointer_pool
from app.models import User, Space
from app.services import stream_and_persist_reference, get_and_persist_reference

router = APIRouter(prefix="/references", tags=["References"]) 

@router.post("/stream", response_class=StreamingResponse)
async def get_streamed_references(user_input: str, space_id: UUID, current_user: Annotated[User, Depends(get_current_usr)], session: Annotated[AsyncSession, Depends(get_db)], pool: Annotated[AsyncConnectionPool, Depends(get_checkpointer_pool)]) -> StreamingResponse: 
    query = select(Space.thread_id).where(Space.id == space_id)
    thread_id = (await session.scalars(query)).one_or_none()

    if thread_id is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid space id"
        )
    
    stream_generator: AsyncGenerator[str, None] = stream_and_persist_reference(
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
            "X-Accel-Buffering": "no"
        }
    )

@router.post("", response_model=ReferenceOutput)
async def get_references(user_input: str, space_id: UUID, current_user: Annotated[User, Depends(get_current_usr)], session: Annotated[AsyncSession, Depends(get_db)], pool: Annotated[AsyncConnectionPool, Depends(get_checkpointer_pool)]) -> ReferenceOutput | None: 
    query = select(Space.thread_id).where(Space.id == space_id)
    thread_id = (await session.scalars(query)).one_or_none()

    if thread_id is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid space id"
            )
    
    response: ReferenceOutput | None = await get_and_persist_reference(
        user_input=user_input, 
        thread_id=str(thread_id), 
        space_id=space_id, 
        user_id=current_user.id, 
        db=session
    )

    return response
    