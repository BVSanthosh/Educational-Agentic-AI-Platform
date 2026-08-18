from fastapi import HTTPException , status
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID
from sqlalchemy import update, func
from langchain.tools import tool
from langchain.agents import create_agent
from psycopg_pool import AsyncConnectionPool
from langchain.agents.middleware import ModelCallLimitMiddleware, ToolCallLimitMiddleware, ToolRetryMiddleware, ModelRetryMiddleware
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_tavily import TavilySearch
from typing import Literal, AsyncGenerator, cast, Any
from app.core.config import env
from app.services.reference_agent.reference_prompt import get_reference_prompt
from app.schemas import ReferenceResponse, TavilySearchInput, TavilySearchOutput, TavilySearchError
from app.models import Space

SYSTEM_PROMPT = get_reference_prompt()
tavily_client = TavilySearch(tavily_api_key=env.TAVILY_API_KEY)

@tool(args_schema=TavilySearchInput)
def web_search(
    query: str,
    topic: Literal["general", "news", "finance"] = "general",
    max_results: int = 5,
    time_range: Literal["day", "week", "month", "year"] | None = None,
    include_domains: list[str] | None = None,
    search_depth: Literal["basic", "advanced", "fast", "ultra-fast"] = "basic"
) -> list[TavilySearchOutput] | TavilySearchError:
    """
    Search the web for relevant resources using tavily. 

    Args:
        query: the user's query
        topic: the type of query. It can only have the following values: "general", "news", "finance"
        max_results: the maximum number of resources to gather. The default is 5 
        time_range: how far back the search should be done from. It can only have the following values: "day", "week", "month", "year"
        include_domains: any specific domains that the search should be based on
        search_depth: how deep the search should be. It can only have the following values: "basic", "advanced", "fast", "ultra-fast"

    Returns either a resource list with the type list[TavilySearchOutput] or an error of type TavilySearchError
    """

    configured_search = tavily_client.bind(
        topic=topic, 
        max_results=max_results, 
        time_range=time_range, 
        include_domains=include_domains,
        search_depth=search_depth
    )

    search_results = configured_search.invoke({"query": query})
    
    if "detail" in search_results:
        return search_results["detail"]["error"]
    else:
        return search_results["results"]

llm = ChatGoogleGenerativeAI(
    model="gemini-2.5-flash-lite", 
    api_key = env.GEMINI_API_KEY,
    temperature=0.0,
    max_tokens=None,
    timeout=None,
) 

agent_middleware = [
    ModelCallLimitMiddleware(run_limit=4),
    ToolCallLimitMiddleware(tool_name="web_search", run_limit=2),
    ModelRetryMiddleware(max_retries=2, backoff_factor=2, initial_delay=1, on_failure="continue"),
    ToolRetryMiddleware(tools=["web_search"], max_retries=1, backoff_factor=2, initial_delay=1, on_failure="continue")
]

reference_agent: Any | None = None

def init_reference_agent(pool: AsyncConnectionPool[Any]):
    global reference_agent
    
    checkpointer = AsyncPostgresSaver(cast(Any, pool))
    
    reference_agent = create_agent(
        model=llm,
        tools=[web_search],
        system_prompt=SYSTEM_PROMPT, 
        response_format=ReferenceResponse,
        middleware=agent_middleware,
        checkpointer=checkpointer
    )

async def stream_and_persist_reference(user_input: str, thread_id: str, space_id: UUID, user_id: UUID, db: AsyncSession) -> AsyncGenerator[str, None]:
    final_output: ReferenceResponse | None = None
    
    if reference_agent is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to initialise agent"
        )
        
    stream = await reference_agent.astream_events(
        {"messages": [{"role": "user", "content": user_input}]},
        {"configurable": {"thread_id": str(thread_id)}},
        version="v3"
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
                    yield str(chunk.content)

            elif event_type == "on_chain_end" and event.get("name") == "LangGraph":
                output = event_data.get("output")
                if isinstance(output, dict):
                    
                    if "structured_response" in output:
                        final_output = output["structured_response"]
                    elif "structured_output" in output:
                        final_output = output["structured_output"]
    except Exception as e:
        yield f"\n[Streaming Error: {str(e)}]"
        return

    if final_output:
        try:
            output_dict = final_output.model_dump(mode="json")
            query = update(Space).where(Space.id == space_id, Space.user_id == user_id).values(data=output_dict, updated_at=func.now())
 
            await db.execute(query)
            await db.commit()
        except Exception as db_err:
            await db.rollback()
            yield f"\n[Warning: Failed to persist response to database: {str(db_err)}]"

async def get_and_persist_reference(user_input: str, thread_id: str, space_id: UUID, user_id: UUID, db: AsyncSession) -> ReferenceResponse:
    final_output: ReferenceResponse | None = None

    if reference_agent is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Couldn't initialise agent"
        )

    try:
        response = await reference_agent.ainvoke(
            {"messages": [{"role": "user", "content": user_input}]},
            {"configurable": {"thread_id": thread_id}}
        )

        if isinstance(response, dict):
            if "structured_output" in response:
                final_output = response["structured_output"]
            elif "structured_response" in response:
                final_output = response["structured_response"]
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error generating response"
        )

    if not final_output:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error generating response"
        )

    if final_output:
        try:
            output_dict = final_output.model_dump(mode="json")
            query = update(Space).where(Space.id == space_id, Space.user_id == user_id).values(data=output_dict, created_at=func.now())

            await db.execute(query)
            await db.commit()
        except Exception as db_err:
            await db.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to persist response to database: {str(db_err)}"
            )

    return final_output

        



