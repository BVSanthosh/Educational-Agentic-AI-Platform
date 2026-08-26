from fastapi import HTTPException, Request, status
from typing import AsyncGenerator, Any
from psycopg_pool import AsyncConnectionPool
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from app.core.config import env

engine = create_async_engine(
    env.DATABASE_URL,
    echo=env.DEBUG, 
    pool_size=20,
    max_overflow=10,
    pool_pre_ping=True
)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False
)

class Base(DeclarativeBase):
    pass

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise

def get_checkpointer_pool(request: Request) -> AsyncConnectionPool[Any]:
    pool: AsyncConnectionPool[Any] | None = getattr(request.app.state, "checkpointer_pool", None)
    
    if pool is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Checkpointer connection pool is not initialized",
        )
        
    return pool
