from typing import Any
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.types import Send
from app.services.research_agent.research_subgraph.research_nodes import (
    research_outline,
    research_worker,
    write_report,
    report_feedback,
)
from app.services.research_agent.research_subgraph.research_state import ResearchOutputState, ResearchState

async def route_gather_source(state: ResearchState):
    return [Send("extract_source", {"query": query}) for query in state["search_queries"]]

def route_final_draft(state: ResearchState):
    MAX_REWRITES = 2
    feedback = state.get("feedback_result")

    if not feedback:
        return "review_report"

    if feedback == "PASS" or state.get("rewrites", 0) >= MAX_REWRITES:
        return END

    return "review_report"

graph_builder = StateGraph(ResearchState)

graph_builder.add_node("research_outline", research_outline)
graph_builder.add_node("extract_source", research_worker)
graph_builder.add_node("write_report", write_report)
graph_builder.add_node("review_report", report_feedback)

graph_builder.add_edge(START, "research_outline")
graph_builder.add_edge("extract_source", "write_report")
graph_builder.add_edge("review_report", "write_report")

graph_builder.add_conditional_edges(
    "research_outline",
    route_gather_source,
    ["extract_source"]
)

graph_builder.add_conditional_edges(
    "write_report",
    route_final_draft,
    {
        "review_report": "review_report",
        END: END
    }
)

checkpointer = InMemorySaver()
# add checkpointer=checkpointer below
app = graph_builder.compile()