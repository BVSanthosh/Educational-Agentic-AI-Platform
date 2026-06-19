from langchain.tools import tool
from langchain.agents import create_agent
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_tavily import TavilySearch
from typing import Literal
from config import env
from utils import read_prompt
from schemas import ReferencesOutput, TavilySearchInput, TavilySearchOutput

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
    search_depth: Literal['basic', 'advanced', 'fast', 'ultra-fast'] = "basic"
) -> list[TavilySearchOutput] | None:
    """
    Search the web for relevant resources given the provided search query

    Args:
        query: the search query
        topic: the topic of search
        max_results: the maximum allowed results
        time_range: how far back the search should be done
        include_domains: any specific domains that the search should be based on
        search_depth: how deep the search should be

    """

    configured_search = tavily_client.bind(
        topic=topic, 
        max_results=max_results, 
        time_range=time_range, 
        include_domains=include_domains,
        search_depth=search_depth
    )
    
    search_results = configured_search.invoke({"query": query})

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

def get_reference_response(topic: str) -> ReferencesOutput:
    result = agent.invoke({
        "messages": [
            {
                "role": "user",
                "content": topic
            }
        ]
    })

    return result["structured_response"]