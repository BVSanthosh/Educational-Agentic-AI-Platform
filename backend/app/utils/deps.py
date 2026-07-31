from fastapi.security import OAuth2PasswordBearer
from fastapi import HTTPException, Depends, status
from typing import Annotated
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from app.core import get_db, env
from app.models import User
from app.utils import validate_token

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")

async def get_current_usr(token: Annotated[str, Depends(oauth2_scheme)], session: Annotated[AsyncSession, Depends(get_db)]) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Couldn't validate credentials"
    )

    payload = validate_token(token, env.ACCESS_TOKEN_TYPE)

    user_id_str = payload.get("id")
    if not user_id_str:
        raise credentials_exception

    try:
        user_id = UUID(user_id_str)
    except ValueError:
        raise credentials_exception

    user = await session.get(User, user_id)
    if not user:
        raise credentials_exception

    return user
