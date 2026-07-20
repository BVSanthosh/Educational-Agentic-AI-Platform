from pydantic import BaseModel
from typing import Union, Literal

class Resource(BaseModel):
    tile: str
    url: str

class ReferenceOutput(BaseModel):
    description: str
    references: Union[list[Resource], None]

class ReferenceInput(BaseModel):
    query: str
    num_of_refs: int

class TavilySearchInput(BaseModel):
    query: str
    topic: Literal["general", "news", "finance"] = "general"
    max_results: int = 5
    time_range: Literal["day", "week", "month", "year"] | None = None
    include_domains: list[str] | None = None
    search_depth: Literal['basic', 'advanced', 'fast', 'ultra-fast'] = "basic"

class TavilySearchOutput(BaseModel):
    title: str
    url: str
    content: str
    score: int
    raw_content: str

class TavilySearchError(BaseModel):
    error: str