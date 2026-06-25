from fastapi import FastAPI
from app.api import router as reference_router

app = FastAPI()

app.include_router(reference_router)

@app.get("/")
async def root():
    return "server running..."