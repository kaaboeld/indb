"""Scripts tab — one-click operational scripts."""

from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import Grid
from textual.widget import Widget
from textual.widgets import Button

from cli.tui.runner import default_scripts, stream_process
from cli.tui.widgets import OutputLog


class ScriptsTab(Widget):
    DEFAULT_CSS = """
    ScriptsTab {
        layout: vertical;
        height: 100%;
    }
    ScriptsTab #scripts-grid {
        grid-size: 4;
        grid-gutter: 1;
        height: auto;
        margin-bottom: 1;
    }
    ScriptsTab #scripts-grid Button {
        width: 100%;
    }
    ScriptsTab OutputLog {
        height: 1fr;
    }
    """

    def compose(self) -> ComposeResult:
        yield Grid(id="scripts-grid")
        yield OutputLog(id="scripts-log", highlight=True)

    def on_mount(self) -> None:
        root = self.app.tui_config.project_root
        self._specs_by_id: dict[str, object] = {}
        self._running = False
        grid = self.query_one("#scripts-grid", Grid)
        for spec in default_scripts(root):
            btn_id = f"script-{spec.label.replace(' ', '-')}"
            self._specs_by_id[btn_id] = spec
            grid.mount(
                Button(
                    f"{spec.emoji} {spec.label}",
                    id=btn_id,
                    variant="default",
                )
            )

    def refresh_tab(self) -> None:
        pass

    async def on_button_pressed(self, event: Button.Pressed) -> None:
        if self._running:
            return
        spec = self._specs_by_id.get(event.button.id or "")
        if not spec:
            return

        log = self.query_one("#scripts-log", OutputLog)
        log.write_banner(f"{spec.emoji} {spec.label}")
        self._running = True
        try:
            env = {"INDB_API_URL": self.app.tui_config.api_url}
            code = await stream_process(
                spec.command,
                spec.cwd or self.app.tui_config.project_root,
                log.write_line,
                env=env,
            )
            log.write_line(f"Done (Exit {code})")
        finally:
            self._running = False
