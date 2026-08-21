import json
from typing import AsyncGenerator, cast, Any, Optional
from uuid import UUID, uuid4
from datetime import datetime, timezone
from sqlalchemy import select, update, func, String, cast as sql_cast
from sqlalchemy.dialects.postgresql import JSONB, ARRAY
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.tools import tool
from langchain_core.runnables import RunnableConfig
from langgraph.graph.state import CompiledStateGraph
from langgraph.prebuilt import create_react_agent
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from llama_index.core.node_parser import SentenceSplitter
from llama_index.embeddings.google_genai import GoogleGenAIEmbedding
from psycopg_pool import AsyncConnectionPool
from app.core.config import env
from app.core.database import AsyncSessionLocal
from app.models import Space, Document as DocumentModel, DocumentChunk

# ==========================================
# 1. MODELS AND TOOLS
# ==========================================

# LlamaIndex Embeddings (Strictly for the ingestion pipeline)
llama_index_embed_model = GoogleGenAIEmbedding(model_name="gemini-embedding-2", api_key=env.GEMINI_API_KEY)
splitter = SentenceSplitter(chunk_size=512, chunk_overlap=50)

# The core LLM 
llm = ChatGoogleGenerativeAI(
    model="gemini-2.5-flash", 
    api_key=env.GEMINI_API_KEY,
    temperature=0.0,
) 

@tool
async def search_document(search_query: str, config: RunnableConfig) -> str:
    """Search the uploaded document in pgvector to retrieve relevant facts, figures, and context."""
    
    # FIX: Extract the space_id dynamically from LangChain's configuration
    configurable = config.get("configurable", {})
    space_id_str = configurable.get("space_id")
    
    if not space_id_str:
        return "Error: space_id not found in configuration."
        
    query_embedding = await llama_index_embed_model.aget_query_embedding(search_query)
    
    async with AsyncSessionLocal() as db:
        stmt = (
            select(DocumentChunk.text)
            .join(DocumentModel, DocumentModel.id == DocumentChunk.document_id)
            .where(DocumentModel.space_id == UUID(space_id_str))
            .order_by(DocumentChunk.embedding.cosine_distance(query_embedding))
            .limit(3)
        )
        result = await db.execute(stmt)
        top_chunks = result.scalars().all()
        
    return "\n\n...[Excerpt]...\n\n".join(top_chunks) if top_chunks else "No relevant context found in the document."


# ==========================================
# 2. AGENT INITIALIZATION
# ==========================================

reference_agent: Optional[CompiledStateGraph] = None

def init_summary_agent(pool: AsyncConnectionPool[Any]):
    """Initialize the LangGraph agent with a Postgres checkpointer."""
    global reference_agent
    
    checkpointer = AsyncPostgresSaver(pool)
    
    # tool execution, streaming, and PostgreSQL memory checkpointing.
    reference_agent = create_react_agent(
        model=llm,
        tools=[search_document],
        checkpointer=checkpointer,
    )


# ==========================================
# 3. QUERY STREAMING FUNCTION
# ==========================================

async def stream_get_answer_and_persist(
    user_input: str, 
    user_id: UUID, 
    space_id: UUID,
    thread_id: str
) -> AsyncGenerator[str, None]:
    if reference_agent is None:
        yield f"data: {json.dumps({'type': 'error', 'message': 'Agent not initialized'})}\n\n"
        return
    
    try:   
        yield f"data: {json.dumps({'type': 'progress', 'message': 'Searching document for answers...'})}\n\n"
        
        # Pass the space_id into the configuration so the `@tool` can access it!
        config: RunnableConfig = {
            "configurable": {
                "thread_id": thread_id, # Group the memory by space
                "space_id": str(space_id)   # Inject space_id for pgvector
            }
        }
        
        inputs = {"messages": [{"role": "user", "content": user_input}]}
        full_agent_response = ""
        
        is_searching = False
        
        # Bulletproof event streaming loop
        async for event in reference_agent.astream_events(inputs, config=config, version="v2"):
            event_type = event.get("event")
            event_data = event.get("data")
            name = event.get("name")
            
            if not isinstance(event_data, dict):
                continue
                
            # 1. Emitting Tool Progress
            if event_type == "on_tool_start" and name == "search_document":
                is_searching = True
                yield f"data: {json.dumps({'type': 'progress', 'message': 'Extracting context from document...'})}\n\n"
                
            elif event_type == "on_tool_end" and name == "search_document":
                is_searching = False
            
            # 2. Emitting LLM Chat Tokens safely
            elif event_type == "on_chat_model_stream" and not is_searching:
                chunk = event_data.get("chunk")
                
                if chunk and hasattr(chunk, "content") and chunk.content:
                    text_delta = ""
                    
                    # Safely extract text whether it is a string or a list of dictionaries
                    if isinstance(chunk.content, str):
                        text_delta = chunk.content
                    elif isinstance(chunk.content, list):
                        for block in chunk.content:
                            if isinstance(block, dict) and "text" in block:
                                text_delta += block["text"]
                            elif isinstance(block, str):
                                text_delta += block
                                
                    # Only yield if we actually extracted text
                    if text_delta:
                        full_agent_response += text_delta
                        yield f"data: {json.dumps({'type': 'token', 'content': text_delta})}\n\n"
            
        # Persist the full response to the DB
        agent_message = {
            "id": str(uuid4()),
            "role": "agent",
            "content": full_agent_response,
            "created_at": datetime.now(timezone.utc).isoformat()
        }
        
        async with AsyncSessionLocal() as db_session:
            update_agent_message = (
                update(Space)
                .where(Space.id == space_id, Space.user_id == user_id)
                .values(
                    data=func.jsonb_insert(
                        Space.data, 
                        sql_cast(["messages", "-1"], ARRAY(String)),
                        sql_cast(agent_message, JSONB),
                        True
                    ),
                    updated_at=func.now()
                )
            )
            await db_session.execute(update_agent_message)
            await db_session.commit()
            
        yield f"data: {json.dumps({'type': 'done'})}\n\n"
        
    except Exception as e:
        print(f"Error in stream_get_answer_and_persist: {e}")
        yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"