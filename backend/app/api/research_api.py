from fastapi import APIRouter, HTTPException
from app.schemas import ResearchInput, ResearchOutput
from app.services import get_research

router = APIRouter(prefix="/research")

@router.post("/stream")
async def get_research_stream(req: ResearchInput) -> str:
    if req.topic == "":
        HTTPException(status_code=40)
        
    report: str = await get_research(req.topic)
    
    return report

        