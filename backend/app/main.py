from fastapi import FastAPI
from app.api import router as reference_router
from app.api import router as research_router
from app.api import router as summary_router

app = FastAPI()

app.include_router(reference_router)
app.include_router(research_router)
app.include_router(summary_router)

@app.get("/")
async def root():
    return "Server running..."