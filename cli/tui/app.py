"""INDB Terminal User Interface — main application."""

from __future__ import annotations

import asyncio
from typing import Optional, Sequence, Type

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.widget import Widget
from textual.widgets import Footer, Header, TabbedContent, TabPane

from cli.tui.api_client import ApiClient
from cli.tui.config import TuiConfig, resolve_api_url, PRODUCTION_API_URL
from cli.tui.widgets import LoadingBar, OutputLog
from cli.tui.tabs import (
    AnalyticsTab,
    ClusterTab,
    ControlTab,
    EventsTab,
    ModulesTab,
    QueryTab,
    ScriptsTab,
)

# Bump when TUI startup/refresh logic changes (visible in Control log).
TUI_BUILD = "2026-07-11e"

POLLABLE_TABS: Sequence[Type[Widget]] = (
    ControlTab,
    EventsTab,
    ModulesTab,
    ClusterTab,
    AnalyticsTab,
)

TAB_LOAD_LABELS: dict[Type[Widget], str] = {
    ControlTab: "Control",
    EventsTab: "Events",
    ModulesTab: "Modules",
    ClusterTab: "Cluster",
    AnalyticsTab: "Analytics",
}


class INDBTuiApp(App):
    """Full-featured INDB monitoring and operations TUI."""

    TITLE = "INDB"
    CSS = """
    Screen {
        background: $surface;
    }
    #app-loading {
        height: 1;
    }
    TabbedContent {
        height: 1fr;
    }
    TabPane {
        padding: 1;
        height: 1fr;
    }
    Header {
        background: $primary;
    }
    Footer {
        background: $panel;
    }

    /* Textual "tall" borders draw block chars on the left — use flat solid instead */
    Input {
        border: solid $border-blurred;
    }
    Input:focus {
        border: solid $accent;
    }
    Input.-invalid {
        border: solid $error 60%;
    }
    Input.-invalid:focus {
        border: solid $error;
    }

    Button {
        border: solid $border-blurred;
        border-top: solid $border-blurred;
        border-bottom: solid $border-blurred;
        border-left: solid $border-blurred;
        border-right: solid $border-blurred;
    }
    Button:hover {
        border: solid $border;
        border-top: solid $border;
        border-bottom: solid $border;
    }
    Button:focus {
        border: solid $accent;
        border-top: solid $accent;
        border-bottom: solid $accent;
    }
    Button.-primary {
        border: solid $primary;
        border-top: solid $primary;
        border-bottom: solid $primary;
    }
    Button.-primary:hover,
    Button.-primary:focus {
        border: solid $primary-lighten-1;
        border-top: solid $primary-lighten-1;
        border-bottom: solid $primary-lighten-1;
    }
    Button.-warning {
        border: solid $warning;
        border-top: solid $warning;
        border-bottom: solid $warning;
    }
    Button.-warning:hover,
    Button.-warning:focus {
        border: solid $warning-lighten-1;
        border-top: solid $warning-lighten-1;
        border-bottom: solid $warning-lighten-1;
    }

    OptionList {
        border: solid $border-blurred;
    }
    OptionList:focus {
        border: solid $accent;
    }
    """

    BINDINGS = [
        Binding("q", "quit", "Quit", show=True),
        Binding("r", "refresh_all", "Refresh", show=True),
        Binding("1", "tab_control", "Control", show=False),
        Binding("2", "tab_events", "Events", show=False),
        Binding("3", "tab_modules", "Modules", show=False),
        Binding("4", "tab_cluster", "Cluster", show=False),
        Binding("5", "tab_scripts", "Scripts", show=False),
        Binding("6", "tab_query", "Query", show=False),
        Binding("7", "tab_analytics", "Analytics", show=False),
        Binding("m", "tab_modules", "Modules", show=True),
        Binding("s", "tab_scripts", "Scripts", show=True),
        Binding("e", "tab_events", "Events", show=True),
        Binding("a", "tab_analytics", "Analytics", show=True),
        Binding("p", "tab_query", "Query", show=True),
    ]

    def __init__(self, api_url: Optional[str] = None, **kwargs) -> None:
        super().__init__(**kwargs)
        self._explicit_api_url = api_url
        self.tui_config = TuiConfig(api_url=PRODUCTION_API_URL)
        self.api = ApiClient(self.tui_config.api_url)
        self.api_reachable = False
        self._bootstrapped = False
        self._poll_lock: Optional[asyncio.Lock] = None
        self._loading_depth = 0

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        yield LoadingBar(id="app-loading")
        with TabbedContent(initial="control"):
            with TabPane("Control", id="control"):
                yield ControlTab()
            with TabPane("Events", id="events"):
                yield EventsTab()
            with TabPane("Modules", id="modules"):
                yield ModulesTab()
            with TabPane("Cluster", id="cluster"):
                yield ClusterTab()
            with TabPane("Query", id="query"):
                yield QueryTab()
            with TabPane("Analytics", id="analytics"):
                yield AnalyticsTab()
            with TabPane("Scripts", id="scripts"):
                yield ScriptsTab()
        yield Footer()

    def on_mount(self) -> None:
        self._poll_lock = asyncio.Lock()
        self.sub_title = f"{self.tui_config.api_url} | starting…"
        self.begin_loading("Starting INDB TUI…")
        self.call_later(self.bootstrap_api)

    def begin_loading(self, message: str) -> None:
        self._loading_depth += 1
        self._show_loading(message)

    def update_loading(self, message: str) -> None:
        if self._loading_depth > 0:
            self._show_loading(message)

    def end_loading(self) -> None:
        self._loading_depth = max(0, self._loading_depth - 1)
        if self._loading_depth == 0:
            try:
                self.query_one("#app-loading", LoadingBar).hide()
            except Exception:
                pass

    def _show_loading(self, message: str) -> None:
        try:
            self.query_one("#app-loading", LoadingBar).set_message(message)
        except Exception:
            pass
        if self._loading_depth > 0 and not self._bootstrapped:
            base = self.tui_config.api_url
            self.sub_title = f"{base} | {message.lower()}"

    async def bootstrap_api(self) -> None:
        self.update_loading("Connecting to API…")
        try:
            resolved_url, note = await asyncio.to_thread(
                resolve_api_url, self._explicit_api_url
            )
            self.api.reconfigure(resolved_url)
            self.tui_config = TuiConfig(api_url=resolved_url, connection_note=note)
            self.update_loading("Loading dashboard…")
            subtitle = f"{resolved_url} | v{self.tui_config.version}"
            if note:
                subtitle += " | connected"
            self.sub_title = subtitle
            self._bootstrapped = True
            self._write_control_log(f"TUI build {TUI_BUILD} picker=inline-dropdown-v2")
            self._write_control_log("Loading data from API…")
            await self._log_connection(note)
            await self.poll_all_tabs()
            self.set_interval(3, self.poll_all_tabs)
        finally:
            self.end_loading()

    async def _log_connection(self, note: Optional[str]) -> None:
        health = await asyncio.to_thread(self.api.health)
        ok = health.get("status") == "ok"
        self.api_reachable = ok
        try:
            log = self.query_one(ControlTab).query_one("#control-log", OutputLog)
            if note:
                log.write_line(f"ℹ {note}")
            if ok:
                overview = await asyncio.to_thread(self.api.analytics_overview)
                total = overview.get("database", {}).get("total_events", "?")
                log.write_line(f"✓ Connected — {total} events in memory")
            else:
                err = health.get("error") or self.api.last_error or "unreachable"
                log.write_line(f"⚠ API error: {err}")
        except Exception:
            pass

    def _write_control_log(self, message: str) -> None:
        try:
            self.query_one(ControlTab).query_one("#control-log", OutputLog).write_line(
                message
            )
        except Exception:
            pass

    async def _safe_load(self, widget: Widget) -> None:
        loader = getattr(widget, "load_data", None)
        if loader is None or not widget.is_mounted:
            return
        try:
            await loader()
        except Exception as exc:
            self._write_control_log(f"⚠ load error [{type(widget).__name__}]: {exc}")

    async def poll_all_tabs(self) -> None:
        if not self._bootstrapped or self._poll_lock is None:
            return
        nested = self._loading_depth > 0
        if not nested:
            self.begin_loading("Refreshing data…")
        async with self._poll_lock:
            try:
                for tab_cls in POLLABLE_TABS:
                    label = TAB_LOAD_LABELS.get(tab_cls, tab_cls.__name__)
                    self.update_loading(f"Loading {label}…")
                    for widget in self.query(tab_cls):
                        await self._safe_load(widget)
            finally:
                if not nested:
                    self.end_loading()

    def on_tabbed_content_tab_activated(self, event: TabbedContent.TabActivated) -> None:
        pane_id = event.pane.id or ""
        mapping = {
            "control": ControlTab,
            "events": EventsTab,
            "modules": ModulesTab,
            "cluster": ClusterTab,
            "analytics": AnalyticsTab,
        }
        tab_cls = mapping.get(pane_id)
        if tab_cls is None:
            return
        self.call_later(self._load_active_tab, tab_cls)

    async def _load_active_tab(self, tab_cls: Type[Widget]) -> None:
        label = TAB_LOAD_LABELS.get(tab_cls, tab_cls.__name__)
        nested = self._loading_depth > 0
        if not nested:
            self.begin_loading(f"Loading {label}…")
        try:
            for widget in self.query(tab_cls):
                await self._safe_load(widget)
        finally:
            if not nested:
                self.end_loading()

    def _cleanup_resources(self) -> None:
        for worker in list(self.workers):
            worker.cancel()
        try:
            self.api.close()
        except Exception:
            pass

    def action_quit(self) -> None:
        self._cleanup_resources()
        self.exit()

    def on_unmount(self) -> None:
        self._cleanup_resources()

    def action_refresh_all(self) -> None:
        self.call_later(self.poll_all_tabs)

    def action_tab_control(self) -> None:
        self.query_one(TabbedContent).active = "control"

    def action_tab_events(self) -> None:
        self.query_one(TabbedContent).active = "events"

    def action_tab_modules(self) -> None:
        self.query_one(TabbedContent).active = "modules"

    def action_tab_cluster(self) -> None:
        self.query_one(TabbedContent).active = "cluster"

    def action_tab_query(self) -> None:
        self.query_one(TabbedContent).active = "query"

    def action_tab_analytics(self) -> None:
        self.query_one(TabbedContent).active = "analytics"

    def action_tab_scripts(self) -> None:
        self.query_one(TabbedContent).active = "scripts"


