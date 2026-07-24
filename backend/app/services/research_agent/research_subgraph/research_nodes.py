from typing import cast, Any
from langchain_tavily import TavilySearch
from backend.app.core.config import env
from app.services.research_agent.llm import llm
from app.services.research_agent.research_subgraph.research_state import ResearchState, Query
from app.services.research_agent.research_subgraph.research_prompt import (
    get_feedback_prompt, 
    get_outline_prompt, 
    get_write_report_prompt, 
    get_rewrite_report_prompt
)
from app.schemas.research_schema import OutlineSchema, Resource, Draft, Feedback

tavily_client = TavilySearch(tavily_api_key=env.TAVILY_API_KEY)

async def research_outline(state: ResearchState):
    OUTLINE_PROMPT = get_outline_prompt()

    system_message = OUTLINE_PROMPT
    human_message = f"""
    Here is the subject matter the research report will be about.

    === SUBJECT MATTER ===
    {state["subject_matter"]}
    """

    structured_llm = llm.with_structured_output(
        schema=OutlineSchema.model_json_schema(), 
        method="json_schema"
    )
 
    response = cast(
        dict[str, Any], 
        await structured_llm.ainvoke([system_message, human_message])
    )

    return {
        "outline": response["outline"],
        "search_queries": response["search_queries"]
    }

async def research_worker(state: Query):
    configured_search = tavily_client.bind(
        max_results=2, 
        search_depth="advanced",
        include_raw_content=True
    )

    search_results = await configured_search.ainvoke({"query": state["query"]})

    if isinstance(search_results, dict) and "detail" in search_results:
        return {"research_results": []}
    
    print(search_results)
    
    results_list = search_results.get("results", [])

    resources: list[Resource] = []
    for result in results_list:
        content_body = result.get("raw_content") or result.get("content") or ""
        resource = Resource(url=result.get("url"), title=result.get("title"), contents=content_body)
        resources.append(resource) 

    return {"research_results": resources}

async def write_report(state: ResearchState):
    system_message = ""
    human_message = ""

    print(f"WRITE: state[\"research_results\"]")

    if state.get("feedback_report"):
        REWRITE_REPORT_PROMPT = get_rewrite_report_prompt(state["subject_matter"], state["outline"], state["research_results"], state["feedback_report"])

        system_message = REWRITE_REPORT_PROMPT
        human_message = f"""
        Here is the report draft to edit. 

        === RESEARCH REPORT DRAFT ===
        {state["research_report"]}
        """
    else:
        WRITE_REPORT_PROMPT = get_write_report_prompt()

        system_message = WRITE_REPORT_PROMPT
        human_message = f"""
        Here is the subject matter of the research, report outline and references to write the research report.

        === SUBJECT MATTER ===
        {state["subject_matter"]}

        === OUTLINE ===
        {state["outline"]}

        === REFERENCE MATERIAL ===
        {state["research_results"]}
        """

    structured_llm = llm.with_structured_output(
        schema=Draft.model_json_schema(), 
        method="json_schema"
    )

    response = cast(
        dict[str, Any],
        await structured_llm.ainvoke([system_message, human_message])
    )

    return {
        "research_report": response["report_draft"]
    }

async def report_feedback(state: ResearchState):    
    FEEDBACK_PROMPT = get_feedback_prompt(state["subject_matter"], state["outline"])

    system_message = FEEDBACK_PROMPT
    human_message = f"""
    Here is the draft of the research report to base the feedback on.

    === RESEARCH REPORT DRAFT ===
    {state["research_report"]}
    """

    structured_llm = llm.with_structured_output(
        schema=Feedback.model_json_schema(),
        method="json_schema"
    )

    response = cast(
        dict[str, Any],
        await structured_llm.ainvoke([system_message, human_message])
    )
    
    current_rewrites = state.get("rewrites", 0)

    return {
        "feedback_result": response["result"],
        "feedback_report": response["feedback"],
        "rewrites": current_rewrites + 1
    }