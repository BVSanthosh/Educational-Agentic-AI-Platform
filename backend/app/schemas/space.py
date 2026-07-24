from pydantic import BaseModel, ConfigDict, Field
from uuid import UUID
from datetime import datetime
from typing import Dict, Any, Literal

class SpaceBase(BaseModel):
    tool_type: Literal["reference", "research", "summary"] = Field(...)
    data: Dict[str, Any] = Field(default=dict())

class SpaceCreate(SpaceBase):
    pass

class SpaceResponse(SpaceBase):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: UUID
    created_at: datetime
    updated_at: datetime