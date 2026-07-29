from pydantic import BaseModel, ConfigDict, Field
from uuid import UUID
from typing import Dict, Any 
from sqlalchemy import select, update, delete

class SpaceBase(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str

class SpaceCreate(SpaceBase):
    pass

class SpaceResponse(SpaceBase):
    data: Dict[str, Any] 