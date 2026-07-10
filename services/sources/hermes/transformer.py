"""
Hermes → INDB Event Transformer

Pure functions: no I/O, no side effects. Transforms Hermes session/memory
content into INDB Events.
"""
from __future__ import annotations

import logging
import re
import time
from typing import Any, Dict, List, Optional

from core.event import Event
from core.source import Source

logger = logging.getLogger("indb.sources.hermes")

HERMES_MAX_TOKENS = 200


def tokenise(text: str) -> List[str]:
    """
    Split text into lowercase word tokens. Keeps tokens ≥ 2 chars.
    Stops at HERMES_MAX_TOKENS.
    """
    words = re.findall(r"[a-zA-Z][a-zA-Z0-9'-]{1,}", text.lower())
    return words[:HERMES_MAX_TOKENS]


def extract_content_from_session(data: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Extract message-like items from Hermes session JSON.
    Handles common structures: messages, turns, history, content.
    Returns list of {"text": str, "role": str, "timestamp": float} dicts.
    """
    items: List[Dict[str, Any]] = []

    # messages: [{"role": "user", "content": "..."}, ...]
    messages = data.get("messages") or data.get("turns") or data.get("history") or []
    if isinstance(messages, list):
        for m in messages:
            if isinstance(m, dict):
                content = m.get("content") or m.get("text") or m.get("body") or ""
                if isinstance(content, list):
                    content = " ".join(
                        c.get("text", str(c)) for c in content if isinstance(c, dict)
                    )
                role = m.get("role", m.get("sender", "unknown"))
                ts = m.get("timestamp") or m.get("created_at") or time.time()
                if content and str(content).strip():
                    items.append({"text": str(content).strip(), "role": role, "timestamp": ts})
            elif isinstance(m, str) and m.strip():
                items.append({"text": m.strip(), "role": "unknown", "timestamp": time.time()})

    # Single content field
    if not items:
        content = data.get("content") or data.get("text") or data.get("summary") or ""
        if content and str(content).strip():
            items.append({
                "text": str(content).strip(),
                "role": data.get("role", "hermes"),
                "timestamp": data.get("timestamp") or time.time(),
            })

    return items


def item_to_event(
    item: Dict[str, Any],
    source: Source,
    session_id: str = "",
    file_path: str = "",
) -> Optional[Event]:
    """
    Transform a Hermes message/item dict into an INDB Event.
    Returns None if insufficient content.
    """
    text = item.get("text", "")
    if not text or len(text.strip()) < 3:
        return None

    tokens = tokenise(text)
    if len(tokens) < 2:
        return None

    raw_anchor = [f"hermes:{t}" for t in tokens]
    role = item.get("role", "unknown")
    raw_anchor.append(f"role:{role}")
    if session_id:
        raw_anchor.append(f"session:{session_id}")

    location = f"hermes://{role}"
    if session_id:
        location = f"hermes://{role}/{session_id[:8]}"

    ts = item.get("timestamp", time.time())
    if isinstance(ts, str):
        try:
            ts = float(ts)
        except (ValueError, TypeError):
            ts = time.time()

    temporal_metadata: Dict[str, Any] = {
        "source": "hermes",
        "role": role,
        "session_id": session_id,
        "file_path": file_path,
    }

    event = Event(
        raw_data_anchor=raw_anchor,
        location=location,
        source_id=source.id,
        temporal_metadata=temporal_metadata,
    )
    event.timestamp = ts
    return event


def memory_md_to_events(
    content: str,
    source: Source,
    file_name: str = "MEMORY.md",
) -> List[Event]:
    """
    Parse Hermes MEMORY.md or USER.md (section-delimited with §).
    Returns list of Events, one per section.
    """
    events: List[Event] = []
    sections = [s.strip() for s in content.split("§") if s.strip()]
    for i, section in enumerate(sections):
        if len(section) < 10:
            continue
        tokens = tokenise(section)
        if len(tokens) < 2:
            continue
        raw_anchor = [f"hermes:{t}" for t in tokens]
        raw_anchor.append(f"memory:{file_name}")
        event = Event(
            raw_data_anchor=raw_anchor,
            location=f"hermes://memory/{file_name}",
            source_id=source.id,
            temporal_metadata={"source": "hermes", "memory_file": file_name, "section": i},
        )
        events.append(event)
    return events
