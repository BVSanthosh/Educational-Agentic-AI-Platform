from pydantic import BaseModel, Field
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
    subject_matter: str = Field(
        description="The detailed topic or prompt to research."
    )
    report_name: str = Field(
        description="A short, catchy, and highly descriptive filename for the report (e.g., 'Quantum_Computing_Q3_Analysis'). Do not include file extensions."
    )