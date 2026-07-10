"""
Moltbook → INDB Event Transformer

Pure functions: no I/O, no side effects. Easy to test in isolation.
"""
from __future__ import annotations

import logging
import re
import time
from typing import Any, Dict, Optional

from core.event import Event
from core.source import Source, SourceType
from services.sources.moltbook.config import MoltbookConfig
from core.constants import MOLTBOOK_MAX_TOKENS

logger = logging.getLogger("indb.sources.moltbook")


def reputation_from_upvotes(upvotes: int, config: MoltbookConfig) -> float:
    """
    Map upvote count to a [0, 1] reputation score.
    0 upvotes    → base_reputation (default 0.3)
    upvote_scale → 1.0
    Linear interpolation, clamped.
    """
    if upvotes <= 0:
        return config.base_reputation
    ratio = upvotes / config.upvote_scale
    return min(1.0, config.base_reputation + (1.0 - config.base_reputation) * ratio)


def tokenise(text: str) -> list[str]:
    """
    Split text into lowercase word tokens, stripping punctuation.
    Keeps tokens ≥ 2 chars and ignores pure-numeric tokens.
    Stops at 200 tokens to keep Event size reasonable.
    """
    words = re.findall(r"[a-zA-Z][a-zA-Z0-9'-]{1,}", text.lower())
    return words[:MOLTBOOK_MAX_TOKENS]


def parse_moltbook_timestamp(iso_str: str) -> float:
    """
    Convert Moltbook ISO 8601 string → Unix float.
    Falls back to time.time() on parse error.
    """
    try:
        from datetime import datetime, timezone
        # Handle both Z-suffix and +00:00
        clean = iso_str.replace("Z", "+00:00")
        dt = datetime.fromisoformat(clean)
        return dt.timestamp()
    except Exception:
        logger.warning("Failed to parse Moltbook timestamp: %r — using now()", iso_str)
        return time.time()


def post_to_event(post: Dict[str, Any], source: Source) -> Optional[Event]:
    """
    Transform a Moltbook API post/comment dict into an INDB Event.

    Returns None if the post has insufficient content to ingest.
    """
    try:
        # ── Content ────────────────────────────────────────────────────────
        title = post.get("title") or ""
        content = post.get("content") or ""
        full_text = f"{title} {content}".strip()

        if not full_text:
            return None

        tokens = tokenise(full_text)
        if len(tokens) < 2:
            return None

        # Prefix tokens to make them searchable as structured fields
        raw_anchor = [f"moltbook:{t}" for t in tokens]

        # Add structured metadata tokens
        author_name = (post.get("author") or {}).get("name", "unknown")
        submolt_name = (post.get("submolt") or {}).get("name", "")
        content_type = post.get("type", "post")  # "post" or "comment"

        raw_anchor.append(f"author:{author_name}")
        raw_anchor.append(f"type:{content_type}")
        if submolt_name:
            raw_anchor.append(f"submolt:{submolt_name}")
        if title:
            raw_anchor.append(f"title:{title[:80]}")

        # ── Location ───────────────────────────────────────────────────────
        # Format: moltbook://{submolt}/{author}
        if submolt_name:
            location = f"moltbook://{submolt_name}/{author_name}"
        else:
            location = f"moltbook://global/{author_name}"

        # ── Timestamp ──────────────────────────────────────────────────────
        created_at = post.get("created_at", "")
        timestamp = parse_moltbook_timestamp(created_at) if created_at else time.time()

        # ── Temporal metadata ──────────────────────────────────────────────
        upvotes = int(post.get("upvotes", 0) or 0)
        similarity = float(post.get("similarity", 0.0) or 0.0)

        temporal_metadata = {
            "source": "moltbook",
            "content_type": content_type,
            "author": author_name,
            "submolt": submolt_name,
            "upvotes": upvotes,
            "downvotes": int(post.get("downvotes", 0) or 0),
            "post_id": post.get("id", ""),
            "similarity_score": similarity,
        }

        # ── Build Event ────────────────────────────────────────────────────
        event = Event(
            raw_data_anchor=raw_anchor,
            location=location,
            source_id=source.id,
            temporal_metadata=temporal_metadata,
        )
        # Override the auto-generated timestamp with Moltbook's
        event.timestamp = timestamp

        return event

    except Exception as e:
        logger.warning("Failed to transform Moltbook post %r: %s", post.get("id", "?"), e)
        return None
