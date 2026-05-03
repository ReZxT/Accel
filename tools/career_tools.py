import json
import os
import sqlite3
from datetime import datetime
from pathlib import Path

import httpx

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


def _tier_for_rating(rating: int) -> str:
    if rating < 0:
        return "?"
    for tier, (lo, hi) in TIERS.items():
        if lo <= rating <= hi:
            return tier
    return "?"


def _load_profile() -> dict:
    if PROFILE_PATH.exists():
        return json.loads(PROFILE_PATH.read_text())
    return {}


def _save_profile(profile: dict):
    PROFILE_PATH.write_text(json.dumps(profile, indent=2, ensure_ascii=False))


async def career_get_profile(**kwargs) -> str:
    profile = _load_profile()
    if not profile:
        return "No career profile set up yet. Use career_update_profile to create one."
    return json.dumps(profile, indent=2, ensure_ascii=False)


async def career_update_profile(
    skills: str = None,
    experience: str = None,
    education: str = None,
    target_roles: str = None,
    preferred_stack: str = None,
    location_preference: str = None,
    salary_expectation: str = None,
    languages: str = None,
    strengths: str = None,
    notes: str = None,
    **kwargs,
) -> str:
    profile = _load_profile()
    for key in ("skills", "experience", "education", "target_roles", "preferred_stack",
                "location_preference", "salary_expectation", "languages", "strengths", "notes"):
        val = locals().get(key)
        if val is not None:
            profile[key] = val
    profile["updated_at"] = datetime.now().isoformat()
    _save_profile(profile)
    return f"Profile updated: {', '.join(k for k in profile if k != 'updated_at')}"


