#!/usr/bin/env python3
"""
new_source.py — Scaffold a new INDB source connector module.

Creates a working "hello world" source in services/sources/<name>/
with either static data or a URL-based HTTP feed.

Usage:
    python scripts/new_source.py
"""
import os
import re
import sys
import textwrap
from pathlib import Path

SOURCES_DIR = Path(__file__).parent.parent / "services" / "sources"
SCRIPTS_DIR = Path(__file__).parent


# ── Helpers ───────────────────────────────────────────────────────────────────

def slugify(s: str) -> str:
    """Convert any string to a snake_case module name."""
    s = s.lower().strip()
    s = re.sub(r"[^a-z0-9]+", "_", s)
    s = re.sub(r"_+", "_", s).strip("_")
    return s


def ask(prompt: str, default: str = "") -> str:
    hint = f" [{default}]" if default else ""
    val = input(f"{prompt}{hint}: ").strip()
    return val or default


def ask_choice(prompt: str, choices: list, default: str) -> str:
    opts = "/".join(f"[{c}]" if c == default else c for c in choices)
    while True:
        val = input(f"{prompt} ({opts}): ").strip().lower() or default
        if val in choices:
            return val
        print(f"  Please enter one of: {', '.join(choices)}")


# ── Template generators ────────────────────────────────────────────────────────

def make_config(name: str, class_name: str, feed_type: str, url: str) -> str:
    url_field = f'\n    url: str = "{url}"' if feed_type == "url" else ""
    url_env = f'\n            url=os.getenv("{name.upper()}_URL", "{url}"),' if feed_type == "url" else ""
    return textwrap.dedent(f'''\
        """
        {class_name} — configuration.

        All fields can be overridden via environment variables.
        """
        from __future__ import annotations

        import os
        from dataclasses import dataclass


        @dataclass
        class {class_name}Config:
            """Runtime configuration for the {class_name} source connector."""

            enabled: bool = True
            poll_interval: int = 60   # seconds between polls{url_field}

            @classmethod
            def from_env(cls) -> "{class_name}Config":
                return cls(
                    enabled=os.getenv("{name.upper()}_ENABLED", "true").lower() == "true",
                    poll_interval=int(os.getenv("{name.upper()}_POLL_INTERVAL", "60")),{url_env}
                )
        ''')


def make_transformer(name: str, class_name: str) -> str:
    return textwrap.dedent(f'''\
        """
        {class_name} transformer — converts raw items into INDB Events.

        Pure functions only: no I/O, no side effects.
        """
        from __future__ import annotations

        import logging
        import time
        from typing import Any, Dict, Optional

        from core.event import Event
        from core.source import Source

        logger = logging.getLogger("indb.sources.{name}")


        def item_to_event(item: Dict[str, Any], source: Source) -> Optional[Event]:
            """
            Transform a raw {class_name} item dict into an INDB Event.
            Returns None if the item has insufficient content.

            Adapt the field names here to match your data source.
            """
            # ── Extract content ───────────────────────────────────────────────
            # TODO: replace with actual field names from your source
            text = str(item.get("title") or item.get("text") or item.get("content") or "")
            if not text.strip():
                return None

            tokens = [f"{name}:" + w.lower() for w in text.split() if len(w) > 1][:200]
            if not tokens:
                return None

            # ── Location ──────────────────────────────────────────────────────
            # TODO: adapt to meaningful location from your source
            location = f"{name}://" + str(item.get("source", "local"))

            # ── Timestamp ─────────────────────────────────────────────────────
            # TODO: parse your source's timestamp field
            timestamp = float(item.get("timestamp", time.time()))

            event = Event(
                raw_data_anchor=tokens,
                location=location,
                source_id=source.id,
                temporal_metadata={{
                    "source": "{name}",
                    "raw_id": str(item.get("id", "")),
                }},
            )
            event.timestamp = timestamp
            return event
        ''')


