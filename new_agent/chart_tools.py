from __future__ import annotations

import csv
import sqlite3
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path
from typing import Dict, Iterable, List

BASE_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = BASE_DIR / "public" / "data"
DB_FILE = DATA_DIR / "offstride.db"
LEADS_FILE = DATA_DIR / "leads.csv"
NOTIFICATIONS_FILE = DATA_DIR / "notifications.csv"

DOMAIN_KEYWORDS = {
    "hr": ["hr", "human resources", "talent", "recruitment", "payroll", "employee"],
    "legal": ["legal", "compliance", "contract", "policy", "litigation"],
    "finance": ["finance", "financial", "cfo", "tax", "audit", "account"],
    "it": ["it", "data", "ai", "cloud", "software", "infrastructure", "website"],
}


def _read_csv_rows(path: Path) -> List[Dict[str, str]]:
    if not path.exists():
        return []
    with path.open("r", newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        return [row for row in reader if row]


def _read_db_rows(query: str) -> List[Dict[str, str]]:
    if not DB_FILE.exists():
        return []
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    try:
        rows = conn.execute(query).fetchall()
        return [dict(row) for row in rows]
    finally:
        conn.close()


def _parse_timestamp(value: str) -> datetime | None:
    if not value:
        return None
    try:
        cleaned = value.replace("Z", "+00:00")
        return datetime.fromisoformat(cleaned)
    except Exception:
        return None


def infer_domain(text: str) -> str:
    value = (text or "").lower()
    for domain, keywords in DOMAIN_KEYWORDS.items():
        if any(keyword in value for keyword in keywords):
            return domain
    return "unknown"


def leads_over_time(rows: Iterable[Dict[str, str]]) -> List[Dict[str, object]]:
    counts: Dict[str, int] = defaultdict(int)
    for row in rows:
        timestamp = _parse_timestamp(row.get("timestamp", ""))
        if not timestamp:
            continue
        day = timestamp.date().isoformat()
        counts[day] += 1
    return [
        {"date": day, "count": counts[day]}
        for day in sorted(counts.keys())
    ]


def leads_by_domain(rows: Iterable[Dict[str, str]]) -> Dict[str, int]:
    counts: Counter[str] = Counter()
    for row in rows:
        domain = infer_domain(row.get("task_summary", ""))
        counts[domain] += 1
    return dict(counts)


def top_locations(rows: Iterable[Dict[str, str]], limit: int = 5) -> List[Dict[str, object]]:
    counts: Counter[str] = Counter()
    for row in rows:
        location = (row.get("location") or "").strip().title()
        if location:
            counts[location] += 1
    return [
        {"location": location, "count": count}
        for location, count in counts.most_common(limit)
    ]


def match_rate(leads: List[Dict[str, str]], notifications: List[Dict[str, str]]) -> float:
    if not leads:
        return 0.0
    return round((len(notifications) / len(leads)) * 100.0, 2)


def overview() -> Dict[str, object]:
    leads = _read_db_rows("SELECT * FROM leads") or _read_csv_rows(LEADS_FILE)
    notifications = _read_db_rows("SELECT * FROM notifications") or _read_csv_rows(NOTIFICATIONS_FILE)

    return {
        "totalLeads": len(leads),
        "totalMatches": len(notifications),
        "matchRate": match_rate(leads, notifications),
        "leadsOverTime": leads_over_time(leads),
        "leadsByDomain": leads_by_domain(leads),
        "topLocations": top_locations(leads),
    }


def tool_catalog() -> Dict[str, str]:
    return {
        "get_overview": "Get overall metrics and time series from leads and notifications data.",
        "get_leads_over_time": "Return daily lead counts based on timestamps.",
        "get_leads_by_domain": "Return counts by inferred domain from task summaries.",
        "get_top_locations": "Return top locations by lead count.",
    }
