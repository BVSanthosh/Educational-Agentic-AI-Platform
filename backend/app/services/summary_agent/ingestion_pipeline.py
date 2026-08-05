import os
from pathlib import Path 
from llama_index.readers.file import PDFReader
from llama_index.core.ingestion import IngestionPipeline
from llama_index.core.llms import ChatMessage
from uuid import UUID, uuid4
from app.core.database import AsyncSessionLocal
from sqlalchemy import update, func
from app.models import Document as DocumentModel, Space
from app.services.summary_agent.models import (
    llm,
    embed_model,
    splitter,
    vector_store,
)

async def embed_and_summarise(filename: str, filepath: str, space_id: UUID, user_id: UUID):
    try:
        file_size = os.path.getsize(filepath)
        doc_id = uuid4()
        
        async with AsyncSessionLocal() as db:
            doc_record = DocumentModel(
                id=doc_id,
                user_id=user_id,
                space_id=space_id,
                filename=filename,
                file_path=filepath,
                file_size_bytes=file_size,
                mime_type="application/json",
                metadata_={"source": filename}
            )
                
            db.add(doc_record)
            await db.commit()
            
        parser = PDFReader()
        documents = parser.load_data(file=Path(filepath))

        for doc in documents:
            doc.metadata["document_id"] = str(doc_id)
            doc.metadata["space_id"] = str(space_id)
            doc.metadata["user_id"] = str(user_id)
                
        pipeline = IngestionPipeline(
            transformations=[
                splitter,
                embed_model,
            ],
            vector_store=vector_store,
        )
            
        await pipeline.arun(documents=documents)

        full_doc_text = "\n\n".join([doc.text for doc in documents])
        messages = [
            ChatMessage(
                role="system", 
                content="Your role is to summarize any documents the user sends you. Provide a detailed and comprehensive overview."
            ),
            ChatMessage(
                role="user", 
                content=f"Please summarize the document '{filename}':\n\n{full_doc_text}"
            ),
        ]
        
        summary_response = await llm.achat(messages)
        summary_text = str(summary_response.message.content)
        
        async with AsyncSessionLocal() as db:
            query = (
                update(Space)
                .where(Space.id == space_id, Space.user_id == user_id)
                .values(
                    data=func.jsonb_set(
                        func.jsonb_set(
                            Space.data,
                            "{summary}",
                            func.to_jsonb(summary_text),
                            True
                        ),
                        "status",
                        func.to_jsonb("read"),
                        True
                    ),
                    updated_at=func.now()
                )
            )
            await db.execute(query)
            await db.commit()
    except Exception as e:
        async with AsyncSessionLocal() as db:
            query = (
                update(Space)
                .where(Space.id == space_id, Space.user_id == user_id)
                .values(
                    data=func.jsonb_set(
                        Space.data,
                        "status",
                        func.to_jsonb(f"faild:{str(e)}"),
                        True
                    ),
                    udpated_at=func.now()
                )
            )
            await db.execute(query)
            await db.commit()
    finally:
        if os.path.exists(filepath):
            os.remove(filepath)