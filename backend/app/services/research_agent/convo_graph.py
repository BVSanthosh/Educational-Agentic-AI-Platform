from typing import Any
from langgraph.graph import StateGraph, START, END
from langgraph.prebuilt import ToolNode, tools_condition
from langgraph.checkpoint.memory import InMemorySaver
from langchain_core.messages import HumanMessage
from langchain_core.runnables import RunnableConfig
from app.services.research_agent.convo_state import ConvoState
from app.services.research_agent.convo_nodes import clarify_research
from app.services.research_agent.convo_tools import write_research_report

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
graph_builder.add_edge("interviewer", END)
 
checkpointer = InMemorySaver()
app = graph_builder.compile(checkpointer=checkpointer)

async def get_research(topic: str) -> str:
    config: RunnableConfig = {"configurable": {"thread_id": "user_1"}}
    message: Any = {"messages": HumanMessage(content=topic)}

    response = await app.ainvoke(message, config)
    last_message_content = response["messages"][-1].content

    if isinstance(last_message_content, list):
        final_message = "".join([
            block["text"] for block in last_message_content 
            if isinstance(block, dict) and block.get("type") == "text"
        ])
    else:
        final_message = str(last_message_content)

    return final_message