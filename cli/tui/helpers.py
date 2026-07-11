"""Formatting helpers for TUI display."""

from __future__ import annotations

import json
from datetime import datetime
from typing import Any, Dict, Iterable, List, Optional


def format_timestamp(ts: float) -> str:
    try:
        return datetime.fromtimestamp(float(ts)).strftime("%H:%M:%S")
    except (TypeError, ValueError, OSError):
        return "—"


def event_content(event: Dict[str, Any]) -> str:
    tokens = event.get("raw_data_anchor") or []
    if not tokens:
        return "—"
    text = str(tokens[0])
    for prefix in ("event:", "quote:"):
        if text.startswith(prefix):
            return text[len(prefix) :].strip() or text
    return text


def event_id_short(event: Dict[str, Any]) -> str:
    eid = str(event.get("id", ""))
    prefix = "⚡" if (event.get("fusion_count") or 0) > 0 or event.get("is_fused") else ""
    return f"{prefix}{eid[:8]}" if eid else "—"


def truncate(text: str, max_len: int) -> str:
    if len(text) <= max_len:
        return text
    return text[: max_len - 1] + "…"


def location_label(location: str, max_len: int = 24) -> str:
    """Short display name for event.location (strips common namespace prefixes)."""
    loc = str(location or "—")
    for prefix in ("books/", "vault/", "hermes://", "wikipedia/", "arxiv/"):
        if loc.startswith(prefix):
            loc = loc[len(prefix) :]
            break
    return truncate(loc, max_len)


def module_status_icon(status: str) -> str:
    icons = {
        "running": "🟢",
        "no_api_key": "🟡",
        "disabled": "⚪",
        "error": "🔴",
    }
    return icons.get(status, "⚪")


def node_status_label(ok: bool, error: bool = False) -> str:
    if error:
        return "⚠️ ERROR"
    return "✅ UP" if ok else "❌ DOWN"


def raft_role_label(state: str, is_leader: bool) -> str:
    if is_leader or state.lower() == "leader":
        return "👑 LEADER"
    if state.lower() == "disabled":
        return "—"
    return "Follower"


def matches_filter(event: Dict[str, Any], query: str) -> bool:
    if not query:
        return True
    q = query.lower()
    parts: List[str] = [
        str(event.get("id", "")),
        str(event.get("location", "")),
        format_timestamp(event.get("timestamp", 0)),
    ]
    for token in event.get("raw_data_anchor") or []:
        parts.append(str(token))
    blob = " ".join(parts).lower()
    return q in blob


def pretty_json(data: Any, limit: int = 8000) -> str:
    try:
        text = json.dumps(data, indent=2, ensure_ascii=False, default=str)
    except TypeError:
        text = str(data)
    if len(text) > limit:
        return text[:limit] + "\n… (truncated)"
    return text


def top_items(counter: Dict[str, Any], limit: int = 8) -> Iterable[str]:
    items = sorted(counter.items(), key=lambda x: x[1], reverse=True)[:limit]
    for key, count in items:
        yield f"  {key}: {count}"
