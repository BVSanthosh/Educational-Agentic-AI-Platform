import httpx
import uuid 
from fastapi import APIRouter, Depends, HTTPException, status, Response, Cookie
from typing import Annotated
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select 
from pwdlib import PasswordHash
from app.core import get_db, env
from app.models import User
from app.schemas import LoginCredentials, SignUpCredentials, AuthResponse, GoogleAuthRequest
from app.utils import create_tokens, validate_token
from app.utils.deps import get_current_usr

router = APIRouter(prefix="/api/auth", tags=["Auth"])

password_hash = PasswordHash.recommended()

def set_cookies(res: Response, refresh_token: str):
    res.set_cookie(
        key="refresh_token",
        value=refresh_token,
        httponly=True,
        secure=env.PRODUCTION,
        samesite="lax",
        path="/auth/refresh",
        max_age=env.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60
    )

@router.post("/login", response_model=AuthResponse)
async def login(cred: LoginCredentials, res: Response, session: Annotated[AsyncSession, Depends(get_db)]):
    query = select(User).where(User.username == cred.username)
    result = await session.scalars(query)
    user = result.one_or_none()

    if (
        not user
        or not user.password_hash
        or not password_hash.verify(cred.password, user.password_hash)
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    tokens = create_tokens(user)
    set_cookies(res, tokens.refresh_token)

    return AuthResponse(
        access_token=tokens.access_token,
        user_id=user.id,
        username=user.username,
        email=user.email
    )

@router.post("/signup", response_model=AuthResponse, status_code=status.HTTP_201_CREATED)
async def signup(cred: SignUpCredentials, res: Response, session: Annotated[AsyncSession, Depends(get_db)]):
    email_query = select(User).where(User.email == cred.email)
    existing_email = (await session.scalars(email_query)).one_or_none()

    if existing_email:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Account with this email already exists",
        )

    username_query = select(User).where(User.username == cred.username)
    existing_username = (await session.scalars(username_query)).one_or_none()

    if existing_username:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Username already taken",
        )

    user_data = cred.model_dump()
    raw_password = user_data.pop("password")
    print(f"PASSWORD: {raw_password}")
    new_user = User(
        **user_data,
        password_hash=password_hash.hash(raw_password)
    )

    session.add(new_user)
    await session.commit()
    await session.refresh(new_user)

    tokens = create_tokens(new_user)
    set_cookies(res, tokens.refresh_token)

    return AuthResponse(
        access_token=tokens.access_token,
        user_id=new_user.id,
        username=new_user.username,
        email=new_user.email
    )

@router.post("/refresh")
async def refresh_access_token(res: Response, session: Annotated[AsyncSession, Depends(get_db)], refresh_token: Annotated[str | None, Cookie()] = None):
    if not refresh_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token missing",
            headers={"WWW-Authenticate": "Bearer"},
        )
        
    payload = validate_token(refresh_token, env.REFRESH_TOKEN_TYPE)
    username = payload.get("sub")

    query = select(User).where(User.username == username)
    user = (await session.scalars(query)).one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"},
        )
        
    new_token = create_tokens(user)

    set_cookies(res, new_token.access_token)

    return new_token.refresh_token

@router.post("/logout")
async def logout(res: Response):
    res.delete_cookie(key="refresh_token", path="/auth/refresh")
    return {"detail": "Successfully logged out"}

@router.delete("/delete-account", status_code=status.HTTP_204_NO_CONTENT)
async def delete_account(
    current_user: User = Depends(get_current_usr),
    db: AsyncSession = Depends(get_db)
):
    """
    Permanently deletes the currently authenticated user.
    """
    try:
        await db.delete(current_user)
        await db.commit()
        
        return None
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete account: {str(e)}"
        )

@router.post("/google", response_model=AuthResponse)
async def google_auth(paylaod: GoogleAuthRequest, res: Response, session: Annotated[AsyncSession, Depends(get_db)]):
    token_url = "https://oauth2.googleapis.com/token"
    token_data = {
        "code": paylaod.code,
        "client_id": env.GOOGLE_CLIENT_ID,
        "client_secret": env.GOOGLE_CLIENT_SECRET,
        "redirect_uri": env.GOOGLE_REDIRECT_URI,
        "grant_type": "authorization_code"
    }

    async with httpx.AsyncClient() as client:
        token_res = await client.post(token_url, data=token_data)
        if token_res.status_code != 200:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to obtain tokens from Google"
            )

        google_tokens = token_res.json()
        access_token = google_tokens.get("access_token")

        user_info_res = await client.get(
            "https://www.googleapis.com/oauth2/v2/userinfo",
            headers={"Authorization": f"Bearer {access_token}"}
        )

        if user_info_res.status_code != 200:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Faield to obtain tokens from Google"
            )

        user_info = user_info_res.json()

    email = user_info.get("email", "")
    name = user_info.get("name", "")

    if not email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Faield to obtain tokens from Google"
        )

    query = select(User).where(User.email == email)
    user = (await session.scalars(query)).one_or_none()

    if not user:
        base_username = f"{email.split("@")[0]}_{uuid.uuid4().hex[:4]}"
        user = User(
            email=email,
            username=base_username,
            password_hash=None,
        )

        session.add(user)
        await session.commit()
        await session.refresh(user)

    tokens = create_tokens(user)
    set_cookies(res, tokens.refresh_token)

    return AuthResponse(
        access_token=tokens.access_token,
        user_id=user.id,
        username=user.username,
        email=user.email
    )