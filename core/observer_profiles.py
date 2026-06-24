"""
Observer profiles — named ObserverContext presets (config-driven, not hardcoded in logic).

Load from JSON path: OBSERVER_PROFILES_PATH (default: data/observer_profiles.json if exists).
"""
from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Dict, Optional

from core.prism import ObserverContext

logger = logging.getLogger("indb.observer_profiles")

_profiles: Dict[str, ObserverContext] = {}
_loaded = False


def _default_path() -> Path:
    env = os.getenv("OBSERVER_PROFILES_PATH")
    if env:
        return Path(env)
    backend_root = Path(__file__).resolve().parent.parent
    return backend_root / "data" / "observer_profiles.json"


def load_profiles(force: bool = False) -> None:
    global _loaded, _profiles
    if _loaded and not force:
        return
    _profiles = {}
    path = _default_path()
    if not path.is_file():
        logger.debug("Observer profiles file not found: %s", path)
        _loaded = True
        return
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
        for name, body in raw.items():
            if isinstance(body, dict):
                _profiles[name] = ObserverContext(**body)
        logger.info("Loaded %d observer profile(s) from %s", len(_profiles), path)
    except Exception as e:
        logger.warning("Failed to load observer profiles from %s: %s", path, e)
    _loaded = True


def list_profile_ids() -> list[str]:
    load_profiles()
    return sorted(_profiles.keys())


def get_profile(profile_id: str) -> Optional[ObserverContext]:
    load_profiles()
    return _profiles.get(profile_id)


def resolve_observer(
    profile_id: Optional[str],
    explicit: Optional[ObserverContext],
) -> Optional[ObserverContext]:
    """Explicit context wins; else load named profile."""
    if explicit is not None:
        return explicit
    if profile_id:
        profile = get_profile(profile_id)
        if profile is None:
            raise ValueError(f"Unknown observer profile: {profile_id}")
        return profile
    return None