async def career_save_offer(
    title: str,
    company: str = "",
    url: str = "",
    description: str = "",
    requirements: str = "",
    salary: str = "",
    location: str = "",
    remote: str = "",
    rating: int = -1,
    notes: str = "",
    **kwargs,
) -> str:
    conn = _db()
    now = datetime.now().isoformat()
    conn.execute(
        """INSERT INTO offers (title, company, url, description, requirements, salary, location, remote, rating, notes, date_added, date_updated)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (title, company, url, description, requirements, salary, location, remote, rating, notes, now, now),
    )
    conn.commit()
    offer_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
    tier = _tier_for_rating(rating)
    conn.close()
    return f"Saved offer #{offer_id}: {title} @ {company} (rating: {rating}/100, tier: {tier})"


async def career_list_offers(
    status: str = None,
    min_rating: int = None,
    tier: str = None,
    **kwargs,
) -> str:
    conn = _db()
    query = "SELECT * FROM offers ORDER BY rating DESC, date_added DESC"
    rows = conn.execute(query).fetchall()
    conn.close()

    if status:
        rows = [r for r in rows if r["status"] == status]
    if min_rating is not None:
        rows = [r for r in rows if r["rating"] >= int(min_rating)]
    if tier:
        tier = tier.upper()
        if tier in TIERS:
            lo, hi = TIERS[tier]
            rows = [r for r in rows if lo <= r["rating"] <= hi]

    if not rows:
        return "No offers found."

    lines = []
    for r in rows:
        t = _tier_for_rating(r["rating"])
        rating_str = f"{r['rating']}/100" if r["rating"] >= 0 else "unrated"
        lines.append(f"#{r['id']} [{t}] {r['title']} @ {r['company']} — {rating_str} ({r['status']})")
        if r["salary"]:
            lines.append(f"   Salary: {r['salary']}")
        if r["location"]:
            loc = r["location"]
            if r["remote"]:
                loc += f" ({r['remote']})"
            lines.append(f"   Location: {loc}")
        if r["notes"]:
            lines.append(f"   Notes: {r['notes']}")
    return "\n".join(lines)


async def career_get_offer(offer_id: int = None, **kwargs) -> str:
    offer_id = offer_id or kwargs.get("id")
    if not offer_id:
        return "Provide offer_id."
    conn = _db()
    row = conn.execute("SELECT * FROM offers WHERE id = ?", (int(offer_id),)).fetchone()
    conn.close()
    if not row:
        return f"Offer #{offer_id} not found."
    return json.dumps(dict(row), indent=2, ensure_ascii=False)


async def career_rate_offer(offer_id: int = None, rating: int = None, notes: str = None, status: str = None, **kwargs) -> str:
    offer_id = offer_id or kwargs.get("id")
    if not offer_id:
        return "Provide offer_id."
    conn = _db()
    row = conn.execute("SELECT * FROM offers WHERE id = ?", (int(offer_id),)).fetchone()
    if not row:
        conn.close()
        return f"Offer #{offer_id} not found."

    updates = []
    params = []
    if rating is not None:
        updates.append("rating = ?")
        params.append(int(rating))
    if notes is not None:
        updates.append("notes = ?")
        params.append(notes)
    if status is not None:
        updates.append("status = ?")
        params.append(status)
    if not updates:
        conn.close()
        return "Nothing to update. Provide rating, notes, or status."

    updates.append("date_updated = ?")
    params.append(datetime.now().isoformat())
    params.append(int(offer_id))

    conn.execute(f"UPDATE offers SET {', '.join(updates)} WHERE id = ?", params)
    conn.commit()

    row = conn.execute("SELECT * FROM offers WHERE id = ?", (int(offer_id),)).fetchone()
    conn.close()
    tier = _tier_for_rating(row["rating"])
    return f"Updated offer #{offer_id}: {row['title']} — {row['rating']}/100 (tier {tier}, status: {row['status']})"


async def career_delete_offer(offer_id: int = None, **kwargs) -> str:
    offer_id = offer_id or kwargs.get("id")
    if not offer_id:
        return "Provide offer_id."
    conn = _db()
    row = conn.execute("SELECT title, company FROM offers WHERE id = ?", (int(offer_id),)).fetchone()
    if not row:
        conn.close()
        return f"Offer #{offer_id} not found."
    conn.execute("DELETE FROM offers WHERE id = ?", (int(offer_id),))
    conn.commit()
    conn.close()
    return f"Deleted offer #{offer_id}: {row['title']} @ {row['company']}"


async def career_tierlist(**kwargs) -> str:
    conn = _db()
    rows = conn.execute("SELECT * FROM offers WHERE rating >= 0 ORDER BY rating DESC").fetchall()
    conn.close()

    if not rows:
        return "No rated offers yet. Use career_rate_offer to rate saved offers."

    tiers: dict[str, list] = {t: [] for t in TIERS}
    for r in rows:
        t = _tier_for_rating(r["rating"])
        tiers[t].append(r)

    lines = []
    for tier_name in ("S", "A", "B", "C", "D"):
        offers = tiers[tier_name]
        if not offers:
            continue
        lines.append(f"\n{'='*40}")
        lines.append(f"  TIER {tier_name} ({TIERS[tier_name][0]}-{TIERS[tier_name][1]})")
        lines.append(f"{'='*40}")
        for r in offers:
            lines.append(f"  #{r['id']} {r['title']} @ {r['company']} — {r['rating']}/100")
            if r["salary"]:
                lines.append(f"       Salary: {r['salary']}")
            if r["notes"]:
                lines.append(f"       {r['notes']}")

    unrated = conn = _db()
    unrated_rows = conn.execute("SELECT * FROM offers WHERE rating < 0 ORDER BY date_added DESC").fetchall()
    conn.close()
    if unrated_rows:
        lines.append(f"\n{'='*40}")
        lines.append(f"  UNRATED ({len(unrated_rows)} offers)")
        lines.append(f"{'='*40}")
        for r in unrated_rows:
            lines.append(f"  #{r['id']} {r['title']} @ {r['company']}")

    return "\n".join(lines)


async def career_compare(offer_id: int = None, **kwargs) -> str:
    offer_id = offer_id or kwargs.get("id")
    if not offer_id:
        return "Provide offer_id."
    profile = _load_profile()
    if not profile:
        return "No career profile set up. Use career_update_profile first."
    conn = _db()
    row = conn.execute("SELECT * FROM offers WHERE id = ?", (int(offer_id),)).fetchone()
    conn.close()
    if not row:
        return f"Offer #{offer_id} not found."

    return json.dumps({
        "profile": profile,
        "offer": dict(row),
        "instruction": "Compare the profile against this offer. Identify matching skills, gaps, and give a fit score 0-100 with reasoning.",
    }, indent=2, ensure_ascii=False)


NOFLUFFJOBS_API = "https://nofluffjobs.com/api/posting"


def _parse_nofluffjobs_posting(p: dict) -> dict:
    salary = p.get("salary") or {}
    sal_from = salary.get("from")
    sal_to = salary.get("to")
    sal_type = salary.get("type", "")
    sal_currency = salary.get("currency", "PLN")
    salary_str = ""
    if sal_from and sal_to:
        salary_str = f"{int(sal_from)}-{int(sal_to)} {sal_currency} ({sal_type})"
    elif sal_from:
        salary_str = f"{int(sal_from)}+ {sal_currency} ({sal_type})"

    location = p.get("location") or {}
    places = location.get("places") or []
    cities = [pl.get("city", "") for pl in places if pl.get("city")]
    location_str = ", ".join(cities) if cities else ""

    fully_remote = p.get("fullyRemote", False)
    remote_str = "remote" if fully_remote else ""
    if not fully_remote and location.get("hybridDesc"):
        remote_str = "hybrid"

    seniority = p.get("seniority") or []
    title = p.get("title", "")
    if seniority and not any(title.startswith(s) for s in seniority):
        title = f"{'/'.join(seniority)} {title}"

    company = p.get("name", "")
    url_slug = p.get("url", "")
    url = f"https://nofluffjobs.com/pl/job/{url_slug}" if url_slug else ""

    tech = p.get("technology", "")
    tiles = p.get("tiles", {}).get("values", [])
    reqs = [t["value"] for t in tiles if t.get("type") == "requirement"]
    if tech and tech not in reqs:
        reqs.insert(0, tech)
    requirements = ", ".join(reqs) if reqs else tech

    return {
        "title": title,
        "company": company,
        "url": url,
        "salary": salary_str,
        "location": location_str,
        "remote": remote_str,
        "requirements": requirements,
        "source_id": p.get("id", ""),
    }


def _matches_filters(p: dict, keywords: str, seniority: str, category: str, location: str, salary_min: int) -> bool:
    if keywords:
        kw_lower = keywords.lower().split()
        searchable = f"{p.get('title','')} {p.get('name','')} {p.get('technology','')} {p.get('category','')}".lower()
        tiles = p.get("tiles", {}).get("values", [])
        searchable += " " + " ".join(t.get("value", "") for t in tiles).lower()
        if not all(k in searchable for k in kw_lower):
            return False
    if seniority:
        sen_list = [s.lower() for s in (p.get("seniority") or [])]
        if seniority.lower() not in sen_list:
            return False
    if category:
        if (p.get("category") or "").lower() != category.lower():
            return False
    if location:
        places = (p.get("location") or {}).get("places") or []
        cities = [pl.get("city", "").lower() for pl in places]
        if not any(location.lower() in c for c in cities):
            fully_remote = p.get("fullyRemote", False)
            if not fully_remote:
                return False
    if salary_min > 0:
        sal = p.get("salary") or {}
        sal_to = sal.get("to", 0) or 0
        if sal_to < salary_min:
            return False
    return True


async def career_fetch_jobs(
    keywords: str = "",
    seniority: str = "",
    category: str = "",
    location: str = "",
    salary_min: int = 0,
    limit: int = 20,
    save: bool = False,
    **kwargs,
) -> str:
    criteria_parts = []
    if keywords:
        criteria_parts.append(f"keyword={keywords.split()[0]}")
    if seniority:
        criteria_parts.append(f"seniority={seniority.lower()}")
    if category:
        criteria_parts.append(f"category={category.lower()}")

    params: dict = {}
    if criteria_parts:
        params["criteria"] = " ".join(criteria_parts)

    try:
        async with httpx.AsyncClient(timeout=60) as client:
            r = await client.get(NOFLUFFJOBS_API, params=params)
            r.raise_for_status()
            data = r.json()
    except httpx.HTTPStatusError as e:
        return f"nofluffjobs API error: HTTP {e.response.status_code}"
    except Exception as e:
        return f"Failed to fetch from nofluffjobs: {e}"

    all_postings = data.get("postings", [])
    filtered = [p for p in all_postings if _matches_filters(p, keywords, seniority, category, location, salary_min)]

    if not filtered:
        return f"No offers matched filters (checked {len(all_postings)} listings)."

    seen_keys: set[str] = set()
    parsed = []
    for p in filtered:
        o = _parse_nofluffjobs_posting(p)
        key = f"{o['company']}|{o['title']}"
        if key in seen_keys:
            continue
        seen_keys.add(key)
        parsed.append(o)
        if len(parsed) >= min(limit, 50):
            break

    conn = _db()
    existing_urls = {row[0] for row in conn.execute("SELECT url FROM offers WHERE url != ''").fetchall()}
    existing_titles = {(row[0], row[1]) for row in conn.execute("SELECT company, title FROM offers").fetchall()}

    saved_count = 0
    lines = [f"Found {len(filtered)} matching listings ({len(parsed)} unique, from {len(all_postings)} total):\n"]

    for i, o in enumerate(parsed, 1):
        dupe = o["url"] in existing_urls or (o["company"], o["title"]) in existing_titles
        marker = " [already saved]" if dupe else ""
        lines.append(f"{i}. {o['title']} @ {o['company']}{marker}")
        if o["salary"]:
            lines.append(f"   Salary: {o['salary']}")
        if o["location"]:
            loc = o["location"]
            if o["remote"]:
                loc += f" ({o['remote']})"
            lines.append(f"   Location: {loc}")
        if o["requirements"]:
            lines.append(f"   Tech: {o['requirements']}")
        lines.append(f"   URL: {o['url']}")

        if save and not dupe:
            now = datetime.now().isoformat()
            conn.execute(
                """INSERT INTO offers (title, company, url, requirements, salary, location, remote, date_added, date_updated)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (o["title"], o["company"], o["url"], o["requirements"],
                 o["salary"], o["location"], o["remote"], now, now),
            )
            saved_count += 1

    if save and saved_count:
        conn.commit()
        lines.append(f"\nSaved {saved_count} new offers to database ({len(parsed) - saved_count} duplicates skipped).")
    elif save:
        lines.append("\nAll offers already in database.")

    conn.close()
    return "\n".join(lines)
