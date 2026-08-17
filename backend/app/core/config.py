from pydantic_settings import BaseSettings, SettingsConfigDict

from pathlib import Path

BASE_DIR = Path(__file__).parent.parent.parent

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=BASE_DIR / ".env", 
        env_file_encoding="utf-8", 
        validate_default=False
    )

    # Application Server
    PRODUCTION: bool = False
    DEBUG: bool = True

    # Google's LLM
    GEMINI_API_KEY: str = "gemini_api_key"

    # Tavily Search
    TAVILY_API_KEY: str = "tavily_api_key"

    # LangSmith Tracing
    LANGSMITH_API_KEY: str = "langsmith_api_key"
    LANGCHAIN_TRACING_V2: str = "langsmith_tracing"


    # PostgreSQL Database
    POSTGRES_USER: str = "admin"
    POSTGRES_PASSWORD: str = "admin123"
    POSTGRES_DB: str = "mydb"
    POSTGRES_HOST: str = "localhost"
    POSTGRES_PORT: int = 5432

    # JWT Authentication
    SECRET_KEY: str = "secret_key"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 90
    ACCESS_TOKEN_TYPE: str = "access"
    REFRESH_TOKEN_TYPE: str = "refresh"

    # Google's OAuth
    GOOGLE_CLIENT_ID: str = "client_id"
    GOOGLE_CLIENT_SECRET:str = "client_secret"
    GOOGLE_REDIRECT_URI: str = "http://localhost:5173/auth/callback/google"
    
    # AWS
    AWS_ACCESS_KEY_ID: str = "your_access_key"
    AWS_SECRET_ACCESS_KEY: str = "your_secret_key"
    AWS_REGION: str = "ap-southeast-1"
    AWS_S3_BUCKET_NAME: str = "research-agent-reports"

    @property
    def DATABASE_URL(self) -> str:
        return f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"

env = Settings()