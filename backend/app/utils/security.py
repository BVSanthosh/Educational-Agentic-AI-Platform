import jwt
from fastapi import HTTPException, status
from datetime import datetime, timedelta, timezone
from uuid import UUID
from jwt.exceptions import InvalidTokenError, ExpiredSignatureError
from app.core.config import env
from app.models import User
from app.schemas import Tokens

def create_tokens(user: User):
    access_token = create_access_token(user.username, user.id)
    refresh_token = create_refresh_token(user.username, user.id)

    return Tokens(access_token=access_token, refresh_token=refresh_token)

def create_access_token(username: str, id: UUID):
    now = datetime.now(timezone.utc)
    payload = {
        "sub": username,
        "id": str(id),
        "type": env.ACCESS_TOKEN_TYPE,
        "iat": now,
        "exp": now + timedelta(minutes=env.ACCESS_TOKEN_EXPIRE_MINUTES)
    }

    token = jwt.encode(payload, env.SECRET_KEY, algorithm=env.ALGORITHM)
    return token

def create_refresh_token(username: str, id: UUID):
    now = datetime.now(timezone.utc)
    payload = {
        "sub": username,
        "id": str(id),
        "type": env.REFRESH_TOKEN_TYPE,
        "iat": now,
        "exp": now + timedelta(days=env.REFRESH_TOKEN_EXPIRE_DAYS)
    }

    token = jwt.encode(payload, env.SECRET_KEY, algorithm=env.ALGORITHM)
    return token

def validate_token(token: str, expected_type: str = env.ACCESS_TOKEN_TYPE):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Couldn't validate credentials"
    )
    try:
        payload = jwt.decode(token, env.SECRET_KEY, algorithms=[env.ALGORITHM])

        if payload.get("type") != expected_type:
            raise credentials_exception
        
        return payload
    except ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired"
        )
    except InvalidTokenError:
        raise credentials_exception