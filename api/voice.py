from fastapi import APIRouter
from voice.pipeline import get_pipeline

router = APIRouter(prefix="/voice", tags=["voice"])


@router.post("/toggle")
def toggle_voice(enabled: bool):
    pipeline = get_pipeline()
    if enabled and not pipeline.enabled:
        pipeline.start()
    elif not enabled and pipeline.enabled:
        pipeline.stop()
    return {"enabled": pipeline.enabled}


@router.get("/status")
def voice_status():
    return {"enabled": get_pipeline().enabled}
