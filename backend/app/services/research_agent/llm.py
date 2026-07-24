from langchain_google_genai import ChatGoogleGenerativeAI
from backend.app.core.config import env

llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash", api_key=env.GEMINI_API_KEY ,temperature=0.0)