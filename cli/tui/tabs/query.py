"""Query Lab tab — full cognitive API surface (user input only, no mock defaults)."""

from __future__ import annotations

import asyncio

from textual.app import ComposeResult
from textual.containers import Horizontal
from textual.widget import Widget
from textual.widgets import Button, Input, Static

from cli.tui.helpers import pretty_json
from cli.tui.widgets import OptionPicker, OutputLog


QUERY_MODES = [
    ("Interpret (Exhale)", "interpret"),
    ("Prism Synthesize", "prism"),
    ("Prism Instinct", "instinct"),
    ("Lens Query", "lens"),
    ("Echo Resonate", "echo"),
    ("Deduction", "deduction"),
    ("What-If", "what_if"),
    ("Context Slice", "slice"),
    ("Paradox Create", "paradox_create"),
    ("Paradox Read", "paradox_read"),
    ("Recovery Identity", "recovery"),
]


class QueryTab(Widget):
    DEFAULT_CSS = """
    QueryTab {
        layout: vertical;
        height: 100%;
    }
    QueryTab #query-toolbar {
        height: auto;
        margin-bottom: 1;
    }
    QueryTab #query-mode {
        width: 28;
        min-width: 28;
        height: 3;
    }
    QueryTab #query-primary {
        width: 2fr;
    }
    QueryTab #query-secondary,
    QueryTab #query-tertiary {
        width: 1fr;
    }
    QueryTab #query-toolbar Button {
        min-width: 9;
        margin-left: 1;
    }
    QueryTab #query-hint {
        height: 2;
        color: $text-muted;
        margin-bottom: 1;
    }
    QueryTab #query-output {
        height: 1fr;
    }
    """

    HINTS = {
        "interpret": "Required: mood | location [| goal]. Uses live /api/v2/interpret.",
        "prism": "Required: event ID or query text.",
        "instinct": "Required: query [| adrenaline]. Secondary field can set adrenaline.",
        "lens": "Required: context_a | context_b.",
        "echo": "Required: seed event UUID.",
        "deduction": "Required: evidence query text.",
        "what_if": "Required: base_query | modifier.",
        "slice": "Required: query | what_if modifier.",
        "paradox_create": "Required: source IDs (comma-separated). Optional: generation_mode, collapse_mode.",
        "paradox_read": "Required: paradox UUID.",
        "recovery": "Required: key_id (SHA-256 of public key).",
    }

    def compose(self) -> ComposeResult:
        with Horizontal(id="query-toolbar"):
            yield OptionPicker(
                [(label, key) for label, key in QUERY_MODES],
                id="query-mode",
                value="interpret",
                prompt="Mode",
            )
            yield Input(placeholder="Primary input…", id="query-primary")
            yield Input(placeholder="Secondary…", id="query-secondary")
            yield Input(placeholder="Tertiary…", id="query-tertiary")
            yield Button("Run", id="query-run", variant="primary")
        yield Static(self.HINTS["interpret"], id="query-hint")
        yield OutputLog(id="query-output", highlight=True)

    def on_mount(self) -> None:
        self.query_one("#query-primary", Input).focus()

    def refresh_tab(self) -> None:
        pass

    def on_option_picker_changed(self, event: OptionPicker.Changed) -> None:
        if event.picker.id == "query-mode":
            hint = self.HINTS.get(str(event.value), "")
            self.query_one("#query-hint", Static).update(hint)

    async def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "query-run":
            await self.execute_query()

    async def on_input_submitted(self, event: Input.Submitted) -> None:
        if event.input.id in ("query-primary", "query-secondary"):
            await self.execute_query()

    async def execute_query(self) -> None:
        mode = str(self.query_one("#query-mode", OptionPicker).value)
        primary = self.query_one("#query-primary", Input).value.strip()
        secondary = self.query_one("#query-secondary", Input).value.strip()
        tertiary = self.query_one("#query-tertiary", Input).value.strip()
        log = self.query_one("#query-output", OutputLog)
        log.write(f"▶ {mode}: {primary or '(empty)'}")
        await self._run_query(mode, primary, secondary, tertiary)

    @staticmethod
    def _split_pipe(value: str, parts: int = 2) -> list[str]:
        return [p.strip() for p in value.split("|", parts - 1)]

    async def _run_query(
        self, mode: str, primary: str, secondary: str, tertiary: str
    ) -> None:
        api = self.app.api
        try:
            if mode == "interpret":
                if not primary:
                    raise ValueError("interpret requires mood | location [| goal]")
                parts = self._split_pipe(primary, 3)
                mood = parts[0]
                location = parts[1] if len(parts) > 1 else ""
                goal = parts[2] if len(parts) > 2 else secondary
                if not mood or not location:
                    raise ValueError("interpret requires mood and location")
                result = await asyncio.to_thread(
                    api.interpret, mood=mood, location=location, goal=goal
                )
            elif mode == "prism":
                if not primary:
                    raise ValueError("prism requires query text or event ID")
                result = await asyncio.to_thread(api.prism_synthesize, primary)
            elif mode == "instinct":
                if not primary:
                    raise ValueError("instinct requires query text")
                parts = primary.split("|")
                query = parts[0].strip()
                adrenaline_text = parts[1].strip() if len(parts) > 1 else secondary
                if not adrenaline_text:
                    raise ValueError("instinct requires adrenaline in primary or secondary field")
                adrenaline = float(adrenaline_text)
                result = await asyncio.to_thread(api.prism_instinct, query, adrenaline)
            elif mode == "lens":
                if not primary:
                    raise ValueError("lens requires context_a | context_b")
                parts = self._split_pipe(primary, 2)
                ctx_a = parts[0]
                ctx_b = parts[1] if len(parts) > 1 else secondary
                if not ctx_a or not ctx_b:
                    raise ValueError("lens requires both context_a and context_b")
                result = await asyncio.to_thread(
                    api.lens_query, context_a=ctx_a, context_b=ctx_b
                )
            elif mode == "echo":
                seed = primary or secondary
                if not seed:
                    raise ValueError("echo requires seed event UUID")
                result = await asyncio.to_thread(api.echo_resonate, seed)
            elif mode == "deduction":
                if not primary:
                    raise ValueError("deduction requires query text")
                result = await asyncio.to_thread(api.deduce, primary)
            elif mode == "what_if":
                if not primary:
                    raise ValueError("what_if requires base_query | modifier")
                parts = self._split_pipe(primary, 2)
                base = parts[0]
                modifier = parts[1] if len(parts) > 1 else secondary
                if not base or not modifier:
                    raise ValueError("what_if requires base_query and modifier")
                result = await asyncio.to_thread(api.what_if, base, modifier)
            elif mode == "slice":
                if not primary:
                    raise ValueError("slice requires query | modifier")
                parts = self._split_pipe(primary, 2)
                query = parts[0]
                modifier = parts[1] if len(parts) > 1 else secondary
                if not query or not modifier:
                    raise ValueError("slice requires query and modifier")
                result = await asyncio.to_thread(api.slice, query, modifier)
            elif mode == "paradox_create":
                sources = [s.strip() for s in (primary or secondary).split(",") if s.strip()]
                if not sources:
                    raise ValueError("paradox_create requires comma-separated source IDs")
                if not secondary or not tertiary:
                    raise ValueError(
                        "paradox_create requires generation_mode (secondary) "
                        "and collapse_mode (tertiary)"
                    )
                result = await asyncio.to_thread(
                    api.paradox_create, sources, secondary, tertiary
                )
            elif mode == "paradox_read":
                paradox_id = primary or secondary
                if not paradox_id:
                    raise ValueError("paradox_read requires paradox UUID")
                result = await asyncio.to_thread(api.paradox_get, paradox_id)
            elif mode == "recovery":
                key_id = primary or secondary
                if not key_id:
                    raise ValueError("recovery requires key_id")
                result = await asyncio.to_thread(api.recovery_identity, key_id)
            else:
                result = {"error": f"Unknown mode: {mode}"}
            text = pretty_json(result)
        except Exception as exc:
            text = f"ERROR: {exc}"
        self._show_result(text)

    def _show_result(self, text: str) -> None:
        log = self.query_one("#query-output", OutputLog)
        log.write(text)
        log.write("─" * 60)
