"""
Hermes source connector — ingests Hermes agent activity into INDB.

SourceManager discovers this package automatically via MANIFEST.
Hermes sessions and memories are polled and transformed into INDB Events.
"""
from services.sources.hermes.connector import HermesConnector
from services.sources.hermes.config import HermesConfig

__all__ = ["HermesConnector", "HermesConfig", "MANIFEST"]

MANIFEST = {
    "name": "hermes",
    "connector_class": HermesConnector,
    "config_class": HermesConfig,
}
