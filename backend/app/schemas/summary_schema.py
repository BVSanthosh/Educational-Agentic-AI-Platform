from pydantic import BaseModel

class SummaryInput(BaseModel):
    query: str
    doc_id: str