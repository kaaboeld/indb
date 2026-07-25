"""Helpers for temporal analytics derived from event timestamps."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict


def season_from_month(month: int) -> str:
    if month in (6, 7, 8):
        return "summer"
    if month in (9, 10, 11):
        return "fall"
    if month in (12, 1, 2):
        return "winter"
    return "spring"


def temporal_fields_from_event(event: Any) -> Dict[str, int | str]:
    """Return month/day_of_week/season/hour, falling back to timestamp."""
    meta = getattr(event, "temporal_metadata", None) or {}
    dt = datetime.fromtimestamp(getattr(event, "timestamp", 0) or 0)
    month = int(meta.get("month", dt.month))
    return {
        "month": month,
        "day_of_week": int(meta.get("day_of_week", dt.weekday())),
        "season": str(meta.get("season", season_from_month(month))),
        "hour": int(meta.get("hour", dt.hour)),
    }
