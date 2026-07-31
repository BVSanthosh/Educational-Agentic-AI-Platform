from pydantic import BaseModel
from uuid import UUID

class LoginCredentials(BaseModel):
    username: str
    password: str

class SignUpCredentials(BaseModel):
    username: str
    email: str
    password: str

class GoogleAuthRequest(BaseModel):
    code: str

class AuthResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user_id: UUID
    username: str
    email: str

class Tokens(BaseModel):
    access_token: str
    refresh_token: str