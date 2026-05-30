from datetime import date, datetime
from typing import Optional


def clean(value) -> Optional[str]:
    if value is None:
        return None
    s = str(value).strip()
    return s if s and s.lower() not in ("none", "n/a", "-", "", "null") else None


def parse_date(value) -> Optional[date]:
    if not value:
        return None
    s = str(value).strip()
    for fmt in (
        "%Y-%m-%d", "%d/%m/%Y", "%m/%d/%Y", "%d-%m-%Y",
        "%d %B %Y", "%B %d, %Y", "%d-%b-%Y", "%Y/%m/%d",
        "%Y %B %d", "%Y %b %d", "%d %b %Y", "%B %Y",
    ):
        try:
            return datetime.strptime(s, fmt).date()
        except ValueError:
            continue
    return None


def normalize_status(value: Optional[str]) -> str:
    if not value:
        return "unknown"
    v = value.lower().strip()
    if any(x in v for x in ("active", "valid", "registered", "approved", "current")):
        return "active"
    if any(x in v for x in ("expired", "lapsed", "expir")):
        return "expired"
    if any(x in v for x in ("suspend", "revok", "cancel", "withdrawn", "recall")):
        return "suspended"
    if any(x in v for x in ("pending", "under review", "submitted", "in progress")):
        return "pending"
    return "unknown"


def parse_dosage_forms(value: Optional[str]) -> list[str]:
    if not value:
        return []
    return [f.strip() for f in str(value).split("/") if f.strip()]
