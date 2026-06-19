from pydantic_settings import BaseSettings, SettingsConfigDict
from pathlib import Path

BASE_DIR = Path.cwd().parent

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=BASE_DIR / ".env", env_file_encoding="utf-8")
    GOOGLE_API_KEY: str = "google_api_key"
    TAVILY_API_KEY: str = "tavily_api_key"

env = Settings()