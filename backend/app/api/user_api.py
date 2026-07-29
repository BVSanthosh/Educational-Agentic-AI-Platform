from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pwdlib import PasswordHash
from app.core import get_db
from app.models import User
from app.schemas import UserBase, CreateUser

router = APIRouter(prefix="/user")

password_hash = PasswordHash.recommended()

@router.get("/login", response_model=UserBase)
async def login(email: str, password: str, session: AsyncSession = Depends(get_db)):
    if not email or not password:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Login credentials missing")

    query = (
        select(User)
        .where(User.email == email)
    )
    result = await session.scalars(query)
    user = result.first()

    if not user or not password_hash.verify(password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid login credentials"
        )
    
    return user

@router.post("/signup", response_model=UserBase)
async def signup(credentials: CreateUser, session: AsyncSession = Depends(get_db)):
    hash = password_hash.hash(credentials.password)
    credentials.password = hash

    new_user = User(**credentials.model_dump())

    session.add(new_user)
    await session.commit()
    await session.refresh(new_user)

    return new_user