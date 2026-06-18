from pydantic import BaseModel
from typing import Union

class Reference(BaseModel):
    tile: str
    link: str

class ReferencesOutput(BaseModel):
    description: str
    references: Union[list[Reference], None]