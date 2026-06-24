"""
Source Manager — auto-discovers and manages all source connector modules.

Each source module (e.g. services/sources/moltbook/) must expose a MANIFEST dict:

    MANIFEST = {
        "name": "moltbook",
        "connector_class": MoltbookConnector,
        "config_class": MoltbookConfig,
    }

The manager discovers modules in services/sources/ that have a MANIFEST,
loads their config via config_class.from_env(), and starts enabled connectors.

Usage in app_factory.py:

    from services.sources.manager import source_manager
    ...
    await source_manager.start_all(kernel)
    ...
    await source_manager.stop_all()
"""
from __future__ import annotations

import asyncio
import importlib
import logging
import pkgutil
from typing import Any, Dict, List

logger = logging.getLogger("indb.sources")


class SourceManager:
    """
    Discovers and manages all registered source connectors.

    Discovery: iterates sub-packages of `services.sources`, imports each,
    and looks for a MANIFEST dict. No registration needed — just drop a
    new connector package and it'll be picked up automatically.
    """

    def __init__(self) -> None:
        self._connectors: List[tuple[str, Any]] = []  # (name, connector)
        self._connector_status: Dict[str, str] = {}  # name -> "running" | "error"

    def get_modules_status(self) -> List[Dict[str, Any]]:
        """
        Discover all source modules and return their config + runtime status.
        Used by /api/v2/modules and TUI.
        """
        import services.sources as sources_pkg
        result: List[Dict[str, Any]] = []

        for finder, module_name, is_pkg in pkgutil.walk_packages(
            path=sources_pkg.__path__,
            prefix=sources_pkg.__name__ + ".",
            onerror=lambda name: None,
        ):
            if not is_pkg or module_name.count(".") != 2:
                continue
            try:
                mod = importlib.import_module(module_name)
            except Exception:
                continue
            manifest = getattr(mod, "MANIFEST", None)
            if not manifest:
                continue

            name = manifest.get("name", "?")
            config_class = manifest.get("config_class")
            if not config_class:
                result.append({"name": name, "enabled": False, "status": "error", "detail": "no config_class"})
                continue

            try:
                cfg = config_class.from_env()
            except Exception as e:
                result.append({"name": name, "enabled": False, "status": "error", "detail": str(e)})
                continue

            enabled = getattr(cfg, "enabled", True)
            api_key = getattr(cfg, "api_key", None)
            needs_key = api_key is not None
            has_key = bool(api_key) if needs_key else True

            if not enabled:
                status = "disabled"
            elif needs_key and not has_key:
                status = "no_api_key"
            else:
                status = self._connector_status.get(name, "running" if enabled else "unknown")

            result.append({
                "name": name,
                "enabled": enabled,
                "status": status,
                "needs_api_key": needs_key,
                "has_api_key": has_key,
            })
        return result

    async def start_all(self, kernel) -> None:
        """
        Discover all source modules, load their configs, and start enabled ones.
        Called once at server startup.
        """
        import services.sources as sources_pkg

        for finder, module_name, is_pkg in pkgutil.walk_packages(
            path=sources_pkg.__path__,
            prefix=sources_pkg.__name__ + ".",
            onerror=lambda name: logger.debug("Cannot import source: %s", name),
        ):
            # Only look at direct sub-packages (depth=1), skip sub-modules
            if not is_pkg:
                continue
            if module_name.count(".") != 2:
                continue  # skip nested packages

            try:
                mod = importlib.import_module(module_name)
            except Exception as e:
                logger.warning("SourceManager: failed to import %s: %s", module_name, e)
                continue

            manifest = getattr(mod, "MANIFEST", None)
            if not manifest:
                continue  # not a connector package

            await self._start_from_manifest(manifest, kernel)

    async def _start_from_manifest(self, manifest: Dict[str, Any], kernel) -> None:
        """Load config and start a single connector from its manifest."""
        name = manifest.get("name", "?")
        connector_class = manifest.get("connector_class")
        config_class = manifest.get("config_class")

        if not connector_class or not config_class:
            logger.warning(
                "SourceManager: MANIFEST for %r is missing connector_class or config_class",
                name,
            )
            return

        try:
            cfg = config_class.from_env()
        except Exception as e:
            logger.warning("SourceManager: failed to load config for %r: %s", name, e)
            return

        if not getattr(cfg, "enabled", True):
            logger.info("SourceManager: source %r is disabled — skipping", name)
            return

        api_key = getattr(cfg, "api_key", None)
        if api_key is not None and not api_key:
            logger.info(
                "SourceManager: source %r has no API key — skipping "
                "(set %s_API_KEY in .env to enable)",
                name, name.upper().replace("-", "_"),
            )
            return

        try:
            connector = connector_class(kernel=kernel, config=cfg)
            self._connectors.append((name, connector))
            asyncio.create_task(connector.start())
            self._connector_status[name] = "running"
            logger.info("SourceManager: started source %r", name)
        except Exception as e:
            self._connector_status[name] = "error"
            logger.warning("SourceManager: failed to start source %r: %s", name, e)

    async def stop_all(self) -> None:
        """Gracefully stop all running connectors."""
        for name, connector in self._connectors:
            try:
                await connector.stop()
            except Exception as e:
                logger.warning("SourceManager: error stopping %r: %s", name, e)
            self._connector_status.pop(name, None)
        self._connectors.clear()
        logger.info("SourceManager: all sources stopped")


# Singleton — import and use this directly
source_manager = SourceManager()
