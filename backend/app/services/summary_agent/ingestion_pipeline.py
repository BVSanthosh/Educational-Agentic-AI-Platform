import os
from pathlib import Path 
from llama_index.readers.file import PDFReader
from llama_index.core.ingestion import IngestionPipeline
from llama_index.core.llms import ChatMessage
from uuid import UUID, uuid4
from app.core.database import AsyncSessionLocal
from sqlalchemy import update, func, String, cast
from sqlalchemy.dialects.postgresql import JSONB, ARRAY
from app.models import Document as DocumentModel, DocumentChunk, Space
from app.services.summary_agent.models import (
    llm,
    embed_model,
    splitter
)

async def embed_and_summarise(filename: str, filepath: str, space_id: UUID, user_id: UUID):
    try:
        file_size = os.path.getsize(filepath)
        doc_id = uuid4()
        
        parser = PDFReader()
        documents = parser.load_data(file=Path(filepath))
        
        # 1. Run pipeline WITHOUT a vector store to just get the embedded nodes
        pipeline = IngestionPipeline(
            transformations=[
                splitter,
                embed_model,
            ],
        )
        
        # nodes will contain the chunked text and the vector embeddings
        nodes = await pipeline.arun(documents=documents)

        # 2. Insert into your custom database tables
        async with AsyncSessionLocal() as db:
            # Add the parent Document first to satisfy the Foreign Key constraint
            doc_record = DocumentModel(
                id=doc_id,
                user_id=user_id,
                space_id=space_id,
                filename=filename,
                file_path=filepath,
                file_size_bytes=file_size,
                mime_type="application/pdf",
                metadata_={"source": filename}
            )
            db.add(doc_record)
            await db.flush() # Ensure doc_record exists before adding chunks
            
            # Map LlamaIndex nodes to your DocumentChunk model
            chunk_records = []
            for i, node in enumerate(nodes):
                chunk_records.append(
                    DocumentChunk(
                        document_id=doc_id,
                        node_id=node.node_id,
                        chunk_index=i,
                        text=node.get_content(),
                        embedding=node.embedding, # Insert pgvector embedding
                        metadata_=node.metadata
                    )
                )
            
            db.add_all(chunk_records)
            await db.commit()

        # 3. Generate the summary (Remains unchanged)
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
        
        # 4. Update Space data (Remains unchanged)
        async with AsyncSessionLocal() as db:
            query = (
                update(Space)
                .where(Space.id == space_id, Space.user_id == user_id)
                .values(
                    data=func.jsonb_set(
                        func.jsonb_set(
                            Space.data,
                            cast(["summary"], ARRAY(String)),
                            cast(summary_text, JSONB),
                            True
                        ),
                        cast(["status"], ARRAY(String)),
                        cast("ready", JSONB),
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
                        cast(["status"], ARRAY(String)),
                        cast(f"failed: {str(e)}", JSONB),
                        True
                    ),
                    updated_at=func.now()
                )
            )
            await db.execute(query)
            await db.commit()
    finally:
        if os.path.exists(filepath):
            os.remove(filepath)