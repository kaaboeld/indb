"""
INDB Core Module

Exports main classes including analytics.

The re-exports are resolved on first attribute access rather than at import time.
Importing them eagerly made core and storage mutually circular: `import
storage.binary` pulls core.encryption, which used to execute core.indb here, which
imports storage.binary again while it is still half-initialised. Anything that
touched storage before core failed with an ImportError.
"""

from importlib import import_module
from typing import TYPE_CHECKING

_EXPORTS = {
    "Event": "core.event",
    "TTLCache": "core.cache",
    "INDB": "core.indb",
    "INDBKernel": "core.kernel",
    "INDBAnalytics": "core.analytics",
}


def __getattr__(name: str):
    module_path = _EXPORTS.get(name)
    if module_path is None:
        raise AttributeError(f"module 'core' has no attribute {name!r}")
    value = getattr(import_module(module_path), name)
    globals()[name] = value  # cache, so the lookup happens once
    return value


def __dir__():
    return sorted(__all__)


if TYPE_CHECKING:  # for type checkers and editors, never executed at runtime
    from core.analytics import INDBAnalytics
    from core.cache import TTLCache
    from core.event import Event
    from core.indb import INDB
    from core.kernel import INDBKernel

__all__ = ["Event", "TTLCache", "INDB", "INDBKernel", "INDBAnalytics"]
