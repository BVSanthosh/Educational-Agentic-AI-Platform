import json
import asyncio
from fastapi import HTTPException, status
from typing import Any, cast, AsyncGenerator
from uuid import UUID, uuid4
from sqlalchemy import update, func, String, cast as sql_cast
from sqlalchemy.dialects.postgresql import JSONB, ARRAY
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from psycopg_pool import AsyncConnectionPool
from langgraph.graph import StateGraph, START, END
from langgraph.prebuilt import ToolNode, tools_condition
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from langchain_core.messages import HumanMessage
from app.services.research_agent.convo_state import ConvoState
from app.services.research_agent.convo_nodes import clarify_research
from app.services.research_agent.convo_tools import write_research_report
from app.models import Space

graph_builder = StateGraph(ConvoState)

graph_builder.add_node("interviewer", clarify_research)
graph_builder.add_node("research_tool", ToolNode([write_research_report]))

graph_builder.add_edge(START, "interviewer")
graph_builder.add_conditional_edges( 
    "interviewer",
    tools_condition,
    {
        "tools": "research_tool",  
        "__end__": END,
    }
) 
graph_builder.add_edge("research_tool", "interviewer")

research_agent: Any | None = None

def init_research_agent(pool: AsyncConnectionPool[Any]):
    global research_agent
    
    checkpointer = AsyncPostgresSaver(cast(Any, pool))
    research_agent = graph_builder.compile(checkpointer=checkpointer)

async def stream_and_persist_research(user_input: str, space_id: UUID, thread_id: str, user_id: UUID, db: AsyncSession) -> AsyncGenerator[str, None]:
    agent = research_agent
    if not agent:
        raise HTTPException(status_code=500, detail="Failed to initialise agent")
        
    config = {
        "configurable": {
            "thread_id": thread_id,
            "space_id": str(space_id),
            "user_id": str(user_id)
        }
    }

    queue = asyncio.Queue()

    # ==========================================
    # 1. BULLETPROOF BACKGROUND TASK
    # ==========================================
    async def run_agent_and_save():
        accumulated_text = []
        is_writing = False
        
        try:
            async for event in agent.astream_events(
                {"messages": [HumanMessage(content=user_input)]},
                config=config,
                version="v2"
            ):
                # Send event to the browser stream
                await queue.put(event)
                
                # Keep track of the text internally so we can save it later
                event_type = event.get("event")
                name = event.get("name")
                
                if event_type == "on_tool_start" and name == "write_research_report":
                    is_writing = True
                elif event_type == "on_tool_end" and name == "write_research_report":
                    is_writing = False
                elif event_type == "on_chat_model_stream" and not is_writing:
                    chunk = event.get("data", {}).get("chunk")
                    if chunk and hasattr(chunk, "content"):
                        if isinstance(chunk.content, str):
                            accumulated_text.append(chunk.content)
                        elif isinstance(chunk.content, list):
                            for block in chunk.content:
                                if isinstance(block, dict) and "text" in block:
                                    accumulated_text.append(block["text"])
                                elif isinstance(block, str):
                                    accumulated_text.append(block)

            # --- THE AGENT FINISHED SUCCESSFULLY ---
            # Save to the database right here in the background task!
            final_text = "".join(accumulated_text).strip()
            if final_text:
                new_message = {
                    "id": str(uuid4()), 
                    "role": "agent",
                    "content": final_text, 
                    "created_at": datetime.now(timezone.utc).isoformat()
                }
                
                query = (
                    update(Space)
                    .where(Space.id == space_id, Space.user_id == user_id)
                    .values(
                        data=func.jsonb_insert(
                            Space.data, 
                            sql_cast(["messages", "-1"], ARRAY(String)),
                            sql_cast(new_message, JSONB),
                            True
                        ),
                        updated_at=func.now()
                    )
                )
                await db.execute(query)
                await db.commit()

        except asyncio.CancelledError:
            # If the backend shuts down
            pass 
        except Exception as e:
            await queue.put(e)
        finally:
            await queue.put(None) 

    # ==========================================
    # 2. START THE BACKGROUND TASK
    # ==========================================
    # Because we use asyncio.create_task, this runs independently of the browser!
    agent_task = asyncio.create_task(run_agent_and_save())

    # ==========================================
    # 3. STREAM TO BROWSER (SAFE TO DISCONNECT)
    # ==========================================
    is_writing_report = False
    try:
        while True:
            try:
                event = await asyncio.wait_for(queue.get(), timeout=15.0)
                
                if event is None: 
                    break
                if isinstance(event, Exception):
                    raise event
                
                event_type = event.get("event")
                event_data = event.get("data")
                name = event.get("name")
                
                if not isinstance(event_data, dict):
                    continue
                
                if event_type == "on_tool_start" and name == "write_research_report":
                    is_writing_report = True
                    yield f"data: {json.dumps({'type': 'progress', 'message': 'Gathering sources and writing report...'})}\n\n"

                elif event_type == "on_tool_end" and name == "write_research_report":
                    is_writing_report = False
                    output_obj = event_data.get("output")
                    output_str = "{}"
                    if output_obj is not None:
                        if hasattr(output_obj, "content"):
                            output_str = str(output_obj.content)
                        elif isinstance(output_obj, dict) and "content" in output_obj:
                            output_str = str(output_obj["content"])
                        elif isinstance(output_obj, str):
                            output_str = output_obj

                    tool_output = json.loads(output_str)
                    
                    if tool_output.get("status") == "success":
                        doc_payload = {
                            "type": "document_ready", 
                            "document_id": tool_output.get("document_id"),
                            "filename": tool_output.get("filename", "Generated_Report.md")
                        }
                        yield f"data: {json.dumps(doc_payload)}\n\n"
                    else:
                        yield f"data: {json.dumps({'type': 'error', 'message': f'Tool Failed'})}\n\n"
                
                elif event_type == "on_chat_model_stream" and not is_writing_report:
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
                            yield f"data: {json.dumps({'type': 'token', 'content': text_delta})}\n\n"
 
            except asyncio.TimeoutError:
                yield f"data: {json.dumps({'type': 'ping'})}\n\n"

    except asyncio.CancelledError:
        # THE BROWSER DISCONNECTED! 
        # We catch it gracefully here. The background task keeps running!
        return
    except Exception as e:
        yield f"data: {json.dumps({'type': 'error', 'message': f'Streaming Error: {str(e)}'})}\n\n"
        return            
                    
    yield f"data: {json.dumps({'type': 'done'})}\n\n"

