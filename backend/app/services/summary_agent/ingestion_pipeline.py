import chromadb
import os
from pathlib import Path 
from llama_index.readers.file import PDFReader
from llama_index.vector_stores.chroma import ChromaVectorStore
from llama_index.core.ingestion import IngestionPipeline
from llama_index.core.llms import ChatMessage
from llama_index.core import Document
from app.services.summary_agent.models import (
    llm,
    embed_model,
    extractor,
    splitter
)

async def create_and_store_embeddings(documents: list[Document], filename: str, doc_id: str):
    for doc in documents:
        doc.metadata["filename"] = filename

    db = chromadb.PersistentClient(path="./chromadb")
    chroma_collection = db.get_or_create_collection(doc_id)
    vector_store = ChromaVectorStore(chroma_collection=chroma_collection)

    pipeline = IngestionPipeline(
        transformations=[
            splitter,
            extractor,
            embed_model,
        ],
        vector_store=vector_store,
    )
    
    pipeline.run(documents=documents)

async def process_and_summarise(filename: str, filepath: str, doc_id: str):
    try:
        parser = PDFReader()
        documents = parser.load_data(file=Path(filepath))

        await create_and_store_embeddings(documents, filename, doc_id)

        full_doc_text = "\n\n".join([doc.text for doc in documents])

        messages = [
            ChatMessage(
                role="system", content="Your role is to summarize any documents the user sends you. Provide a detailed and comprehensive overview."
            ),
            ChatMessage(role="user", content=f"Please summarize the following document:\n\n{full_doc_text}"),
        ]
        
        summary = await llm.achat(messages)
        return summary
    finally:
            if os.path.exists(filepath):
                os.remove(filepath)