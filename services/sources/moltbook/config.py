"""
Moltbook Connector Configuration
"""
from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from typing import List


@dataclass
class MoltbookConfig:
    """
    Runtime configuration for the Moltbook source connector.
    All values can be overridden via environment variables; the
    `from_env()` factory reads them automatically.
    """

    # ── Auth ────────────────────────────────────────────────────────────────
    api_key: str = ""

    # ── Polling ─────────────────────────────────────────────────────────────
    # Minimum safe interval: Moltbook allows 60 GET req / 60 s.
    # Default = 120 s → consumes ~0.5 req/s budget, leaving room for search.
    poll_interval: int = 120

    # Which submolts to pull from. Empty list = global "new" feed.
    submolts: List[str] = field(default_factory=lambda: ["general"])

    # Semantic search queries run on every poll cycle (in addition to feed).
    # Useful for topic-specific ingestion ("agents discussing memory", etc.)
    search_queries: List[str] = field(default_factory=list)

    # ── Volume ───────────────────────────────────────────────────────────────
    max_posts_per_poll: int = 25

    # Rolling seen-ID window to prevent re-ingestion.
    dedupe_window: int = 10_000

    # ── Toggle ───────────────────────────────────────────────────────────────
    enabled: bool = True

    # ── Reputation tuning ────────────────────────────────────────────────────
    # upvotes needed to reach reputation = 1.0
    upvote_scale: int = 50

    # Base reputation for posts with 0 upvotes
    base_reputation: float = 0.3

    @classmethod
    def from_env(cls) -> "MoltbookConfig":
        """Load configuration from environment variables."""
        submolts_raw = os.getenv("MOLTBOOK_SUBMOLTS", "general")
        submolts = [s.strip() for s in submolts_raw.split(",") if s.strip()]

        search_raw = os.getenv("MOLTBOOK_SEARCH_QUERIES", "[]")
        try:
            search_queries = json.loads(search_raw)
        except json.JSONDecodeError:
            search_queries = []

        return cls(
            api_key=os.getenv("MOLTBOOK_API_KEY", ""),
            poll_interval=int(os.getenv("MOLTBOOK_POLL_INTERVAL", "120")),
            submolts=submolts,
            search_queries=search_queries,
            max_posts_per_poll=int(os.getenv("MOLTBOOK_MAX_POSTS", "25")),
            dedupe_window=int(os.getenv("MOLTBOOK_DEDUPE_WINDOW", "10000")),
            enabled=os.getenv("MOLTBOOK_ENABLED", "true").lower() == "true",
            upvote_scale=int(os.getenv("MOLTBOOK_UPVOTE_SCALE", "50")),
            base_reputation=float(os.getenv("MOLTBOOK_BASE_REPUTATION", "0.3")),
        )
