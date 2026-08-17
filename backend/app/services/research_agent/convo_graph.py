import json
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
    if not research_agent:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to initialise agent"
        )
        
    accumulated_response: list[str] = []

    # Inject space_id and user_id into config so the tool can use them
    config = {
        "configurable": {
            "thread_id": thread_id,
            "space_id": str(space_id),
            "user_id": str(user_id)
        }
    }

    stream = research_agent.astream_events(
        {"messages": [HumanMessage(content=user_input)]},
        config=config,
        version="v2"
    ) 
     
    try:
        async for event in stream:
            event_type = event.get("event")
            event_data = event.get("data")
            name = event.get("name")
            
            if not isinstance(event_data, dict):
                continue
            
            # 1. Emitting Tool Progress
            if event_type == "on_tool_start" and name == "write_research_report":
                yield f"data: {json.dumps({'type': 'progress', 'message': 'Gathering sources and writing report...'})}\n\n"

            # 2. Emitting Tool Completion & Document Link
            elif event_type == "on_tool_end" and name == "write_research_report":
                try:
                    tool_output = json.loads(event_data.get("output", "{}"))
                    doc_payload = {
                        "type": "document_ready", 
                        "document_id": tool_output.get("document_id"),
                    }
                    yield f"data: {json.dumps(doc_payload)}\n\n"
                except json.JSONDecodeError:
                    pass
            
            # 3. Emitting LLM Chat Tokens
            elif event_type == "on_chat_model_stream" and "interviewer" in event.get("tags", []):
                chunk = event_data.get("chunk")
                if chunk and hasattr(chunk, "content") and chunk.content:
                    text_delta = str(chunk.content)
                    accumulated_response.append(text_delta)
                    yield f"data: {json.dumps({'type': 'token', 'content': text_delta})}\n\n"

    except Exception as e:
        yield f"data: {json.dumps({'type': 'error', 'message': f'Streaming Error: {str(e)}'})}\n\n"
        return            
                    
    # End of stream event
    yield f"data: {json.dumps({'type': 'done'})}\n\n"

    # Persist the final conversational LLM output into the Space messages
    final_text = "".join(accumulated_response).strip()

    if final_text:
        try:
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
        except Exception as db_err:
            await db.rollback()
            # Do not yield pure text anymore; everything is SSE formatted
            yield f"data: {json.dumps({'type': 'error', 'message': f'Warning: Failed to persist research response: {str(db_err)}'})}\n\n"

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