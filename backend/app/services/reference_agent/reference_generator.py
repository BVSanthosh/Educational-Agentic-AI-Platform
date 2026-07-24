from fastapi import HTTPException 
from langchain.tools import tool
from langchain.agents import create_agent
from langchain.agents.middleware import ModelCallLimitMiddleware, ToolCallLimitMiddleware, ToolRetryMiddleware, ModelRetryMiddleware
from langgraph.checkpoint.memory import InMemorySaver
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_tavily import TavilySearch
from typing import Literal, AsyncGenerator
from backend.app.core.config import env
from app.services.reference_agent.reference_prompt import get_reference_prompt
from app.schemas import ReferenceOutput, TavilySearchInput, TavilySearchOutput, TavilySearchError

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
    ModelCallLimitMiddleware(
        run_limit=4
    ),
    ToolCallLimitMiddleware(
        tool_name="web_search",
        run_limit=2
    ),
    ModelRetryMiddleware(
        max_retries=2,
        backoff_factor=2,
        initial_delay=1,
        on_failure="continue",
    ),
    ToolRetryMiddleware(
        tools=["web_search"],
        max_retries=1,
        backoff_factor=2,
        initial_delay=1,
        on_failure="continue"
    )
]

reference_agent = create_agent(
    model=llm,
    tools=[web_search],
    system_prompt=SYSTEM_PROMPT,
    response_format=ReferenceOutput,
    middleware=agent_middleware,
    checkpointer=InMemorySaver()
)

async def get_references_stream(input: str) -> AsyncGenerator[str, None]:
    stream = await reference_agent.astream_events(
        {"messages": [{"role": "user", "content": input}]},
        {"configurable": {"thread_id": "1"}},
        version="v3")
    try:
        async for message in stream.messages:
            async for delta in message.text:
                yield delta
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

async def get_references(input: str) -> ReferenceOutput:
    try:
        response = await reference_agent.ainvoke(
            {"messages": [{"role": "user", "content": input}]},
            {"configurable": {"thread_id": "1"}}
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
    if not response or not hasattr(response, "structured_response"):
        raise HTTPException(status_code=500, detail="An error occured while calling the agent. Please try again later.")

    return response["structured_response"]