from typing import AsyncGenerator
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
    sutoflush=False
)

class Base(DeclarativeBase):
    pass

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise

checkpointer_pool: AsyncConnectionPool | None = None

def get_checkpointer_pool() -> AsyncConnectionPool:
    if checkpointer_pool is None:
        raise RuntimeError("Checkpointer pool is not initialised")
    return checkpointer_pool
