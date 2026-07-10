"""
Moltbook Source Connector

Async pull-based ingestion adapter.
Polls the Moltbook public feed and optionally runs semantic search queries,
converting posts into INDB Events via MoltbookTransformer.

Usage (automatic via app_factory.py if MOLTBOOK_API_KEY is set):

    from services.sources.moltbook.connector import MoltbookConnector
    from services.sources.moltbook.config import MoltbookConfig

    cfg = MoltbookConfig.from_env()
    connector = MoltbookConnector(kernel=kernel, config=cfg)
    asyncio.create_task(connector.start())
"""
from __future__ import annotations

import asyncio
import logging
from collections import deque
from typing import Any, Dict, List, Optional

import httpx

from core.source import Source, SourceType
from services.sources.moltbook.config import MoltbookConfig
from services.sources.moltbook.transformer import post_to_event, reputation_from_upvotes

logger = logging.getLogger("indb.sources.moltbook")

BASE_URL = "https://www.moltbook.com/api/v1"


class MoltbookConnector:
    """
    Async connector that ingests Moltbook posts into INDB.

    Two ingestion paths per poll cycle:
        1. Feed poll  — GET /posts?sort=new (per submolt or global)
        2. Search     — GET /search?q=... for each configured search_query
    """

    def __init__(self, kernel, config: Optional[MoltbookConfig] = None):
        self.kernel = kernel
        self.cfg = config or MoltbookConfig.from_env()

        # Rolling dedup set (deque keeps memory bounded)
        self._seen_ids: deque = deque(maxlen=self.cfg.dedupe_window)

        # Stable Source identity for all events from this connector
        self._source = Source(
            name="moltbook",
            type=SourceType.AGENT,
            reputation=0.5,
            meta={"url": BASE_URL},
        )

        self._running = False
        self._client: Optional[httpx.AsyncClient] = None

        if not self.cfg.api_key:
            logger.warning(
                "MoltbookConnector: no API key set — connector is disabled. "
                "Register INDB as an agent and set MOLTBOOK_API_KEY."
            )

    # ── Lifecycle ─────────────────────────────────────────────────────────────

    async def start(self) -> None:
        if not self.cfg.enabled or not self.cfg.api_key:
            logger.info("MoltbookConnector: disabled (enabled=%s, api_key=%s)",
                        self.cfg.enabled, bool(self.cfg.api_key))
            return

        self._running = True
        self._client = httpx.AsyncClient(
            base_url=BASE_URL,
            headers={"Authorization": f"Bearer {self.cfg.api_key}"},
            timeout=10.0,
        )

        logger.info(
            "MoltbookConnector: started (poll_interval=%ds, submolts=%s, search_queries=%d)",
            self.cfg.poll_interval, self.cfg.submolts, len(self.cfg.search_queries),
        )

        while self._running:
            try:
                await self._poll_cycle()
            except Exception as e:
                logger.error("MoltbookConnector poll error: %s", e, exc_info=True)

            await asyncio.sleep(self.cfg.poll_interval)

    async def stop(self) -> None:
        self._running = False
        if self._client:
            await self._client.aclose()
        logger.info("MoltbookConnector: stopped")

    # ── Poll Cycle ────────────────────────────────────────────────────────────

    async def _poll_cycle(self) -> None:
        ingested_total = 0

        # 1. Feed per submolt (or global if submolts=[])
        if self.cfg.submolts:
            for submolt in self.cfg.submolts:
                posts = await self._fetch_feed(submolt=submolt)
                ingested_total += await self._ingest_posts(posts)
        else:
            posts = await self._fetch_feed(submolt=None)
            ingested_total += await self._ingest_posts(posts)

        # 2. Semantic search queries
        for query in self.cfg.search_queries:
            posts = await self._fetch_search(query)
            ingested_total += await self._ingest_posts(posts)

        if ingested_total:
            logger.info("MoltbookConnector: ingested %d new events", ingested_total)

    # ── Fetch ─────────────────────────────────────────────────────────────────

    async def _fetch_feed(self, submolt: Optional[str]) -> List[Dict[str, Any]]:
        """Fetch latest posts from feed (global or per-submolt)."""
        params = {"sort": "new", "limit": self.cfg.max_posts_per_poll}
        if submolt:
            params["submolt"] = submolt

        try:
            resp = await self._client.get("/posts", params=params)
            resp.raise_for_status()
            data = resp.json()
            return data.get("posts", data.get("data", []))
        except httpx.HTTPStatusError as e:
            logger.warning(
                "MoltbookConnector: feed request failed (submolt=%s) HTTP %d",
                submolt, e.response.status_code,
            )
            return []
        except Exception as e:
            logger.warning("MoltbookConnector: feed request error: %s", e)
            return []

    async def _fetch_search(self, query: str) -> List[Dict[str, Any]]:
        """Semantic search: find posts matching a natural language query."""
        params = {"q": query, "type": "posts", "limit": self.cfg.max_posts_per_poll}
        try:
            resp = await self._client.get("/search", params=params)
            resp.raise_for_status()
            data = resp.json()
            return data.get("results", [])
        except httpx.HTTPStatusError as e:
            logger.warning(
                "MoltbookConnector: search failed (q=%r) HTTP %d",
                query[:40], e.response.status_code,
            )
            return []
        except Exception as e:
            logger.warning("MoltbookConnector: search error (q=%r): %s", query[:40], e)
            return []

    # ── Ingest ────────────────────────────────────────────────────────────────

    async def _ingest_posts(self, posts: List[Dict[str, Any]]) -> int:
        """Transform and ingest a list of Moltbook posts. Returns count ingested."""
        ingested = 0
        for post in posts:
            post_id = post.get("id")
            if not post_id or post_id in self._seen_ids:
                continue

            # Build a per-post Source with upvote-weighted reputation
            upvotes = int(post.get("upvotes", 0) or 0)
            rep = reputation_from_upvotes(upvotes, self.cfg)
            author = (post.get("author") or {}).get("name", "unknown")
            source = Source(
                name=f"moltbook::{author}",
                type=SourceType.AGENT,
                reputation=rep,
                meta={"post_id": post_id, "upvotes": upvotes},
            )

            event = post_to_event(post, source)
            if event is None:
                continue

            try:
                await self.kernel.db.ingest(
                    raw_data_anchor=event.raw_data_anchor,
                    location=event.location,
                    source_id=source.id,
                    temporal_metadata=event.temporal_metadata,
                )
                self._seen_ids.append(post_id)
                ingested += 1
            except Exception as e:
                logger.warning(
                    "MoltbookConnector: failed to ingest post %s: %s", post_id, e
                )

        return ingested
