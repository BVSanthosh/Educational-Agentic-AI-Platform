from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete
from typing import Dict, Any
from uuid import UUID
from app.schemas import SpaceResponse, SpaceCreate, SpaceBase
from app.core import get_db
from app.models import Space

router = APIRouter(prefix="/space")

@router.get("/{space_id}", response_model=SpaceResponse)
async def get_space(space_id: UUID, session: AsyncSession = Depends(get_db)):
    query = (
        select(Space)
        .where(Space.id == space_id)
    )
    result = await session.scalars(query)
    space = result.one_or_none()

    if not space:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail="Space not found"
        )
    
    return space

@router.get("/", response_model=list[SpaceBase])
async def get_spaces(user_id: UUID, tool_type: str, session: AsyncSession = Depends(get_db)):
    query = (
        select(Space)
        .where(Space.user_id == user_id, Space.tool_type == tool_type)
        .order_by(Space.create_at)
    )
    result = await session.scalars(query)
    spaces = result.all()

    return spaces

@router.post("/", response_model=SpaceResponse, status_code=status.HTTP_201_CREATED)
async def create_space(paylaod: SpaceCreate, session: AsyncSession = Depends(get_db)):
    new_space = Space(**paylaod.model_dump())
    session.add(new_space)
    await session.commit()
    await session.refresh(new_space)

    return new_space

@router.put("/{space_id}", response_model=SpaceResponse)
async def update_space(space_id: UUID, payload: Dict[Any, str], session: AsyncSession = Depends(get_db)):
    query = (
        update(Space)
        .where(Space.id == space_id)
        .values(data=payload)
        .returning(Space)
    )
    result = await session.execute(query)
    updated_space = result.scalar_one_or_none()

    if not updated_space:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Space not found"
        )

    await session.commit()
    return updated_space
            
@router.delete("/{space_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_space(space_id: UUID, session: AsyncSession = Depends(get_db)):
    space = await session.get(Space, space_id)

    if not space:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail="Space not found"
        )

    await session.delete(space)
    await session.commit()
    return None