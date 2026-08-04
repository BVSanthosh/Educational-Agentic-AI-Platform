from fastapi import HTTPException, status
from typing import Any, cast, AsyncGenerator
from uuid import UUID, uuid4
from sqlalchemy import update, func
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from psycopg_pool import AsyncConnectionPool
from langgraph.graph import StateGraph, START, END
from langgraph.prebuilt import ToolNode, tools_condition
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from langchain_core.messages import HumanMessage
from langchain_core.runnables import RunnableConfig
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
    global reearch_agent
    
    checkpointer = AsyncPostgresSaver(cast(Any, pool))
    reearch_agent = graph_builder.compile(checkpointer=checkpointer)

async def stream_and_persist_research(user_input: str, space_id: UUID, thread_id: str, user_id: UUID, db: AsyncSession) -> AsyncGenerator[str,None]:
    if not research_agent:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to initialise agent"
        )
        
    accumulated_response: list[str] = []

    stream = await research_agent.astream_events(
        {"messages": [HumanMessage(content=user_input)]},
        {"configurable": {"thread_id": thread_id}},
        version="v2"
    )
    
    try:
        async for event in stream:
            event_type = event.get("event")
            event_data = event.get("data")
            
            if not isinstance(event_data, dict):
                continue
            
            if event_type == "on_chat_model_stream":
                chunk = event_data.get("chunk")
                if chunk and hasattr(chunk, "content") and chunk.content:
                    text_delta = str(chunk.content)
                    accumulated_response.append(text_delta)
                    yield text_delta
    except Exception as e:
        yield f"\n[Streaming Error: {str(e)}]"
        return           
                    
    final_text = "".join(accumulated_response).strip()

    if final_text:
        try:
            new_message = {
                "id": str(uuid4()),
                "role": "user",
                "contet": user_input,
                "created_at": datetime.now(timezone.utc).isoformat()
            }
            query = (
                update(Space)
                .where(Space.id == space_id, Space.user_id == user_id)
                .values(
                    data=func.jsonb_insert(
                        Space.data, 
                        "{messages, -1}", 
                        func.to_jsonb(new_message), 
                        True
                    ),
                    updated_at=func.now()
                )
            )
            
            await db.execute(query)
            await db.commit()
        except Exception as db_err:
            await db.rollback()
            yield f"\n[Warning: Failed to persist research response: {str(db_err)}]"

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
                    "{messages, -1}", 
                    func.to_jsonb(new_message), 
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