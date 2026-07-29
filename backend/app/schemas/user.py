from pydantic import BaseModel, ConfigDict
from uuid import UUID

class UserBase(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID

class CreateUser(UserBase):
    email: str
    password: str