from logging_config import setup_logging
setup_logging()

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from api.chat import router as chat_router
from api.approve import router as approve_router
from api.settings import router as settings_router
from api.embeddings import router as embeddings_router
from api.voice import router as voice_router
from api.music import router as music_router
from api.canvas import router as canvas_router
from api.notes import router as notes_router
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
app.include_router(voice_router)
app.include_router(music_router)
app.include_router(canvas_router)
app.include_router(notes_router)

if __name__ == "__main__":
    uvicorn.run("main:app", host=config.host, port=config.port, reload=False)