def _purge_tui_bytecode() -> None:
    import shutil
    from pathlib import Path

    tui_root = Path(__file__).resolve().parent
    for cache in tui_root.rglob("__pycache__"):
        if cache.is_dir():
            shutil.rmtree(cache, ignore_errors=True)
    for artifact in tui_root.rglob("*.pyc"):
        artifact.unlink(missing_ok=True)


def _verify_tui_modules() -> None:
    import importlib
    import sys
    from pathlib import Path

    importlib.invalidate_caches()
    from cli.tui import widgets as tui_widgets

    widgets_path = Path(tui_widgets.__file__).resolve()
    source = widgets_path.read_text(encoding="utf-8")
    if "class PickerOverlay" in source:
        print(
            f"FATAL: stale widgets at {widgets_path} — still has PickerOverlay.\n"
            "Run: pkill -f cli.tui.app; cd db && ./start_tui.sh",
            file=sys.stderr,
        )
        raise SystemExit(1)
    if getattr(tui_widgets, "PICKER_IMPL", "") != "inline-dropdown-v2":
        print(
            f"FATAL: unexpected picker impl in {widgets_path}.\n"
            "Run: pkill -f cli.tui.app; cd db && ./start_tui.sh",
            file=sys.stderr,
        )
        raise SystemExit(1)
    print(f"picker={tui_widgets.PICKER_IMPL} widgets={widgets_path}", file=sys.stderr)


def main() -> None:
    import sys

    _purge_tui_bytecode()
    _verify_tui_modules()
    print(f"INDB TUI {TUI_BUILD} ← {__file__}", file=sys.stderr)
    app = INDBTuiApp()
    try:
        app.run()
    except KeyboardInterrupt:
        pass
    finally:
        app._cleanup_resources()


if __name__ == "__main__":
    main()
