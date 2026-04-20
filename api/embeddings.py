import asyncio
import subprocess
import httpx
from fastapi import APIRouter

router = APIRouter()

BGE_MODEL = "/mnt/WD/Models/bge-m3-q8_0.gguf"
GPU_EMBED_PORT = 8083

_proc: subprocess.Popen | None = None
_refcount = 0
_lock = asyncio.Lock()


async def _wait_ready(port: int, timeout: int = 30) -> bool:
    async with httpx.AsyncClient() as client:
        for _ in range(timeout):
            await asyncio.sleep(1)
            try:
                r = await client.get(f"http://localhost:{port}/health", timeout=2)
                if r.status_code == 200:
                    return True
            except Exception:
                pass
    return False


@router.post("/embeddings/start")
async def start_gpu_embeddings():
    global _proc, _refcount
    async with _lock:
        _refcount += 1
        if _proc is not None and _proc.poll() is None:
            return {"status": "already_running", "port": GPU_EMBED_PORT}
        _proc = subprocess.Popen([
            "llama-server",
            "--model", BGE_MODEL,
            "-ngl", "99",
            "--port", str(GPU_EMBED_PORT),
            "--embeddings",
            "--pooling", "mean",
            "--ctx-size", "8192",
            "--batch-size", "2048",
            "--log-disable",
        ])
    ready = await _wait_ready(GPU_EMBED_PORT)
    return {"status": "ready" if ready else "timeout", "port": GPU_EMBED_PORT}


@router.post("/embeddings/stop")
async def stop_gpu_embeddings():
    global _proc, _refcount
    async with _lock:
        _refcount = max(0, _refcount - 1)
        if _refcount > 0:
            return {"status": "still_in_use", "refcount": _refcount}
        if _proc is not None:
            _proc.terminate()
            try:
                _proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                _proc.kill()
            _proc = None
    return {"status": "stopped"}
