from pydantic import BaseModel
from typing import Literal

class ResearchRequest(BaseModel): 
    user_input: str

# Not being used for now since only a string is being returned from the backend
class ResearchResponse(BaseModel):
    response: str

class OutlineSchema(BaseModel):
    outline: str
    search_queries: list[str]

class Resource(BaseModel):
    url: str
    title: str
    contents: str 

class Draft(BaseModel):
    report_draft: str

class Feedback(BaseModel):
    result: Literal["PASS", "FAIL"]
    feedback: str

class ResarchSubject(BaseModel):
    subject_matter: str