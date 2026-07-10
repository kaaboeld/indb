"""
Hermes Source Connector — ingests Hermes agent activity into INDB.

Polls Hermes session files (~/.hermes/sessions/) and optionally memory files
(MEMORY.md, USER.md). Transforms agent conversations and memory into INDB Events.

Usage (automatic via SourceManager when HERMES_ENABLED=true):

    Mount host ~/.hermes in Docker:
      volumes:
        - ~/.hermes:/hermes:ro
    Set HERMES_SESSIONS_PATH=/hermes/sessions

    Or run INDB on host — default path ~/.hermes/sessions is used.
"""
from __future__ import annotations

import asyncio
import json
import logging
from collections import deque
from pathlib import Path
from typing import Any, Dict, List, Optional

from core.source import Source, SourceType
from services.sources.hermes.config import HermesConfig
from services.sources.hermes.transformer import (
    extract_content_from_session,
    item_to_event,
    memory_md_to_events,
)

logger = logging.getLogger("indb.sources.hermes")


class HermesConnector:
    """
    Polls Hermes session and memory files, ingests agent activity as INDB events.
    """

    def __init__(self, kernel, config: Optional[HermesConfig] = None):
        self.kernel = kernel
        self.cfg = config or HermesConfig.from_env()

        self._seen: deque = deque(maxlen=self.cfg.dedupe_window)
        self._running = False

        self._source = Source(
            name="hermes",
            type=SourceType.AGENT,
            reputation=0.7,
            meta={"sessions_path": self.cfg.sessions_path},
        )

    async def start(self) -> None:
        if not self.cfg.enabled:
            logger.info("HermesConnector: disabled")
            return

        self._running = True
        logger.info(
            "HermesConnector: started (sessions=%s, interval=%ds)",
            self.cfg.sessions_path,
            self.cfg.poll_interval,
        )

        while self._running:
            try:
                await self._poll_cycle()
            except Exception as e:
                logger.error("HermesConnector poll error: %s", e, exc_info=True)
            await asyncio.sleep(self.cfg.poll_interval)

    async def stop(self) -> None:
        self._running = False
        logger.info("HermesConnector: stopped")

    async def _poll_cycle(self) -> None:
        ingested = 0

        # 1. Poll session files
        sessions_path = Path(self.cfg.sessions_path)
        if sessions_path.exists() and sessions_path.is_dir():
            ingested += await self._ingest_sessions(sessions_path)

        # 2. Poll memory files (optional)
        memories_path = Path(self.cfg.memories_path)
        if memories_path.exists() and memories_path.is_dir():
            ingested += await self._ingest_memories(memories_path)

        if ingested:
            logger.info("HermesConnector: ingested %d new events", ingested)

    async def _ingest_sessions(self, base: Path) -> int:
        """Traverse session directory, parse JSON files, ingest messages."""
        ingested = 0
        for path in base.rglob("*.json"):
            try:
                data = json.loads(path.read_text(encoding="utf-8", errors="replace"))
            except (json.JSONDecodeError, OSError) as e:
                logger.debug("HermesConnector: skip %s: %s", path.name, e)
                continue

            session_id = path.stem
            items = extract_content_from_session(data)

            for item in items:
                dedupe_key = f"{path}:{item.get('text', '')[:80]}"
                if dedupe_key in self._seen:
                    continue

                event = item_to_event(
                    item,
                    self._source,
                    session_id=session_id,
                    file_path=str(path),
                )
                if event is None:
                    continue

                try:
                    await self.kernel.db.ingest(
                        raw_data_anchor=event.raw_data_anchor,
                        location=event.location,
                        source_id=self._source.id,
                        temporal_metadata=event.temporal_metadata,
                    )
                    self._seen.append(dedupe_key)
                    ingested += 1
                except Exception as e:
                    logger.warning("HermesConnector: ingest error for %s: %s", path.name, e)

        return ingested

    async def _ingest_memories(self, base: Path) -> int:
        """Read MEMORY.md and USER.md, parse §-delimited sections, ingest."""
        ingested = 0
        for name in ("MEMORY.md", "USER.md"):
            path = base / name
            if not path.exists():
                continue
            try:
                content = path.read_text(encoding="utf-8", errors="replace")
            except OSError as e:
                logger.debug("HermesConnector: skip %s: %s", name, e)
                continue

            events = memory_md_to_events(content, self._source, file_name=name)
            for event in events:
                dedupe_key = f"mem:{name}:{event.raw_data_anchor[0] if event.raw_data_anchor else ''}"
                if dedupe_key in self._seen:
                    continue
                try:
                    await self.kernel.db.ingest(
                        raw_data_anchor=event.raw_data_anchor,
                        location=event.location,
                        source_id=self._source.id,
                        temporal_metadata=event.temporal_metadata,
                    )
                    self._seen.append(dedupe_key)
                    ingested += 1
                except Exception as e:
                    logger.warning("HermesConnector: memory ingest error: %s", e)

        return ingested