def make_connector_static(name: str, class_name: str) -> str:
    return textwrap.dedent(f'''\
        """
        {class_name} connector — static data source (hello world).

        Replace STATIC_DATA with your real data or switch to the URL variant.
        """
        from __future__ import annotations

        import asyncio
        import logging
        from typing import Optional

        from core.source import Source, SourceType
        from services.sources.{name}.config import {class_name}Config
        from services.sources.{name}.transformer import item_to_event

        logger = logging.getLogger("indb.sources.{name}")

        # ── Static payload — replace or extend as needed ──────────────────────
        STATIC_DATA = [
            {{"id": "hello-1", "title": "Hello from {class_name}!", "source": "local", "timestamp": None}},
            {{"id": "hello-2", "title": "World event from {class_name}", "source": "local", "timestamp": None}},
        ]


        class {class_name}Connector:
            """
            Ingests static events into INDB on every poll cycle.
            Replace STATIC_DATA with real data or an API call.
            """

            def __init__(self, kernel, config: Optional[{class_name}Config] = None):
                self.kernel = kernel
                self.cfg = config or {class_name}Config.from_env()
                self._source = Source(
                    name="{name}",
                    type=SourceType.AGENT,
                    reputation=0.6,
                )
                self._running = False

            async def start(self) -> None:
                if not self.cfg.enabled:
                    logger.info("{class_name}Connector: disabled")
                    return
                self._running = True
                logger.info("{class_name}Connector: started (static mode, interval=%ds)", self.cfg.poll_interval)
                while self._running:
                    await self._poll()
                    await asyncio.sleep(self.cfg.poll_interval)

            async def stop(self) -> None:
                self._running = False
                logger.info("{class_name}Connector: stopped")

            async def _poll(self) -> None:
                import time
                ingested = 0
                for item in STATIC_DATA:
                    if item.get("timestamp") is None:
                        item["timestamp"] = time.time()
                    event = item_to_event(item, self._source)
                    if event is None:
                        continue
                    try:
                        await self.kernel.db.ingest(
                            raw_data_anchor=event.raw_data_anchor,
                            location=event.location,
                            source_id=self._source.id,
                            temporal_metadata=event.temporal_metadata,
                        )
                        ingested += 1
                    except Exception as e:
                        logger.warning("{class_name}Connector: ingest error: %s", e)
                if ingested:
                    logger.info("{class_name}Connector: ingested %d events", ingested)
        ''')


def make_connector_url(name: str, class_name: str, url: str) -> str:
    return textwrap.dedent(f'''\
        """
        {class_name} connector — HTTP/JSON feed source.

        Polls a URL, expects a JSON response with a list under a "data", "items",
        "results", or "posts" key (or the root list itself).
        """
        from __future__ import annotations

        import asyncio
        import logging
        from collections import deque
        from typing import Any, Dict, List, Optional

        import httpx

        from core.source import Source, SourceType
        from services.sources.{name}.config import {class_name}Config
        from services.sources.{name}.transformer import item_to_event

        logger = logging.getLogger("indb.sources.{name}")


        class {class_name}Connector:
            """
            Polls a JSON API endpoint and ingests items as INDB events.
            Adapt _extract_items() to match the response shape of your API.
            """

            def __init__(self, kernel, config: Optional[{class_name}Config] = None):
                self.kernel = kernel
                self.cfg = config or {class_name}Config.from_env()
                self._source = Source(
                    name="{name}",
                    type=SourceType.AGENT,
                    reputation=0.6,
                )
                self._seen: deque = deque(maxlen=5_000)
                self._running = False
                self._client: Optional[httpx.AsyncClient] = None

            async def start(self) -> None:
                if not self.cfg.enabled:
                    logger.info("{class_name}Connector: disabled")
                    return
                self._running = True
                self._client = httpx.AsyncClient(timeout=10.0)
                logger.info("{class_name}Connector: started (url=%s, interval=%ds)",
                            self.cfg.url, self.cfg.poll_interval)
                while self._running:
                    await self._poll()
                    await asyncio.sleep(self.cfg.poll_interval)

            async def stop(self) -> None:
                self._running = False
                if self._client:
                    await self._client.aclose()
                logger.info("{class_name}Connector: stopped")

            async def _poll(self) -> None:
                try:
                    resp = await self._client.get(self.cfg.url)
                    resp.raise_for_status()
                    raw = resp.json()
                    items = self._extract_items(raw)
                except Exception as e:
                    logger.warning("{class_name}Connector: fetch error: %s", e)
                    return

                ingested = 0
                for item in items:
                    item_id = str(item.get("id", ""))
                    if item_id and item_id in self._seen:
                        continue
                    event = item_to_event(item, self._source)
                    if event is None:
                        continue
                    try:
                        await self.kernel.db.ingest(
                            raw_data_anchor=event.raw_data_anchor,
                            location=event.location,
                            source_id=self._source.id,
                            temporal_metadata=event.temporal_metadata,
                        )
                        if item_id:
                            self._seen.append(item_id)
                        ingested += 1
                    except Exception as e:
                        logger.warning("{class_name}Connector: ingest error: %s", e)

                if ingested:
                    logger.info("{class_name}Connector: ingested %d new events", ingested)

            @staticmethod
            def _extract_items(raw: Any) -> List[Dict]:
                """
                Extract the item list from the API response.
                Handles common shapes: root list, or dict with data/items/results/posts key.
                TODO: adapt to your specific API response structure.
                """
                if isinstance(raw, list):
                    return raw
                if isinstance(raw, dict):
                    for key in ("data", "items", "results", "posts", "events"):
                        if isinstance(raw.get(key), list):
                            return raw[key]
                return []
        ''')


