from fastapi import APIRouter, Depends, HTTPException, status
from typing import Annotated
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from typing import Dict, Any
from uuid import UUID
from app.schemas import SpaceResponse, SpaceBase, SpacesResponse
from app.core import get_db
from app.models import Space, User
from app.utils import get_current_usr 

REFERENCE = "Reference"
RESEEARCH = "Research"
SUMMARY = "Summary"
 
router = APIRouter(prefix="/space", tags=["Spaces"]) 

@router.get("/{space_id}", response_model=SpaceResponse)
async def get_space(space_id: UUID, session: Annotated[AsyncSession, Depends(get_db)], current_user: Annotated[User, Depends(get_current_usr)]):
    query = select(Space).where(Space.id == space_id, Space.user_id == current_user.id)
    space = (await session.scalars(query)).one_or_none()

    if not space:
        raise HTTPException( 
            status_code=status.HTTP_404_NOT_FOUND, 
            detail="Space not found"
        )
    
    return space

@router.get("/", response_model=list[SpacesResponse])
async def get_spaces(tool_type: str, session:Annotated[AsyncSession, Depends(get_db)], current_user: Annotated[User, Depends(get_current_usr)]):
    query = select(Space).where(Space.user_id == current_user.id, Space.tool_type == tool_type).order_by(Space.create_at)
    spaces = (await session.scalars(query)).all()

    return spaces

@router.post("/", status_code=status.HTTP_201_CREATED)
async def create_space(paylaod: SpaceBase, session: Annotated[AsyncSession, Depends(get_db)], current_user: Annotated[User, Depends(get_current_usr)]):
    new_space = Space(
        **paylaod.model_dump(),
        user_id=current_user.id
    )
    
    new_data = {}
    if paylaod.tool_type == RESEEARCH:
        new_data["messages"] = []
    elif paylaod.tool_type == SUMMARY:
        new_data["messages"] = []
        new_data["summary"] = ""
        new_data["status"] = ""
        
    new_space.data = new_data

    session.add(new_space)
    await session.commit()
    await session.refresh(new_space)

    return {"detail": "Space created successfully"}

@router.put("/{space_id}")
async def update_space(space_id: UUID, payload: Dict[Any, str], session: Annotated[AsyncSession, Depends(get_db)], current_user: Annotated[User, Depends(get_current_usr)]):
    query = update(Space).where(Space.id == space_id, Space.user_id == current_user.id).values(data=payload).returning(Space)
    updated_space = (await session.execute(query)).scalar_one_or_none()

    if not updated_space:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Space not found"
        )

    await session.commit()
    return {"detail": "Space updated successfully"}
            
@router.delete("/{space_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_space(space_id: UUID, session: Annotated[AsyncSession, Depends(get_db)], current_user: Annotated[User, Depends(get_current_usr)]):
    query = select(Space).where(Space.id == space_id, Space.user_id == current_user.id)
    space = (await session.scalars(query)).first()

    if not space:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail="Space not found"
        )

    await session.delete(space)
    await session.commit()
    return {"detail": "Space deleted successfully"}