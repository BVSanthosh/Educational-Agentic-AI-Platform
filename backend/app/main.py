from fastapi import FastAPI
from backend.app.api.references import router as references

app = FastAPI()

app.include_router(references)

@app.get("/")
async def root():
    return "server running..."