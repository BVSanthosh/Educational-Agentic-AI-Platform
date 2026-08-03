from fastapi import APIRouter, HTTPException, Depends, status
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Annotated
from datetime import datetime, timezone
from psycopg_pool import AsyncConnectionPool
from uuid import UUID, uuid4
from app.schemas import ResearchInput, ResearchOutput
from app.services import stream_and_persist_research
from app.utils import get_current_usr
from app.models import User, Space
from app.core.database import get_db, get_checkpointer_pool


router = APIRouter(prefix="/research")
 
@router.post("/stream")
async def get_streamed_research(user_input: str, space_id: UUID, current_user: Annotated[User, Depends(get_current_usr)], session: Annotated[AsyncSession, Depends(get_db)], pool: Annotated[AsyncConnectionPool, Depends(get_checkpointer_pool)]) -> str:
    thread_query = select(Space.thread_id, Space.data).where(Space.id == space_id)
    thread_result = (await session.scalars(thread_query)).one_or_none()

    if not thread_result:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid space id"
        )

    new_message = {
        "id": str(uuid4()),
        "role": "user",
        "contet": user_input,
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    new_data = thread_result.data["messages"].append(new_message)

    messages_query = update(Space).where(Space.id == space_id).values(data=new_data).returning(Space)
    messages_result = (await session.execute(messages_query)).scalar_one_or_none()

    if not messages_result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Space not found"
        )

    await session.commit()
    
    report: str = await stream_and_persist_research(user_input, space_id, str(thread_result.thread_id), current_user.id, session, pool)
    
    return report

        