from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from typing import AsyncGenerator
from services import get_stream_generator
from schemas import References
 
router = APIRouter(prefix="/references")

@router.post("/", response_model=StreamingResponse)
async def get_references(req: References) -> StreamingResponse: 
    """
    Generates a list of references

    Args:
        topic: User-provided topic that the referneces should be about 

    Returns:
        references: A list of references
    """
    
    if str == None:
        raise HTTPException(status_code=400, detail="No topic provided")
    
    input: str = f"query: {req.query}. resources: {req.num_of_refs}"

    stream_generator: AsyncGenerator[str, None] = get_stream_generator(input)

    return StreamingResponse(stream_generator, media_type="text/event_stream")
    