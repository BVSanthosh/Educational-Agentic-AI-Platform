from pydantic import BaseModel

class SummaryRequest(BaseModel):
    user_input: str
    
class SummaryResponse(BaseModel):
    response: str