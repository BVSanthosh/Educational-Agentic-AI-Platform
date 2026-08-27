import os
import json
import asyncio
import aioboto3
from pathlib import Path 
from typing import AsyncGenerator
from llama_index.readers.file import PDFReader
from llama_index.core.ingestion import IngestionPipeline
from uuid import UUID, uuid4
from app.core.database import AsyncSessionLocal
from app.models import Document, DocumentChunk
from app.utils.s3_client import upload_document_to_s3
from app.core.config import env
from app.services.summary_agent.summary_agent import (
    llm,
    llama_index_embed_model,
    splitter
)

boto_session = aioboto3.Session()

async def stream_embed_and_summarise(
    filename: str, 
    tmp_filepath: str, 
    s3_key: str, 
    space_id: UUID, 
    user_id: UUID
) -> AsyncGenerator[str, None]:
    
    queue = asyncio.Queue()

    # 1. Background worker that processes the heavy pipeline and saves to DB independently of the browser
    async def run_ingestion_and_summary_background():
        try:
            await queue.put({'type': 'progress', 'message': 'Parsing document and creating vector embeddings...'})
            
            file_size = os.path.getsize(tmp_filepath)
            doc_id = uuid4()
            
            parser = PDFReader()
            documents = parser.load_data(file=Path(tmp_filepath))
            
            pipeline = IngestionPipeline(
                transformations=[splitter, llama_index_embed_model], 
            )
            nodes = await pipeline.arun(documents=documents)

            # Save source file and chunks into database
            async with AsyncSessionLocal() as db:
                doc_record = Document(
                    id=doc_id,
                    user_id=user_id,
                    space_id=space_id,
                    filename=filename,
                    file_path=s3_key,
                    file_size_bytes=file_size,
                    mime_type="application/pdf",
                    metadata_={"source": filename}
                )
                db.add(doc_record)
                await db.flush()
                
                chunk_records = [
                    DocumentChunk(
                        document_id=doc_id,
                        node_id=node.node_id,
                        chunk_index=i,
                        text=node.get_content(),
                        embedding=node.embedding,
                        metadata_=node.metadata
                    )
                    for i, node in enumerate(nodes)
                ]
                db.add_all(chunk_records)
                await db.commit()

            await queue.put({'type': 'progress', 'message': 'Generating comprehensive markdown summary...'})

            full_doc_text = "\n\n".join([doc.text for doc in documents])
            
            messages = [
                ("system", "Your role is to summarize documents sent by the user. Provide a detailed, highly structured, and comprehensive markdown-formatted overview."),
                ("human", f"Please summarize the document '{filename}':\n\n{full_doc_text}")
            ]
            
            summary_response = await llm.ainvoke(messages)
            summary_text = str(summary_response.content)

            # Save Summary as a viewable Document in S3/Database
            base_name = os.path.splitext(filename)[0]
            summary_filename = f"Summary_{base_name}.md"
            s3_data = await upload_document_to_s3(summary_text, filename, "summary")

            async with AsyncSessionLocal() as db_session:
                new_doc = Document(
                    space_id=space_id,
                    user_id=user_id,
                    filename=summary_filename,
                    file_path=s3_data["s3_key"],
                    file_size_bytes=s3_data["file_size_bytes"],
                    mime_type=s3_data["mime_type"],
                    metadata_={"s3_url": s3_data["url"]}
                )
                db_session.add(new_doc)
                await db_session.commit()
                await db_session.refresh(new_doc)
                summary_doc_id = new_doc.id

            await queue.put({
                'type': 'document_ready', 
                'document_id': str(summary_doc_id), 
                'filename': summary_filename
            })

            # Stream the handoff message tokens into the queue
            handoff_text = f"I have successfully analyzed '{filename}', generated your summary, and opened it in the right panel. Feel free to ask me any questions about the document!"
            chunk_size = 6
            for i in range(0, len(handoff_text), chunk_size):
                chunk = handoff_text[i:i + chunk_size]
                await queue.put({'type': 'token', 'content': chunk})
                await asyncio.sleep(0.02)
                
            # Cleanup temp file from S3
            async with boto_session.client("s3") as s3:
                await s3.delete_object(
                    Bucket=env.AWS_S3_BUCKET_NAME, 
                    Key=s3_key
                )

            await queue.put({'type': 'done'})

        except Exception as e:
            print(f"ERROR IN STREAM_EMBED_AND_SUMMARISE_BACKGROUND: {str(e)}")
            await queue.put(e)
        finally:
            await queue.put(None)  # Signal completion

    # 2. Launch background task
    task = asyncio.create_task(run_ingestion_and_summary_background())

    # 3. Stream from queue to browser with timeout protection (heartbeat pings)
    try:
        while True:
            try:
                event = await asyncio.wait_for(queue.get(), timeout=15.0)
                
                if event is None: 
                    break
                if isinstance(event, Exception):
                    raise event
                
                yield f"data: {json.dumps(event)}\n\n"

            except asyncio.TimeoutError:
                yield f"data: {json.dumps({'type': 'ping'})}\n\n"

    except asyncio.CancelledError:
        # Browser disconnected/switched spaces. Background task finishes saving safely!
        return
    except Exception as e:
        yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"