from pydantic_settings import BaseSettings, SettingsConfigDict

from pathlib import Path

BASE_DIR = Path(__file__).parent.parent.parent

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=BASE_DIR / ".env", 
        env_file_encoding="utf-8", 
        validate_default=False
    )
 
    GEMINI_API_KEY: str = "gemini_api_key"
    TAVILY_API_KEY: str = "tavily_api_key"
    LANGSMITH_API_KEY: str = "langsmith_api_key"
    LANGCHAIN_TRACING_V2: str = "langsmith_tracing"
    DEBUG: bool = True
    POSTGRES_USER: str = "admin"
    POSTGRES_PASSWORD: str = "admin123"
    POSTGRES_DB: str = "mydb"
    POSTGRES_HOST: str = "localhost"
    POSTGRES_PORT: int = 5432
    SECRET_KEY: str = "f054b0882fedf7660687c56c7306175e7bf210e209cb9425fb1ceaf3027560b8"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    @property
    def DATABASE_URL(self) -> str:
        return f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"

env = Settings()