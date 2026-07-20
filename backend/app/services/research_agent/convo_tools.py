from typing import Any
from langchain.tools import tool
from langchain_core.runnables import RunnableConfig
from app.schemas.research_schema import ResarchSubject
from app.services.research_agent.research_subgraph.research_subgraph import app

@tool(args_schema=ResarchSubject)
async def write_research_report(subject_matter: str):
    """
    Generates a research report given a subject matter

    Args: 
        subject_matter: the subject matter for the research
    """

    config: RunnableConfig = {"configurable": {"thread_id": "user_1"}}
    input: Any = {"subject_matter": subject_matter}

    response = await app.ainvoke(input, config)
    return response["research_report"]