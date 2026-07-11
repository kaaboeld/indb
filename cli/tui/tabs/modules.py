"""Modules tab — source connectors and protocols."""

from __future__ import annotations

import asyncio

from textual.app import ComposeResult
from textual.widget import Widget
from textual.widgets import DataTable, Static

from cli.tui.helpers import module_status_icon


class ModulesTab(Widget):
    DEFAULT_CSS = """
    ModulesTab {
        layout: vertical;
        height: 100%;
    }
    ModulesTab .section-title {
        text-style: bold;
        margin: 0 0 1 0;
        height: 1;
    }
    ModulesTab DataTable {
        height: 1fr;
        min-height: 8;
    }
    ModulesTab #protocols-status {
        height: 2;
        color: $text-muted;
        margin-top: 1;
    }
    """

    def compose(self) -> ComposeResult:
        yield Static("Source Connectors", classes="section-title")
        mod_table = DataTable(id="modules-table", zebra_stripes=True)
        mod_table.add_columns("Module", "Enabled", "Status", "API Key")
        yield mod_table
        yield Static("Active Protocols", classes="section-title")
        proto_table = DataTable(id="protocols-table", zebra_stripes=True)
        proto_table.add_columns("Protocol", "Status", "Port")
        yield proto_table
        yield Static("", id="protocols-status")

    async def load_data(self) -> None:
        api = self.app.api
        modules, protocols = await asyncio.gather(
            asyncio.to_thread(api.modules),
            asyncio.to_thread(api.protocols),
        )
        self._update_tables(modules, protocols)

    def _update_tables(self, modules: list, protocols: dict) -> None:
        mod_table = self.query_one("#modules-table", DataTable)
        mod_table.clear(columns=False)
        for mod in modules:
            enabled = "✓" if mod.get("enabled") else "✗"
            status = mod.get("status", "unknown")
            icon = module_status_icon(status)
            needs_key = mod.get("needs_api_key", False)
            key_col = "—" if not needs_key else ("✓" if mod.get("has_api_key") else "✗")
            mod_table.add_row(
                mod.get("name", "?"),
                enabled,
                f"{icon} {status}",
                key_col,
            )

        proto_table = self.query_one("#protocols-table", DataTable)
        proto_table.clear(columns=False)
        proto_list = protocols.get("protocols", [])
        for proto in proto_list:
            if isinstance(proto, dict):
                proto_table.add_row(
                    proto.get("name", "?"),
                    proto.get("status", "—"),
                    str(proto.get("port", "—")),
                )

        status = self.query_one("#protocols-status", Static)
        online = protocols.get("status", "unknown")
        if not modules and not proto_list:
            status.update(f"⚠ No data ({self.app.api.last_error or 'unknown'})")
        else:
            status.update(f"System protocols: {online} | {len(proto_list)} registered")
