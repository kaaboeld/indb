"""TUI configuration loaded from environment."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional, Tuple
from urllib.parse import urlparse

import httpx

DEFAULT_VERSION = "0.7.0"
PRODUCTION_API_URL = "https://api.indb.tech"

# Load .env from project root when available.
try:
    from dotenv import load_dotenv

    _root = Path(__file__).resolve().parents[2]
    load_dotenv(_root / ".env")
except ImportError:
    pass


def _port_label(url: str) -> str:
    parsed = urlparse(url)
    if parsed.port:
        return str(parsed.port)
    if parsed.scheme == "https":
        return "443"
    return "80"


def cluster_nodes(api_url: str) -> List[Tuple[str, str, str]]:
    """Return cluster endpoints to poll — from env or the configured API."""
    custom = os.getenv("INDB_CLUSTER_NODES", "").strip()
    if custom:
        urls = [u.strip().rstrip("/") for u in custom.split(",") if u.strip()]
        return [(f"node-{i + 1}", url, _port_label(url)) for i, url in enumerate(urls)]

    url = api_url.rstrip("/")
    parsed = urlparse(url)
    host = parsed.hostname or ""
    label = host or "api"
    return [(label, url, _port_label(url))]


def _probe_url(url: str, timeout: float = 2.0) -> bool:
    try:
        response = httpx.get(f"{url.rstrip('/')}/health", timeout=timeout, follow_redirects=True)
        if response.status_code != 200:
            return False
        payload = response.json()
        return payload.get("status") == "ok"
    except Exception:
        return False


def resolve_api_url(explicit: Optional[str] = None) -> Tuple[str, Optional[str]]:
    """
    Resolve the API endpoint.

    Priority: CLI arg → INDB_API_URL → production default.
    No localhost auto-discovery — production DB is the default target.
    """
    if explicit and explicit.strip():
        url = explicit.strip().rstrip("/")
    else:
        env_url = os.getenv("INDB_API_URL", "").strip()
        url = env_url.rstrip("/") if env_url else PRODUCTION_API_URL

    if _probe_url(url):
        if url.rstrip("/") == PRODUCTION_API_URL:
            return url, f"Connected to production: {url}"
        return url, None

    return url, (
        f"API unreachable: {url}. "
        f"Set INDB_API_URL or start the local cluster."
    )


@dataclass
class TuiConfig:
    api_url: str = PRODUCTION_API_URL
    connection_note: Optional[str] = None
    in_docker: bool = field(
        default_factory=lambda: os.getenv("INDB_IN_DOCKER", "false").lower() in ("1", "true", "yes")
    )
    version: str = field(
        default_factory=lambda: os.getenv("INDB_VERSION", DEFAULT_VERSION)
    )
    project_root: Path = field(
        default_factory=lambda: Path(__file__).resolve().parents[2]
    )
    poll_stats_seconds: float = 3.0
    poll_events_seconds: float = 3.0
    poll_modules_seconds: float = 3.0
    poll_cluster_seconds: float = 3.0
    poll_system_seconds: float = 5.0

    @property
    def nodes(self) -> List[Tuple[str, str, str]]:
        return cluster_nodes(self.api_url)
