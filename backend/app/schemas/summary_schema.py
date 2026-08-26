from pydantic import BaseModel
from uuid import UUID

class SummaryRequest(BaseModel):
    user_input: str
    
class SummaryResponse(BaseModel):
    response: str
    
class PresignedUrlRequest(BaseModel):
    filename: str
    content_type: str
    space_id: UUID

class ProcessS3DocumentRequest(BaseModel):
    s3_key: str
    filename: str
    space_id: UUID