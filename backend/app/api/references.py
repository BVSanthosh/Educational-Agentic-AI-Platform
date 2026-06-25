from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from typing import AsyncGenerator
from app.services import get_response_stream, get_response
from app.schemas import References, AgentOutput
 
router = APIRouter(prefix="/references")

@router.post("/stream", response_class=StreamingResponse)
async def get_streamed_references(req: References) -> StreamingResponse: 
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

    stream_generator: AsyncGenerator[str, None] = get_response_stream(input)

    return StreamingResponse(stream_generator, media_type="text/event_stream")

@router.post("", response_model=AgentOutput)
async def get_reference(req: References) -> AgentOutput: 
    if req == None:
        raise HTTPException(status_code=400, detail="No user query provided")
    
    input: str = f"query: {req.query}. resources: {req.num_of_refs}"

    response: AgentOutput = await get_response(input)

    return response
    