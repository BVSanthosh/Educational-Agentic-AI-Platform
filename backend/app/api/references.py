from fastapi import APIRouter, UploadFile, HTTPException
from yaml import safe_load, YAMLError

router = APIRouter(prefix="/analysis")

@router.post("/")
async def get_document(doc : UploadFile):
    """
    Analyses a IaC file and provides a detailed report

    Args:
        doc: The document to summarise

    Returns:
        summary: A concise summary
    """

    MAX_SIZE = 2097152   # The max file size allowed

    if doc.size == 0:
        raise HTTPException(status_code=400, detail="Empty file uploaded")
    elif doc.size != None and doc.size > MAX_SIZE:
        raise HTTPException(status_code=413, detail="File size too large")
    elif doc.filename != None and (doc.filename[-4:] != "yaml" and doc.filename[-3:] != "yml"):
        raise HTTPException(status_code=400, detail="Invalid file uploaded")
    
    # Extacts the file contents as a single string
    file_bytes = await doc.read()
    file_contents = file_bytes.decode("utf-8") 

    # Parses the file contents to ensure valid syntax
    try:
        parsed_yaml = safe_load(file_contents)
    except YAMLError:
        raise HTTPException(status_code=400, detail="Invalid YAML syntax")

    # Send file_contents to a service function for analysis using LangGraph

    return "report"
    