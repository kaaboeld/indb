"""Tab widgets for INDB TUI."""

from cli.tui.tabs.control import ControlTab
from cli.tui.tabs.events import EventsTab
from cli.tui.tabs.modules import ModulesTab
from cli.tui.tabs.cluster import ClusterTab
from cli.tui.tabs.query import QueryTab
from cli.tui.tabs.analytics import AnalyticsTab
from cli.tui.tabs.scripts import ScriptsTab

__all__ = [
    "ControlTab",
    "EventsTab",
    "ModulesTab",
    "ClusterTab",
    "QueryTab",
    "AnalyticsTab",
    "ScriptsTab",
]
