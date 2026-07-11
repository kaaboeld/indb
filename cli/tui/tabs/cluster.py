"""Cluster tab — API and Raft status from the configured endpoint."""

from __future__ import annotations

import asyncio

from textual.app import ComposeResult
from textual.widget import Widget
from textual.widgets import DataTable, Static

from cli.tui.helpers import node_status_label, raft_role_label


class ClusterTab(Widget):
    DEFAULT_CSS = """
    ClusterTab {
        layout: vertical;
        height: 100%;
    }
    ClusterTab #cluster-summary {
        height: 2;
        margin-bottom: 1;
        text-style: bold;
    }
    ClusterTab DataTable {
        height: 1fr;
        min-height: 8;
    }
    """

    def compose(self) -> ComposeResult:
        yield Static("Loading cluster status…", id="cluster-summary")
        table = DataTable(id="cluster-table", zebra_stripes=True)
        table.add_columns("Endpoint", "Status", "Port", "Raft", "Term")
        yield table

    async def load_data(self) -> None:
        api = self.app.api
        raft = await asyncio.to_thread(api.raft_status)
        nodes = self.app.tui_config.nodes
        rows = []
        active = 0
        for name, url, port in nodes:
            ok, data, err = await asyncio.to_thread(api.node_status, url)
            if ok:
                active += 1
            node_raft = data.get("raft", {}) if data else {}
            state = node_raft.get("state") or node_raft.get("status") or raft.get("status", "—")
            leader = node_raft.get("leader") or node_raft.get("node_id")
            is_leader = (
                str(state).lower() == "leader"
                or (leader and node_raft.get("node_id") == leader)
            )
            rows.append(
                (
                    name,
                    node_status_label(ok, error=bool(err and not ok)),
                    port,
                    raft_role_label(str(state), is_leader),
                    str(node_raft.get("term", raft.get("term", "—"))),
                )
            )
        strategy = str(raft.get("status") or ("active" if active else "unreachable"))
        self._update(rows, active, len(nodes), strategy)

    def _update(self, rows: list, active: int, total: int, strategy: str) -> None:
        self.query_one("#cluster-summary", Static).update(
            f"Endpoints: {active}/{total} up | Raft: {strategy}"
        )
        table = self.query_one("#cluster-table", DataTable)
        table.clear(columns=False)
        for row in rows:
            table.add_row(*row)
