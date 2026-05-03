import json
import sqlite3
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Query

from tools.career_tools import career_fetch_jobs as _fetch_jobs

router = APIRouter(prefix="/career", tags=["career"])

DATA_DIR = Path(__file__).parent.parent / "data"
DB_PATH = DATA_DIR / "career.db"
PROFILE_PATH = DATA_DIR / "career_profile.json"

TIERS = {"S": (90, 100), "A": (75, 89), "B": (60, 74), "C": (40, 59), "D": (0, 39)}


def _db():
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("""CREATE TABLE IF NOT EXISTS offers (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        company TEXT NOT NULL DEFAULT '',
        url TEXT DEFAULT '',
        description TEXT DEFAULT '',
        requirements TEXT DEFAULT '',
        salary TEXT DEFAULT '',
        location TEXT DEFAULT '',
        remote TEXT DEFAULT '',
        rating INTEGER DEFAULT -1,
        notes TEXT DEFAULT '',
        status TEXT DEFAULT 'new',
        date_added TEXT NOT NULL,
        date_updated TEXT NOT NULL
    )""")
    conn.commit()
    return conn


def _tier(rating: int) -> str:
    if rating < 0:
        return "?"
    for t, (lo, hi) in TIERS.items():
        if lo <= rating <= hi:
            return t
    return "?"


@router.get("/profile")
async def get_profile():
    if PROFILE_PATH.exists():
        return json.loads(PROFILE_PATH.read_text())
    return {}


@router.get("/offers")
async def get_offers():
    conn = _db()
    rows = conn.execute("SELECT * FROM offers ORDER BY rating DESC, date_added DESC").fetchall()
    conn.close()
    offers = []
    for r in rows:
        d = dict(r)
        d["tier"] = _tier(r["rating"])
        offers.append(d)
    return {"offers": offers}


@router.get("/tierlist")
async def get_tierlist():
    conn = _db()
    rows = conn.execute("SELECT * FROM offers WHERE rating >= 0 ORDER BY rating DESC").fetchall()
    conn.close()
    tiers = {t: [] for t in TIERS}
    for r in rows:
        t = _tier(r["rating"])
        d = dict(r)
        d["tier"] = t
        tiers[t].append(d)
    return {"tiers": tiers}


@router.post("/fetch")
async def fetch_jobs(
    keywords: str = Query("", description="Search keywords"),
    seniority: str = Query("", description="junior/mid/senior"),
    category: str = Query("", description="backend/frontend/etc"),
    location: str = Query("", description="City name"),
    salary_min: int = Query(0, description="Minimum salary"),
    limit: int = Query(20, description="Max results"),
):
    result = await _fetch_jobs(
        keywords=keywords, seniority=seniority, category=category,
        location=location, salary_min=salary_min, limit=limit, save=True,
    )
    conn = _db()
    rows = conn.execute("SELECT * FROM offers ORDER BY rating DESC, date_added DESC").fetchall()
    conn.close()
    offers = []
    for r in rows:
        d = dict(r)
        d["tier"] = _tier(r["rating"])
        offers.append(d)
    return {"message": result, "offers": offers}
