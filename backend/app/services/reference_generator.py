from langchain.agents import create_agent
from langchain_google_genai import ChatGoogleGenerativeAI
from config import env
from utils import read_prompt
from schemas import ReferencesOutput

PROMPT_FILE_NAME = "references.md"
SYSTEM_PROMPT = read_prompt(PROMPT_FILE_NAME)

llm = ChatGoogleGenerativeAI(
    model="gemini-2.5-flash",
    api_key = env.GOOGLE_API_KEY,
    temperature=0.0,
    max_tokens=None,
    timeout=None,
    max_retries=2,
    tools=[{"type": "google_search"}]
)

agent = create_agent(
    model=llm,
    tools=[],
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