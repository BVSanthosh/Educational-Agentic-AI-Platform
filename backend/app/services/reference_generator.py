from langchain_google_genai import ChatGoogleGenerativeAI
from ..config import env
from ..utils import read_prompt

PROMPT_FILE_NAME = "reference_generator.py"
SYSTEM_PROMPT = read_prompt(PROMPT_FILE_NAME)

agent = ChatGoogleGenerativeAI(
    model="gemini-2.5-flash",
    temperature=0.0,
    api_key = env.GOOGLE_API_KEY,
    system_prompt=SYSTEM_PROMPT
    google_search=True
)

def get_reference_response(topic: str):
    return ""