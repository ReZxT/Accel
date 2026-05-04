"""Seed the Qdrant 'tools' collection from TOOL_DETAILS.

Usage: cd /home/rezxt/bootstrap && .venv/bin/python -m prefetch.seed_tools [--force]
"""
import asyncio
import hashlib
import logging
import re
import sys

from qdrant_client.models import (
    Distance, VectorParams, SparseVectorParams, PointStruct, SparseVector,
)

from memory.facts import get_client
from memory.hybrid import compute_query_vectors
from tools.tool_descriptions import TOOL_DETAILS
from tools.code_tools import IRREVERSIBLE_TOOLS
from prefetch.tools_retrieval import TOOL_CATEGORIES, TOOL_MODES, _extract_one_liner

log = logging.getLogger(__name__)

COLLECTION = "tools"


def _tool_id(name: str) -> str:
    return hashlib.md5(name.encode()).hexdigest()


def _extract_param_semantics(spec: str) -> str:
    """Extract parameter names and descriptions, stripping type annotations."""
    lines = []
    for line in spec.split("\n"):
        line = line.strip()
        # Match lines like "  param_name (type, required/optional): description"
        m = re.match(r"(\w+)\s*\([^)]*\):\s*(.+)", line)
        if m:
            lines.append(f"{m.group(1)}: {m.group(2)}")
    return ". ".join(lines)


def _build_embed_text(name: str, one_liner: str, spec: str) -> str:
    """Build the text to embed — semantically meaningful parts only."""
    params = _extract_param_semantics(spec)
    parts = [f"{name}. {one_liner}"]
    if params:
        parts.append(f"Parameters: {params}")
    return ". ".join(parts)


async def ensure_tools_collection() -> None:
    client = get_client()
    collections = await client.get_collections()
    names = [c.name for c in collections.collections]
    if COLLECTION in names:
        return
    await client.create_collection(
        collection_name=COLLECTION,
        vectors_config={"dense": VectorParams(size=1024, distance=Distance.COSINE)},
        sparse_vectors_config={"sparse": SparseVectorParams()},
    )
    log.info("Created '%s' collection", COLLECTION)


async def seed_tools(force: bool = False) -> int:
    client = get_client()
    await ensure_tools_collection()

    if not force:
        info = await client.get_collection(COLLECTION)
        if info.points_count >= len(TOOL_DETAILS):
            log.info("Tools collection already has %d points, skipping (use --force to re-seed)", info.points_count)
            return 0

    points = []
    for name, spec in TOOL_DETAILS.items():
        one_liner = _extract_one_liner(name)
        embed_text = _build_embed_text(name, one_liner, spec)
        dense_vec, sp_idx, sp_vals = await compute_query_vectors(embed_text)

        vectors = {"dense": dense_vec}
        if sp_idx:
            vectors["sparse"] = SparseVector(indices=sp_idx, values=sp_vals)

        points.append(PointStruct(
            id=_tool_id(name),
            vector=vectors,
            payload={
                "name": name,
                "one_liner": one_liner,
                "full_spec": spec,
                "category": TOOL_CATEGORIES.get(name, "general"),
                "irreversible": name in IRREVERSIBLE_TOOLS,
                "modes": TOOL_MODES.get(name, []),
            },
        ))

    await client.upsert(collection_name=COLLECTION, points=points)
    log.info("Seeded %d tools into '%s'", len(points), COLLECTION)
    return len(points)


async def main():
    logging.basicConfig(level=logging.INFO)
    force = "--force" in sys.argv
    count = await seed_tools(force=force)
    if count:
        print(f"Seeded {count} tools")
    else:
        print("Already seeded (use --force to re-embed)")


if __name__ == "__main__":
    asyncio.run(main())
