import tempfile
import shutil
from fastapi import APIRouter, UploadFile, BackgroundTasks, HTTPException
from app.services.summary_agent.ingestion_pipeline import process_and_summarise
from app.services.summary_agent.summary_agent import get_answer
from app.schemas.summary_schema import SummaryInput

router = APIRouter(prefix="/summary")

@router.post("/uploadfile")
async def upload_summary(file: UploadFile, background_task: BackgroundTasks):
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
        shutil.copyfileobj(file.file, tmp)
        tmp_path = tmp.name

    filename = file.filename or "filename"
    doc_id = "doc_id"
    background_task.add_task(process_and_summarise, filename, tmp_path, doc_id)
    
    return {"doc_id": doc_id, "status": "processing"}

@router.post("/query")
async def answer_query(req: SummaryInput):
    if req.query == "":
        HTTPException(status_code=400)

    response = await get_answer(req.query, req.doc_id)
    return response