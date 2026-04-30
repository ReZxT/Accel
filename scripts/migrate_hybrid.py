#!/usr/bin/env python3
"""Migrate Qdrant collections from single dense vector to named dense + sparse vectors.

Usage: .venv/bin/python scripts/migrate_hybrid.py [--dry-run]

For each collection:
1. Scroll all existing points (with vectors + payloads)
2. Delete the old collection
3. Recreate with named vectors: "dense" (1024-dim cosine) + "sparse"
4. Re-insert all points with the original dense vector + a new sparse vector computed from payload text
"""

import asyncio
import sys
import time

from qdrant_client import AsyncQdrantClient
from qdrant_client.models import (
    Distance, VectorParams, SparseVectorParams, SparseVector,
    PointStruct, NamedVector,
)

sys.path.insert(0, "/home/rezxt/bootstrap")
from memory.sparse import sparse_vector

QDRANT_URL = "http://localhost:6333"
DENSE_DIM = 1024

COLLECTIONS = ["facts", "procedures", "episodes", "sources", "notes"]

# sessions collection stores chat history, not semantic content — skip sparse
SKIP_SPARSE = {"sessions"}


def _text_from_payload(payload: dict) -> str:
    """Extract searchable text from a point's payload."""
    parts = []
    for key in ("text", "content", "title", "section", "filename", "filepath"):
        v = payload.get(key)
        if v and isinstance(v, str):
            parts.append(v)
    return " ".join(parts)


async def migrate(dry_run: bool = False):
    client = AsyncQdrantClient(url=QDRANT_URL)

    for name in COLLECTIONS:
        print(f"\n{'='*60}")
        print(f"Collection: {name}")
        print(f"{'='*60}")

        # scroll all points
        all_points = []
        offset = None
        while True:
            result = await client.scroll(
                collection_name=name,
                limit=500,
                offset=offset,
                with_payload=True,
                with_vectors=True,
            )
            points, next_offset = result
            all_points.extend(points)
            print(f"  scrolled {len(all_points)} points...", end="\r")
            offset = next_offset
            if offset is None:
                break

        print(f"  Total: {len(all_points)} points")

        if dry_run:
            sample = all_points[:3]
            for p in sample:
                text = _text_from_payload(p.payload)
                idx, vals = sparse_vector(text)
                print(f"  [{p.id}] {len(idx)} sparse tokens from: {text[:80]}...")
            print(f"  (dry run — skipping recreation)")
            continue

        # delete old collection
        print(f"  Deleting old collection...")
        await client.delete_collection(name)

        # recreate with named vectors
        print(f"  Creating with named vectors (dense + sparse)...")
        await client.create_collection(
            collection_name=name,
            vectors_config={"dense": VectorParams(size=DENSE_DIM, distance=Distance.COSINE)},
            sparse_vectors_config={"sparse": SparseVectorParams()},
            on_disk_payload=True,
        )

        # re-insert in batches
        batch_size = 100
        t0 = time.monotonic()
        for i in range(0, len(all_points), batch_size):
            batch = all_points[i:i + batch_size]
            new_points = []
            for p in batch:
                dense_vec = p.vector if isinstance(p.vector, list) else p.vector.get("dense", p.vector.get("", []))
                text = _text_from_payload(p.payload)
                sp_idx, sp_vals = sparse_vector(text)

                vectors = {"dense": dense_vec}
                if sp_idx:
                    vectors["sparse"] = SparseVector(indices=sp_idx, values=sp_vals)

                new_points.append(PointStruct(
                    id=p.id,
                    vector=vectors,
                    payload=p.payload,
                ))

            await client.upsert(collection_name=name, points=new_points)
            done = min(i + batch_size, len(all_points))
            elapsed = time.monotonic() - t0
            rate = done / elapsed if elapsed > 0 else 0
            print(f"  Inserted {done}/{len(all_points)} ({rate:.0f} pts/s)", end="\r")

        elapsed = time.monotonic() - t0
        print(f"  Done: {len(all_points)} points in {elapsed:.1f}s")

    await client.close()
    print(f"\nMigration complete.")


if __name__ == "__main__":
    dry = "--dry-run" in sys.argv
    if dry:
        print("DRY RUN — no changes will be made\n")
    asyncio.run(migrate(dry_run=dry))
