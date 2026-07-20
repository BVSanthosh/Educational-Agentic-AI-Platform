from pydantic_settings import BaseSettings, SettingsConfigDict

from pathlib import Path

BASE_DIR = Path(__file__).parent.parent

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=BASE_DIR / ".env", env_file_encoding="utf-8", validate_default=False)
    GEMINI_API_KEY: str = "gemini_api_key"
    TAVILY_API_KEY: str = "tavily_api_key"
    LANGSMITH_API_KEY: str = "langsmith_api_key"
    LANGCHAIN_TRACING_V2: str = "langsmith_tracing"

env = Settings()