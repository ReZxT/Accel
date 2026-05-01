import os
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

router = APIRouter(prefix="/notes", tags=["notes"])

VAULT_ROOT = "/mnt/WD/The Ideas"


def _safe_path(rel: str) -> str:
    """Resolve a vault-relative path and reject traversal attempts."""
    full = os.path.realpath(os.path.join(VAULT_ROOT, rel))
    if not full.startswith(os.path.realpath(VAULT_ROOT)):
        raise HTTPException(status_code=400, detail="Path outside vault")
    return full


def _build_tree(root: str, rel: str = "") -> list[dict]:
    """Recursively build a file tree, markdown files only."""
    entries = []
    try:
        items = sorted(os.scandir(root), key=lambda e: (not e.is_dir(), e.name.lower()))
    except PermissionError:
        return []
    for item in items:
        if item.name.startswith('.') or item.name.startswith('_'):
            continue
        item_rel = os.path.join(rel, item.name) if rel else item.name
        if item.is_dir():
            children = _build_tree(item.path, item_rel)
            if children:
                entries.append({"name": item.name, "path": item_rel, "type": "dir", "children": children})
        elif item.name.endswith('.md'):
            entries.append({"name": item.name, "path": item_rel, "type": "file"})
    return entries


@router.get("/tree")
async def get_tree():
    return _build_tree(VAULT_ROOT)


@router.get("/file")
async def get_file(path: str = Query(...)):
    full = _safe_path(path)
    if not os.path.isfile(full):
        raise HTTPException(status_code=404, detail="File not found")
    with open(full, encoding="utf-8") as f:
        return {"path": path, "content": f.read()}


class WriteBody(BaseModel):
    path: str
    content: str


@router.put("/file")
async def put_file(body: WriteBody):
    if not body.path.endswith('.md'):
        raise HTTPException(status_code=400, detail="Only .md files allowed")
    full = _safe_path(body.path)
    os.makedirs(os.path.dirname(full), exist_ok=True)
    with open(full, "w", encoding="utf-8") as f:
        f.write(body.content)
    return {"ok": True}
