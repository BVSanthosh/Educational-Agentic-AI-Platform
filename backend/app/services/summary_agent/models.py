from uuid import UUID
from llama_index.core.agent.workflow import FunctionAgent
from llama_index.embeddings.google_genai import GoogleGenAIEmbedding
from llama_index.core.node_parser import SentenceSplitter
from llama_index.llms.google_genai import GoogleGenAI 
from sqlalchemy import select
from app.core.config import env
from app.core.database import AsyncSessionLocal
from app.models import Document as DocumentModel, DocumentChunk

llm = GoogleGenAI(model="gemini-2.5-flash", api_key=env.GEMINI_API_KEY)
embed_model = GoogleGenAIEmbedding(model_name="gemini-embedding-2", api_key=env.GEMINI_API_KEY)
splitter = SentenceSplitter(chunk_size=512, chunk_overlap=50)
 
def build_summary_agent(space_id: str) -> FunctionAgent:
    """
    Factory function to create an isolated agent for a specific space.
    """
    
    # 1. The tool is defined LOCALLY inside the factory
    # The LLM only sees 'search_query' in the tool schema
    async def search_document(search_query: str) -> str:
        """
        Search the uploaded document in pgvector to retrieve relevant facts, figures, 
        context, and excerpts necessary to answer the user's question.
        """
        
        # 1. Embed the user's query
        query_embedding = await embed_model.aget_query_embedding(search_query)
        
        # 2. Run a native pgvector similarity search using your custom tables
        async with AsyncSessionLocal() as db:
            stmt = (
                select(DocumentChunk.text)
                .join(DocumentModel, DocumentModel.id == DocumentChunk.document_id)
                .where(DocumentModel.space_id == UUID(space_id))
                .order_by(DocumentChunk.embedding.cosine_distance(query_embedding))
                .limit(3)
            )
            result = await db.execute(stmt)
            top_chunks = result.scalars().all()
            
        if not top_chunks:
            return "No relevant context found in the document."
            
        # 3. Format the chunks for the LLM
        return "\n\n...[Excerpt]...\n\n".join(top_chunks)

    # 2. Instantiate and return the agent with the scoped tool
    return FunctionAgent(
        llm=llm,
        tools=[search_document], 
        system_prompt=(
            "You are an expert Q&A assistant for a provided document. "
            "Always use the 'search_document' tool to fetch information from "
            "the document before answering the user's question."
        )
    )