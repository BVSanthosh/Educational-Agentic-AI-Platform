from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from typing import AsyncGenerator
from services import get_stream_generator
from schemas import ReferencesOutput

router = APIRouter(prefix="/references")

@router.post("/")
async def get_document(query: str, num_of_refs: int) -> StreamingResponse: 
    """
    Generates a list of references

    Args:
        topic: User-provided topic that the referneces should be about 

    Returns:
        references: A list of references
    """
    
    if str == None:
        raise HTTPException(status_code=400, detail="No topic provided")
    
    input: str = f"query: {query}. resources: {num_of_refs}"

    stream_generator: AsyncGenerator[str, None] = get_stream_generator(input)

    return StreamingResponse(stream_generator, media_type="text/event_stream")
    