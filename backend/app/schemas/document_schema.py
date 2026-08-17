from uuid import UUID
from datetime import datetime
from pydantic import BaseModel

class DocumentResponse(BaseModel):
    id: UUID
    filename: str
    file_size_bytes: int
    mime_type: str
    created_at: datetime
    content: str

    class Config:
        from_attributes = True