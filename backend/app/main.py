from fastapi import FastAPI
from api.analysis import router as analysis_router

app = FastAPI()

app.include_router(analysis_router)

@app.get("/")
async def root():
    return "server running..."