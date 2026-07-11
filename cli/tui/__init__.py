"""INDB Terminal User Interface (Textual)."""

from typing import TYPE_CHECKING

__all__ = ["INDBTuiApp"]

if TYPE_CHECKING:
    from cli.tui.app import INDBTuiApp


def __getattr__(name: str):
    if name == "INDBTuiApp":
        from cli.tui.app import INDBTuiApp

        return INDBTuiApp
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
