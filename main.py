import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from api.chat import router as chat_router
from api.approve import router as approve_router
from api.settings import router as settings_router
from api.embeddings import router as embeddings_router
from config import config

app = FastAPI(title="Bootstrap", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(chat_router)
app.include_router(approve_router)
app.include_router(settings_router)
app.include_router(embeddings_router)

if __name__ == "__main__":
    uvicorn.run("main:app", host=config.host, port=config.port, reload=True)
