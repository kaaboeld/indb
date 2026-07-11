"""Events tab — live searchable event table."""

from __future__ import annotations

import asyncio
from typing import List, Tuple

from textual.app import ComposeResult
from textual.containers import Horizontal
from textual.widget import Widget
from textual.widgets import Button, DataTable, Input, Static

from cli.tui.helpers import (
    event_content,
    event_id_short,
    format_timestamp,
    location_label,
    matches_filter,
    truncate,
)
from cli.tui.widgets import OptionPicker

SOURCE_MIXED = "mixed"
SOURCE_LATEST = "latest"


class EventsTab(Widget):
    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self._events_cache: list = []
        self._filter = ""
        self._source_mode = SOURCE_MIXED
        self._source_options: List[Tuple[str, str]] = [
            ("All sources", SOURCE_MIXED),
            ("Latest", SOURCE_LATEST),
        ]

    DEFAULT_CSS = """
    EventsTab {
        layout: vertical;
        height: 100%;
    }
    EventsTab #events-toolbar {
        height: auto;
        margin-bottom: 1;
    }
    EventsTab #events-toolbar Input {
        width: 1fr;
    }
    EventsTab #events-source {
        width: 28;
        min-width: 28;
        height: 3;
        margin-right: 1;
    }
    EventsTab #events-toolbar Button {
        margin-left: 1;
    }
    EventsTab #events-status {
        height: 1;
        color: $text-muted;
        margin-bottom: 1;
    }
    EventsTab DataTable {
        height: 1fr;
        min-height: 10;
    }
    """

    def compose(self) -> ComposeResult:
        with Horizontal(id="events-toolbar"):
            yield OptionPicker(
                self._source_options,
                id="events-source",
                value=SOURCE_MIXED,
                prompt="Source",
            )
            yield Input(
                placeholder="Filter events…",
                id="events-search",
            )
            yield Button("Filter", id="events-search-btn", variant="primary")
            yield Button("API Search", id="events-api-btn")
        yield Static("Loading…", id="events-status")
        table = DataTable(id="events-table", zebra_stripes=True)
        table.add_columns("ID", "Time", "Location", "Content")
        table.cursor_type = "row"
        yield table

    async def load_data(self) -> None:
        api = self.app.api
        health = await asyncio.to_thread(api.health)
        if health.get("status") != "ok":
            err = health.get("error") or api.last_error or "API unreachable"
            self._show_error(str(err))
            return

        await self._refresh_source_options()
        events = await asyncio.to_thread(self._fetch_events)
        self._apply_events(events)

    def _fetch_events(self) -> list:
        api = self.app.api
        mode = self._source_mode
        if mode == SOURCE_MIXED:
            return api.events_mixed(per_source=10, max_total=50)
        if mode == SOURCE_LATEST:
            return api.events(50)
        return api.events_by_location(mode, 50)

    async def _refresh_source_options(self) -> None:
        overview = await asyncio.to_thread(self.app.api.analytics_overview)
        top_locations = overview.get("database", {}).get("top_locations", {})
        options: List[Tuple[str, str]] = [
            ("All sources", SOURCE_MIXED),
            ("Latest", SOURCE_LATEST),
        ]
        for location in top_locations:
            options.append((location_label(location, 30), location))

        if options == self._source_options:
            return

        self._source_options = options
        picker = self.query_one("#events-source", OptionPicker)
        current = self._source_mode
        picker.set_options(options)
        if any(value == current for _, value in options):
            picker.set_value(current)
        else:
            picker.set_value(SOURCE_MIXED)
            self._source_mode = SOURCE_MIXED

    def _show_error(self, err: str) -> None:
        self.query_one("#events-status", Static).update(f"⚠ API down: {err[:80]}")
        self.query_one("#events-table", DataTable).clear(columns=False)

    def _apply_events(self, events: list) -> None:
        self._events_cache = events
        self._render_table()

    def _source_status_label(self) -> str:
        if self._source_mode == SOURCE_MIXED:
            return "mixed sources"
        if self._source_mode == SOURCE_LATEST:
            return "latest"
        return location_label(self._source_mode, 30)

    def _render_table(self, api_results: list | None = None) -> None:
        table = self.query_one("#events-table", DataTable)
        status = self.query_one("#events-status", Static)
        table.clear(columns=False)

        source = api_results if api_results is not None else self._events_cache
        shown = 0
        sources_seen: set[str] = set()
        for event in source:
            if api_results is None and not matches_filter(event, self._filter):
                continue
            loc = str(event.get("location", "—"))
            sources_seen.add(loc)
            table.add_row(
                event_id_short(event),
                format_timestamp(event.get("timestamp", 0)),
                location_label(loc),
                truncate(event_content(event), 60),
            )
            shown += 1

        label = "API search" if api_results is not None else self._source_status_label()
        if api_results is None and self._filter:
            label = f"{label} · filter: {self._filter}"
        elif api_results is None:
            label = f"{label} · {len(sources_seen)} sources"
        status.update(f"{shown} events ({label})")

    def on_option_picker_changed(self, event: OptionPicker.Changed) -> None:
        if event.picker.id != "events-source":
            return
        self._source_mode = str(event.value)
        self.app.call_later(self.load_data)

    def on_input_submitted(self, event: Input.Submitted) -> None:
        if event.input.id == "events-search":
            self._filter = event.value.strip()
            self._render_table()

    async def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "events-search-btn":
            search = self.query_one("#events-search", Input)
            self._filter = search.value.strip()
            self._render_table()
        elif event.button.id == "events-api-btn":
            query = self.query_one("#events-search", Input).value.strip()
            if query:
                results = await asyncio.to_thread(self.app.api.search, query, 50)
                self._render_table(results)
