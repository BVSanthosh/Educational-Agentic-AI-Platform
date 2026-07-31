from pydantic import BaseModel, ConfigDict
from uuid import UUID
from typing import Dict, Any 

class SpaceBase(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    name: str
    tool_type: str

class SpacesResponse(SpaceBase):
    id: UUID

class SpaceResponse(SpaceBase):
    id: UUID
    data: Dict[str, Any] 