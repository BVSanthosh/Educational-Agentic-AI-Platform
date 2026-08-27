import json 
import asyncio
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
    agent = reference_agent
    if agent is None:
        yield f"data: {json.dumps({'type': 'error', 'message': 'Agent not initialized'})}\n\n"
        return
    
    queue = asyncio.Queue()

    # 1. Background worker to execute the LangGraph agent and save to DB independently
    async def run_summary_agent_background():
        full_agent_response = ""
        is_searching = False
        
        try:
            await queue.put({'type': 'progress', 'message': 'Searching document for answers...'})
            
            config: RunnableConfig = {
                "configurable": {
                    "thread_id": thread_id,
                    "space_id": str(space_id)
                }
            }
            inputs = {"messages": [{"role": "user", "content": user_input}]}

            async for event in agent.astream_events(inputs, config=config, version="v2"):
                event_type = event.get("event")
                event_data = event.get("data")
                name = event.get("name")
                
                if not isinstance(event_data, dict):
                    continue
                    
                if event_type == "on_tool_start" and name == "search_document":
                    is_searching = True
                    await queue.put({'type': 'progress', 'message': 'Extracting context from document...'})
                    
                elif event_type == "on_tool_end" and name == "search_document":
                    is_searching = False
                
                elif event_type == "on_chat_model_stream" and not is_searching:
                    chunk = event_data.get("chunk")
                    if chunk and hasattr(chunk, "content") and chunk.content:
                        text_delta = ""
                        if isinstance(chunk.content, str):
                            text_delta = chunk.content
                        elif isinstance(chunk.content, list):
                            for block in chunk.content:
                                if isinstance(block, dict) and "text" in block:
                                    text_delta += block["text"]
                                elif isinstance(block, str):
                                    text_delta += block
                                    
                        if text_delta:
                            full_agent_response += text_delta
                            await queue.put({'type': 'token', 'content': text_delta})

            # --- AGENT FINISHED SUCCESSFULLY: PERSIST TO DB ---
            if full_agent_response.strip():
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
 
            await queue.put({'type': 'done'})

        except Exception as e:
            print(f"Error in run_summary_agent_background: {e}")
            await queue.put(e)
        finally:
            await queue.put(None)  # Signal completion

    # 2. Launch background task
    task = asyncio.create_task(run_summary_agent_background())

    # 3. Stream to browser with heartbeat protection
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
        # Browser disconnected/switched spaces. Background task safely finishes writing to DB!
        return
    except Exception as e:
        yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"
        return