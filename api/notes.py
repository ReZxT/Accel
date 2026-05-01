import json
import os
import uuid
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

router = APIRouter(prefix="/notes", tags=["notes"])

VAULTS_FILE = os.path.join(os.path.dirname(__file__), "..", "config", "vaults.json")


def _load_vaults() -> list[dict]:
    try:
        with open(VAULTS_FILE, encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return []


def _save_vaults(vaults: list[dict]) -> None:
    os.makedirs(os.path.dirname(VAULTS_FILE), exist_ok=True)
    with open(VAULTS_FILE, "w", encoding="utf-8") as f:
        json.dump(vaults, f, indent=2)


def _get_vault(vault_id: str) -> dict:
    for v in _load_vaults():
        if v["id"] == vault_id:
            return v
    raise HTTPException(status_code=404, detail="Vault not found")


def _safe_path(vault_root: str, rel: str) -> str:
    full = os.path.realpath(os.path.join(vault_root, rel))
    if not full.startswith(os.path.realpath(vault_root)):
        raise HTTPException(status_code=400, detail="Path outside vault")
    return full


def _build_tree(root: str, rel: str = "") -> list[dict]:
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


# --- Vault management ---

@router.get("/vaults")
async def get_vaults():
    return _load_vaults()


class VaultBody(BaseModel):
    name: str
    path: str


@router.post("/vaults")
async def add_vault(body: VaultBody):
    path = os.path.expanduser(body.path)
    if not os.path.isdir(path):
        raise HTTPException(status_code=400, detail="Path does not exist or is not a directory")
    vaults = _load_vaults()
    vault = {"id": str(uuid.uuid4()), "name": body.name, "path": path}
    vaults.append(vault)
    _save_vaults(vaults)
    return vault


@router.delete("/vaults/{vault_id}")
async def delete_vault(vault_id: str):
    if vault_id == "default":
        raise HTTPException(status_code=400, detail="Cannot delete the default vault")
    vaults = _load_vaults()
    vaults = [v for v in vaults if v["id"] != vault_id]
    _save_vaults(vaults)
    return {"ok": True}


# --- File operations ---

@router.get("/tree")
async def get_tree(vault: str = "default"):
    v = _get_vault(vault)
    return _build_tree(v["path"])


@router.get("/file")
async def get_file(path: str = Query(...), vault: str = "default"):
    v = _get_vault(vault)
    full = _safe_path(v["path"], path)
    if not os.path.isfile(full):
        raise HTTPException(status_code=404, detail="File not found")
    with open(full, encoding="utf-8") as f:
        return {"path": path, "content": f.read()}


class WriteBody(BaseModel):
    path: str
    content: str
    vault: str = "default"


@router.put("/file")
async def put_file(body: WriteBody):
    if not body.path.endswith('.md'):
        raise HTTPException(status_code=400, detail="Only .md files allowed")
    v = _get_vault(body.vault)
    full = _safe_path(v["path"], body.path)
    os.makedirs(os.path.dirname(full), exist_ok=True)
    with open(full, "w", encoding="utf-8") as f:
        f.write(body.content)
    return {"ok": True}
