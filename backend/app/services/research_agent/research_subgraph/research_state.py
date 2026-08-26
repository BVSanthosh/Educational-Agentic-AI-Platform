import operator
from typing import TypedDict, Annotated, Literal
from langchain_core.messages import AnyMessage
from app.schemas.research_schema import Resource
 
class ResearchState(TypedDict):
    subject_matter: str
    outline: str
    search_queries: list[str]
    research_results: Annotated[list[Resource], operator.add]
    research_report: str
    feedback_result: Literal["PASS", "FAIL"]
    feedback_report: str
    rewrites: int

class ResearchOutputState(TypedDict):
    research_report: str

class Query(TypedDict): 
    query: str