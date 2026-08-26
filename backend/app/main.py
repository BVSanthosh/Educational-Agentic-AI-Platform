from fastapi import FastAPI
from typing import Any
from contextlib import asynccontextmanager
from fastapi.middleware.cors import CORSMiddleware
from psycopg_pool import AsyncConnectionPool
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from app.core.config import env
from app.core.database import engine
from sqlalchemy import text
from app.api import (
    reference_router,
    research_router, 
    summary_router,
    space_router,
    user_router, 
    document_router
)
from app.services import (
    init_reference_agent,
    init_research_agent, 
    init_summary_agent
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
    
    # 1. Initialize and open the connection pool
    pool: AsyncConnectionPool[Any] = AsyncConnectionPool(
        conninfo=conn_str,
        max_size=20,
        open=False,
        kwargs={"autocommit": True}
    )
    await pool.open()
     
    # 2. Run migrations/setup for the checkpointer tables
    async with pool.connection() as conn:
        checkpointer = AsyncPostgresSaver(conn)
        await checkpointer.setup()
    
    # 3. Store on app.state (accessible globally via any Request)
    app.state.checkpointer_pool = pool
    
    # Initialize your agents using the pool
    init_reference_agent(pool)
    init_research_agent(pool)
    init_summary_agent(pool)

    yield 

    # 4. Graceful shutdown
    if hasattr(app.state, "checkpointer_pool") and app.state.checkpointer_pool:
        print("Closing checkpointer pool...")
        await app.state.checkpointer_pool.close()

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
app.include_router(document_router)
app.include_router(reference_router)
app.include_router(research_router)
app.include_router(summary_router)

@app.get("/health", tags=["Health"])
async def health_check():
    return {"status": "ok", "environment": "test" if env.DEBUG else "production"}