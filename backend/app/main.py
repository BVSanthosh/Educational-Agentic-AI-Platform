from fastapi import FastAPI
from contextlib import asynccontextmanager
from fastapi.middleware.cors import CORSMiddleware
from psycopg_pool import AsyncConnectionPool
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from app.core.config import env
from app.core.database import engine, checkpointer_pool
from sqlalchemy import text
from app.api import (
    reference_router,
    research_router,
    summary_router,
    space_router,
    user_router
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    print("Connecting to PostgreSQL...")

    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
    except Exception as e:
        print(f"Failed to connect to database: {e}")
        raise e

    conn_str = env.DATABASE_URL.replace("postgresql+asyncpg://", "postgresql://")

    checkpointer_pool = AsyncConnectionPool(
        conninfo=conn_str,
        max_size=20,
        kwargs={"autocommit": True}
    )
    await checkpointer_pool.open()

    async with checkpointer_pool.connection() as conn:
        checkpointer = AsyncPostgresSaver(conn)
        await checkpointer.setup()

    yield 

    if checkpointer_pool:
        await checkpointer_pool.close()

    print("closing database connection...")
    await engine.dispose()

app = FastAPI(
    title="Educational AI Platform",
    version="1.0.0",
    debug=env.DEBUG,
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)

app.include_router(user_router)
app.include_router(space_router)
app.include_router(reference_router)
app.include_router(research_router)
app.include_router(summary_router)

@app.get("/health", tags=["Health"])
async def health_check():
    return {"status": "ok", "environment": "test" if env.DEBUG else "production"}