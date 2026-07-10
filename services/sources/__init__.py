"""
Source connectors — pull-based ingestion adapters for external data sources.

Each connector lives in its own sub-package and exposes a MANIFEST dict.
SourceManager discovers them automatically — no registration needed.
"""
from services.sources.manager import source_manager

__all__ = ["source_manager"]
