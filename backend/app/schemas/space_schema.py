from pydantic import BaseModel, ConfigDict
from uuid import UUID
from datetime import datetime
from typing import Dict, Any, Literal, List

type SpaceType = Literal["reference", "summary", "research"]
type UploadStatus = Literal["chat", "upload"]

# 1. Add the lightweight DocumentMeta schema
class DocumentMeta(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    filename: str

class SpaceBase(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    tool: SpaceType
    upload_status: UploadStatus
    created_at: datetime

class SpaceResponse(SpaceBase):
    data: Dict[str, Any] 
    documents: List[DocumentMeta] = []
    
class CreateSpace(BaseModel):
    tool: SpaceType
    name: str
    upload_status: UploadStatus
    
class SpacesRequest(BaseModel):
    tool: SpaceType