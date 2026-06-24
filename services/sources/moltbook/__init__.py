"""
Moltbook source connector.

SourceManager discovers this package automatically via MANIFEST.
To add a new source: create a package with a MANIFEST dict like this one.
"""
from services.sources.moltbook.connector import MoltbookConnector
from services.sources.moltbook.config import MoltbookConfig

__all__ = ["MoltbookConnector", "MoltbookConfig", "MANIFEST"]

# ── Discovery contract ────────────────────────────────────────────────────────
# SourceManager reads this dict. Both classes must implement:
#   - connector_class(kernel, config) + async start() / async stop()
#   - config_class.from_env() → returns populated config dataclass with `enabled: bool`
MANIFEST = {
    "name": "moltbook",
    "connector_class": MoltbookConnector,
    "config_class": MoltbookConfig,
}
