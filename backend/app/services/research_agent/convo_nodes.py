from langchain_core.messages import SystemMessage
from app.services.research_agent.convo_state import ConvoState
from app.services.research_agent.convo_prompt import get_convo_prompt
from app.services.research_agent.llm import llm
from app.services.research_agent.convo_tools import write_research_report

async def clarify_research(state: ConvoState):
    CONVO_PROMPT: SystemMessage = get_convo_prompt()
    messages: list = [CONVO_PROMPT] + state["messages"]

    llm_with_tools = llm.bind_tools([write_research_report])
    response = await llm_with_tools.ainvoke(messages)

    return {"messages": response}