async def get_and_persist_research(user_input: str, thread_id: str, space_id: UUID, user_id: UUID, db: AsyncSession) -> str:

    if research_agent is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Research agent has not been initialized."
        )

    try:
        response = await research_agent.ainvoke(
            {"messages": [HumanMessage(content=user_input)]},
            {"configurable": {"thread_id": str(thread_id)}}
        )
    except Exception as err:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error executing research agent: {str(err)}"
        )

    messages = response.get("messages", [])
    if not messages:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Research agent finished with no output messages."
        )

    last_message = messages[-1]
    last_message_content = getattr(last_message, "content", "")

    if isinstance(last_message_content, list):
        final_text = "".join([
            block["text"] for block in last_message_content
            if isinstance(block, dict) and block.get("type") == "text"
        ]).strip()
    else:
        final_text = str(last_message_content).strip()

    if not final_text:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Research agent produced empty output."
        )

    new_message = {
        "id": str(uuid4()),
        "role": "assistant",
        "content": final_text,
        "created_at": datetime.now(timezone.utc).isoformat()
    }

    try:
        query = (
            update(Space)
            .where(Space.id == space_id, Space.user_id == user_id)
            .values(
                data=func.jsonb_insert(
                    Space.data, 
                    sql_cast(["messages", "-1"], ARRAY(String)),
                    sql_cast(new_message, JSONB),
                    True
                ),
                updated_at=func.now()
            )
        )
        await db.execute(query)
        await db.commit()
    except Exception as db_err:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to persist research response to database: {str(db_err)}"
        )

    return final_text