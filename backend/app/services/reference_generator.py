from langchain.tools import tool
from langchain.agents import create_agent
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_tavily import TavilySearch
from typing import Literal, AsyncGenerator
from config import env
from utils import read_prompt
from schemas import ReferencesOutput, TavilySearchInput, TavilySearchOutput, TavilySearchError

PROMPT_FILE_NAME = "references.md"
SYSTEM_PROMPT = read_prompt(PROMPT_FILE_NAME)

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
    model="gemini-2.5-flash",
    api_key = env.GOOGLE_API_KEY,
    temperature=0.0,
    max_tokens=None,
    timeout=None,
    max_retries=2,
)

agent = create_agent(
    model=llm,
    tools=[web_search],
    system_prompt=SYSTEM_PROMPT,
    response_format=ReferencesOutput,
)

async def get_stream_generator(input: str) -> AsyncGenerator[str, None]:
    stream = await agent.astream_events({
        "messages": [
            {
                "role": "user",
                "content": input
            }
        ]
    }, version="v3")

    async for message in stream.messages:
        async for delta in message.text:
            yield delta