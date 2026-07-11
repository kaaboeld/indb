"""Control tab — live stats, system log, local actions."""

from __future__ import annotations

import asyncio

from textual.app import ComposeResult
from textual.containers import Horizontal
from textual.widget import Widget
from textual.widgets import Button

from cli.tui.runner import run_audit, run_pytest
from cli.tui.widgets import OutputLog, StatsBar


class ControlTab(Widget):
    DEFAULT_CSS = """
    ControlTab {
        layout: vertical;
        height: 100%;
    }
    ControlTab #control-actions {
        height: auto;
        margin: 0 0 1 0;
    }
    ControlTab #control-actions Button {
        margin-right: 1;
    }
    """

    def compose(self) -> ComposeResult:
        yield StatsBar("Events", "Fusion %", "Server", id="control-stats")
        with Horizontal(id="control-actions"):
            yield Button("Run Tests", id="btn-tests", variant="primary")
            yield Button("Run Audit", id="btn-audit")
            yield Button("Restart", id="btn-restart", variant="warning")
        yield OutputLog(id="control-log", highlight=True)

    def on_mount(self) -> None:
        log = self.query_one("#control-log", OutputLog)
        log.write_line(f"INDB TUI started — API {self.app.tui_config.api_url}")
        if self.app.tui_config.in_docker:
            for btn_id in ("btn-tests", "btn-audit", "btn-restart"):
                self.query_one(f"#{btn_id}", Button).display = False
        else:
            log.write_line("Standalone mode — Control Panel enabled")

    async def load_data(self) -> None:
        api = self.app.api
        overview, health = await asyncio.gather(
            asyncio.to_thread(api.analytics_overview),
            asyncio.to_thread(api.health),
        )
        db = overview.get("database", {}) if overview else {}
        perf = overview.get("performance", {}) if overview else {}
        if health.get("status") == "ok":
            events = str(db.get("total_events", 0))
            server = "Running"
        else:
            events = "—"
            server = "Down"
            err = health.get("error") or api.last_error or "unreachable"
            self._log_api_error(str(err))
        fusion = perf.get("fusion_compression_rate")
        if fusion is None:
            fusion_data = overview.get("fusion", {}) if overview else {}
            fusion = fusion_data.get("fusion_rate", "—")
        fusion_text = f"{fusion}%" if isinstance(fusion, (int, float)) else str(fusion)
        self.query_one("#control-stats", StatsBar).set_values(events, fusion_text, server)

        sys_h = overview.get("system_health", {}) if overview else {}
        if sys_h and health.get("status") == "ok":
            cpu = sys_h.get("cpu_percent", 0)
            mem = sys_h.get("memory_rss_mb", 0)
            line = f"CPU {cpu:.1f}% | RAM {mem:.0f} MB"
            if getattr(self, "_last_sys_line", None) != line:
                self._last_sys_line = line
                self.query_one("#control-log", OutputLog).write_line(line)

    def _log_api_error(self, err: str) -> None:
        if getattr(self, "_last_api_error", None) == err:
            return
        self._last_api_error = err
        self.query_one("#control-log", OutputLog).write_line(f"⚠ API error: {err}")

    async def on_button_pressed(self, event: Button.Pressed) -> None:
        if self.app.tui_config.in_docker:
            return
        log = self.query_one("#control-log", OutputLog)
        btn = event.button.id
        root = self.app.tui_config.project_root

        if btn == "btn-tests":
            log.write_banner("Run Tests")
            code = await run_pytest(root, log.write_line)
            log.write_line(f"Done (Exit {code})")
        elif btn == "btn-audit":
            log.write_banner("Run Audit")
            code = await run_audit(root, log.write_line)
            log.write_line(f"Done (Exit {code})")
        elif btn == "btn-restart":
            log.write_banner("Restart")
            log.write_line("Launching ./start.sh in background…")
            proc = await asyncio.create_subprocess_shell(
                "./start.sh",
                cwd=str(root),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            log.write_line(f"Restart process started (pid {proc.pid})")
