import sqlite3
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Optional

import holidays as holidays_lib
from fastapi import APIRouter

router = APIRouter(prefix="/calendar", tags=["calendar"])

DB_PATH = Path(__file__).parent.parent / "data" / "calendar.db"
PL_HOLIDAYS = holidays_lib.Poland()


def _conn():
    db = sqlite3.connect(DB_PATH)
    db.row_factory = sqlite3.Row
    db.execute("""
        CREATE TABLE IF NOT EXISTS events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            date TEXT NOT NULL,
            time TEXT,
            description TEXT,
            all_day INTEGER DEFAULT 1,
            recurring TEXT DEFAULT 'none',
            created_at TEXT DEFAULT (datetime('now'))
        )
    """)
    db.commit()
    return db


def _format_event(row) -> dict:
    return {
        "id": row["id"],
        "title": row["title"],
        "date": row["date"],
        "time": row["time"],
        "description": row["description"],
        "all_day": bool(row["all_day"]),
        "recurring": row["recurring"],
    }


def _expand_recurring(events: list[dict], start: date, end: date) -> list[dict]:
    expanded = []
    for ev in events:
        ev_date = datetime.strptime(ev["date"], "%Y-%m-%d").date()
        rec = ev.get("recurring", "none")
        if rec == "none":
            expanded.append(ev)
            continue
        current = ev_date
        while current <= end:
            if current >= start:
                expanded.append({**ev, "date": current.strftime("%Y-%m-%d")})
            if rec == "daily":
                current += timedelta(days=1)
            elif rec == "weekly":
                current += timedelta(weeks=1)
            elif rec == "monthly":
                m = current.month + 1
                y = current.year + (m - 1) // 12
                m = (m - 1) % 12 + 1
                try:
                    current = current.replace(year=y, month=m)
                except ValueError:
                    break
            elif rec == "yearly":
                try:
                    current = current.replace(year=current.year + 1)
                except ValueError:
                    break
            else:
                break
    return expanded


@router.get("/events")
async def get_events(start: str, end: str):
    start_date = datetime.strptime(start, "%Y-%m-%d").date()
    end_date = datetime.strptime(end, "%Y-%m-%d").date()

    db = _conn()
    rows = db.execute(
        "SELECT * FROM events WHERE date BETWEEN ? AND ? ORDER BY date, time",
        (start, end),
    ).fetchall()
    recurring_rows = db.execute(
        "SELECT * FROM events WHERE recurring != 'none' AND date <= ?",
        (end,),
    ).fetchall()
    db.close()

    events = [_format_event(r) for r in rows]
    recurring = [_format_event(r) for r in recurring_rows if _format_event(r) not in events]
    all_events = _expand_recurring(events + recurring, start_date, end_date)

    holidays = []
    current = start_date
    while current <= end_date:
        name = PL_HOLIDAYS.get(current)
        if name:
            holidays.append({"date": current.strftime("%Y-%m-%d"), "title": name})
        current += timedelta(days=1)

    return {"events": all_events, "holidays": holidays}
