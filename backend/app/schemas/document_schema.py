from pydantic import BaseModel, ConfigDict
from uuid import UUID
from typing import Dict, Any, List
from datetime import datetime

# 1. Lightweight schema for the UI button
class DocumentMeta(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    filename: str

# 2. Heavy schema for the Right Panel
class DocumentFull(DocumentMeta):
    content: str

# 3. Space Response uses the lightweight metadata
class SpaceResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    name: str
    tool: str
    upload_status: str
    created_at: datetime
    data: Dict[str, Any]
    documents: List[DocumentMeta] = []