def make_init(name: str, class_name: str) -> str:
    return textwrap.dedent(f'''\
        """
        {class_name} source connector.

        SourceManager discovers this package automatically via MANIFEST.
        """
        from services.sources.{name}.connector import {class_name}Connector
        from services.sources.{name}.config import {class_name}Config

        __all__ = ["{class_name}Connector", "{class_name}Config", "MANIFEST"]

        MANIFEST = {{
            "name": "{name}",
            "connector_class": {class_name}Connector,
            "config_class": {class_name}Config,
        }}
        ''')


def make_env_snippet(name: str, url: str, feed_type: str) -> str:
    url_line = f"\n{name.upper()}_URL={url}" if feed_type == "url" else ""
    return (
        f"\n# ── {name.capitalize()} Source Connector ────────────────────────────────────────\n"
        f"{name.upper()}_ENABLED=true\n"
        f"{name.upper()}_POLL_INTERVAL=60{url_line}\n"
    )


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    print()
    print("=" * 60)
    print("  INDB — New Source Connector Generator")
    print("=" * 60)
    print()

    # 1. Name
    raw_name = ask("Source name (e.g. 'hacker news', 'local mqtt', 'rss feed')")
    if not raw_name:
        print("Name is required.")
        sys.exit(1)
    name = slugify(raw_name)
    class_name = "".join(w.capitalize() for w in name.split("_"))
    print(f"\n  → Module name : {name}")
    print(f"  → Class prefix: {class_name}")

    # 2. Feed type
    print()
    feed_type = ask_choice("Feed type", ["url", "static"], default="url")

    url = ""
    if feed_type == "url":
        url = ask("Feed URL", default="https://example.com/api/feed")

    # 3. Description (for README snippet)
    description = ask("Short description (optional)", default=f"{class_name} data source")

    # 4. Confirm
    pkg_dir = SOURCES_DIR / name
    print()
    print(f"  Will create: services/sources/{name}/")
    print(f"    __init__.py  (MANIFEST)")
    print(f"    config.py    ({class_name}Config)")
    print(f"    transformer.py")
    print(f"    connector.py  (feed_type={feed_type})")
    print()
    confirm = ask("Proceed? (y/n)", default="y").lower()
    if confirm != "y":
        print("Cancelled.")
        sys.exit(0)

    # 5. Create files
    pkg_dir.mkdir(parents=True, exist_ok=True)

    (pkg_dir / "__init__.py").write_text(make_init(name, class_name))
    (pkg_dir / "config.py").write_text(make_config(name, class_name, feed_type, url))
    (pkg_dir / "transformer.py").write_text(make_transformer(name, class_name))

    if feed_type == "url":
        (pkg_dir / "connector.py").write_text(make_connector_url(name, class_name, url))
    else:
        (pkg_dir / "connector.py").write_text(make_connector_static(name, class_name))

    # 6. Append .env.example snippet
    env_example = Path(__file__).parent.parent / ".env.example"
    if env_example.exists():
        existing = env_example.read_text()
        if f"{name.upper()}_ENABLED" not in existing:
            with env_example.open("a") as f:
                f.write(make_env_snippet(name, url, feed_type))
            print(f"\n  ✓ Added env vars to .env.example")

    # 7. Done
    print()
    print("=" * 60)
    print(f"  ✅  Source '{name}' created!")
    print("=" * 60)
    print()
    print("  Next steps:")
    print(f"  1. Edit services/sources/{name}/transformer.py")
    print(f"     → adapt item_to_event() to your data shape")
    if feed_type == "url":
        print(f"  2. Edit services/sources/{name}/connector.py")
        print(f"     → adapt _extract_items() if needed")
    else:
        print(f"  2. Edit services/sources/{name}/connector.py")
        print(f"     → replace STATIC_DATA or add fetch logic")
    print(f"  3. Set {name.upper()}_ENABLED=true in .env")
    if feed_type == "url":
        print(f"     Set {name.upper()}_URL=<your feed URL>")
    print(f"  4. Restart server — connector activates automatically (no registration needed)")
    print()
    print("  🔍 Verify:")
    print(f"     python scripts/new_source.py was idempotent — run again to see existing module")
    print(f"     GET /api/v2/events  → look for location starting with '{name}://'")
    print()


if __name__ == "__main__":
    main()
