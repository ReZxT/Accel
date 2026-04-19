import sqlite3
import json
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Optional

import holidays as holidays_lib

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


def _holiday_name(d: date) -> Optional[str]:
    return PL_HOLIDAYS.get(d)


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


async def calendar_add_event(
    title: str,
    date: str,
    time: str = None,
    description: str = None,
    recurring: str = "none",
) -> str:
    """Add an event to the calendar.
    date: YYYY-MM-DD
    time: HH:MM (optional, omit for all-day)
    recurring: none | daily | weekly | monthly | yearly
    """
    try:
        datetime.strptime(date, "%Y-%m-%d")
    except ValueError:
        return "Error: date must be YYYY-MM-DD format"
    if time:
        try:
            datetime.strptime(time, "%H:%M")
        except ValueError:
            return "Error: time must be HH:MM format"
    db = _conn()
    cur = db.execute(
        "INSERT INTO events (title, date, time, description, all_day, recurring) VALUES (?,?,?,?,?,?)",
        (title, date, time, description, 0 if time else 1, recurring or "none"),
    )
    db.commit()
    event_id = cur.lastrowid
    db.close()
    time_str = f" at {time}" if time else " (all day)"
    recur_str = f", recurring {recurring}" if recurring and recurring != "none" else ""
    return f"Event added (id={event_id}): '{title}' on {date}{time_str}{recur_str}"


async def calendar_get_events(start_date: str, end_date: str = None) -> str:
    """Get events and holidays for a date or date range.
    start_date: YYYY-MM-DD
    end_date: YYYY-MM-DD (optional, defaults to start_date for single day)
    """
    try:
        start = datetime.strptime(start_date, "%Y-%m-%d").date()
    except ValueError:
        return "Error: start_date must be YYYY-MM-DD"
    if end_date:
        try:
            end = datetime.strptime(end_date, "%Y-%m-%d").date()
        except ValueError:
            return "Error: end_date must be YYYY-MM-DD"
    else:
        end = start

    db = _conn()
    rows = db.execute(
        "SELECT * FROM events WHERE date BETWEEN ? AND ? ORDER BY date, time",
        (start_date, end_date or start_date),
    ).fetchall()
    db.close()

    events_by_date: dict[str, list] = {}
    for row in rows:
        events_by_date.setdefault(row["date"], []).append(_format_event(row))

    # walk the date range
    lines = []
    current = start
    while current <= end:
        ds = current.strftime("%Y-%m-%d")
        dow = current.strftime("%A")
        holiday = _holiday_name(current)
        is_weekend = current.weekday() >= 5

        day_parts = [f"{ds} ({dow})"]
        if holiday:
            day_parts.append(f"🇵🇱 Holiday: {holiday}")
        if is_weekend and not holiday:
            day_parts.append("Weekend")

        ev_list = events_by_date.get(ds, [])
        for ev in ev_list:
            t = f" {ev['time']}" if ev.get("time") else ""
            rec = f" [{ev['recurring']}]" if ev.get("recurring", "none") != "none" else ""
            desc = f" — {ev['description']}" if ev.get("description") else ""
            day_parts.append(f"  • [{ev['id']}] {ev['title']}{t}{rec}{desc}")

        lines.append(" | ".join(day_parts[:2]) if not ev_list and not holiday and not is_weekend else "\n  ".join(day_parts))
        current += timedelta(days=1)

    return "\n".join(lines) if lines else "No data."


async def calendar_delete_event(event_id: int) -> str:
    """Delete a calendar event by its id."""
    db = _conn()
    row = db.execute("SELECT title, date FROM events WHERE id=?", (event_id,)).fetchone()
    if not row:
        db.close()
        return f"Event id={event_id} not found."
    db.execute("DELETE FROM events WHERE id=?", (event_id,))
    db.commit()
    db.close()
    return f"Deleted event [{event_id}]: '{row['title']}' on {row['date']}"


async def calendar_today() -> str:
    """Get today's date, day, holiday status, and scheduled events."""
    return await calendar_get_events(date.today().strftime("%Y-%m-%d"))
