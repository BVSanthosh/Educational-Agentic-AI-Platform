from fastapi import APIRouter, HTTPException
from services import get_reference_response
from schemas import ReferencesOutput

router = APIRouter(prefix="/references")

@router.post("/")
async def get_document(query: str, num_of_refs: int) -> ReferencesOutput: 
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

    response: ReferencesOutput = get_reference_response(input)

    return response
    