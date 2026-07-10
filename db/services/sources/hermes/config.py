"""
Hermes Integration — configuration.

All fields can be overridden via environment variables.
"""
from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass
class HermesConfig:
    """
    Runtime configuration for the Hermes source connector.

    Polls Hermes session/memory files and ingests agent activity into INDB.
    When running in Docker, mount host ~/.hermes to /hermes and set HERMES_SESSIONS_PATH.
    """

    # ── Paths ─────────────────────────────────────────────────────────────────
    # Directory to poll for Hermes session files (JSON).
    # In Docker: mount ~/.hermes:/hermes, set HERMES_SESSIONS_PATH=/hermes/sessions
    # On host: default ~/.hermes/sessions
    sessions_path: str = ""

    # Optional: also poll memories (MEMORY.md, USER.md) for changes
    memories_path: str = ""

    # ── Polling ─────────────────────────────────────────────────────────────
    poll_interval: int = 60  # seconds between polls

    # Rolling seen-ID window to prevent re-ingestion
    dedupe_window: int = 5_000

    # ── Toggle ───────────────────────────────────────────────────────────────
    enabled: bool = True

    # Hermes connector does not require API key (local files)
    # We use a dummy field for SourceManager compatibility — always truthy
    api_key: str = "local"

    @classmethod
    def from_env(cls) -> "HermesConfig":
        """Load configuration from environment variables."""
        default_sessions = os.path.expanduser("~/.hermes/sessions")
        default_memories = os.path.expanduser("~/.hermes/memories")

        return cls(
            sessions_path=os.getenv("HERMES_SESSIONS_PATH", default_sessions),
            memories_path=os.getenv("HERMES_MEMORIES_PATH", default_memories),
            poll_interval=int(os.getenv("HERMES_POLL_INTERVAL", "60")),
            dedupe_window=int(os.getenv("HERMES_DEDUPE_WINDOW", "5000")),
            enabled=os.getenv("HERMES_ENABLED", "true").lower() == "true",
        )
