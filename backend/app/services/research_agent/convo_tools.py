import json
from typing import Any
from uuid import UUID
from langchain.tools import tool
from langchain_core.runnables import RunnableConfig
from app.schemas.research_schema import ResarchSubject
from app.services.research_agent.research_subgraph.research_subgraph import app
from app.models import Document
from app.utils.s3_client import upload_document_to_s3
from app.core.database import AsyncSessionLocal

@tool(args_schema=ResarchSubject)
async def write_research_report(subject_matter: str, config: RunnableConfig) -> str:
    """
    Generates a research report given a subject matter
    """ 
    # Extract parent thread and metadata injected from stream_and_persist_research
    configurable = config.get("configurable", {})
    parent_thread = configurable.get("thread_id", "default")
    space_id_str = configurable.get("space_id")
    user_id_str = configurable.get("user_id")
     
    input: Any = {"subject_matter": subject_matter}
    subgraph_config: RunnableConfig = {
        "configurable": {"thread_id": f"{parent_thread}_subgraph"}
    }
    
    # 1. Generate the report
    response = await app.ainvoke(
        input, 
        config=subgraph_config
    )
    report_content = response["research_report"]
    
    try:
    # 2. Upload to S3
        s3_data = await upload_document_to_s3(report_content)

        # 3. Save directly to Database using a fresh session (avoids streaming conflicts)
        async with AsyncSessionLocal() as db_session:
            clean_subject = "".join([c if c.isalnum() or c.isspace() else "_" for c in subject_matter])
            truncated_name = clean_subject.strip()[:50].strip().replace(" ", "_")
            safe_filename = f"{truncated_name}.md"
            
            new_doc = Document(
                space_id=UUID(space_id_str),
                user_id=UUID(user_id_str),
                filename=safe_filename,
                file_path=s3_data["s3_key"],                  
                file_size_bytes=s3_data["file_size_bytes"],   
                mime_type=s3_data["mime_type"],               
                metadata_={"s3_url": s3_data["url"]}          
            )
            db_session.add(new_doc)
            await db_session.commit()
            await db_session.refresh(new_doc)

        # 4. Return JSON summary back to the LLM (NOT the full document)
        return json.dumps({
            "status": "success",
            "document_id": str(new_doc.id),
            "filename": safe_filename,
            "message": "Report generated and saved successfully."
        })
    except Exception as e:
        # If the DB or S3 fails, catch it and return it so we can see the error!
        print(f"FAILED TO SAVE DOCUMENT: {str(e)}")
        return json.dumps({
            "status": "error",
            "error": str(e)
        })