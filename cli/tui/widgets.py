"""Shared TUI widgets."""

from __future__ import annotations

from typing import Generic, Hashable, TypeVar

from dataclasses import dataclass

from textual import events, on
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.message import Message
from textual.reactive import var
from textual.widget import Widget
from textual.widgets import Button, LoadingIndicator, Log, OptionList, Static

PickerType = TypeVar("PickerType", bound=Hashable)
PICKER_IMPL = "inline-dropdown-v2"


class PickerDropdown(OptionList):
    """Inline dropdown list — floats over the UI, no screen stack."""

    BINDINGS = [Binding("escape", "dismiss_menu", "Close")]

    @dataclass
    class Dismiss(Message):
        lost_focus: bool = False

    @dataclass
    class Selected(Message):
        option_id: str | None

    def action_dismiss_menu(self) -> None:
        self.post_message(self.Dismiss())

    def _on_blur(self, _event: events.Blur) -> None:
        self.post_message(self.Dismiss(lost_focus=True))
        self.suppress_click()

    def on_option_list_option_selected(self, event: OptionList.OptionSelected) -> None:
        event.stop()
        self.post_message(self.Selected(event.option_id))


class OptionPicker(Vertical, Generic[PickerType], can_focus=True):
    """Toolbar dropdown: button + inline overlay list."""

    expanded: var[bool] = var(False, init=False)

    DEFAULT_CSS = """
    OptionPicker {
        width: 28;
        min-width: 28;
        height: auto;
    }
    OptionPicker > Button {
        width: 100%;
        height: 3;
        background: $surface;
        color: $text;
        padding: 0 1;
        content-align: left middle;
        border: solid $border-blurred;
    }
    OptionPicker:focus > Button {
        border: solid $accent;
    }
    OptionPicker > PickerDropdown {
        width: 1fr;
        display: none;
        height: auto;
        max-height: 14;
        overlay: screen;
        constrain: none inside;
        border: solid $border-blurred;
        background: $surface;
    }
    OptionPicker.-expanded > PickerDropdown {
        display: block;
    }
    """

    class Changed(Message):
        """Posted when the selected value changes."""

        def __init__(self, picker: "OptionPicker[PickerType]", value: PickerType) -> None:
            super().__init__()
            self.picker = picker
            self.value = value

        @property
        def control(self) -> "OptionPicker[PickerType]":
            return self.picker

    def __init__(
        self,
        options: list[tuple[str, PickerType]] | None = None,
        *,
        value: PickerType | None = None,
        prompt: str = "Choose…",
        id: str | None = None,
        classes: str | None = None,
        disabled: bool = False,
    ) -> None:
        super().__init__(id=id, classes=classes, disabled=disabled)
        self._options: list[tuple[str, PickerType]] = list(options or [])
        self._prompt = prompt
        self._value: PickerType | None = value
        if self._value is None and self._options:
            self._value = self._options[0][1]

    @property
    def value(self) -> PickerType | None:
        return self._value

    @value.setter
    def value(self, val: PickerType) -> None:
        self.set_value(val, notify=True)

    def compose(self) -> ComposeResult:
        yield Button(self._button_label(), id="picker-btn", variant="default")
        yield PickerDropdown(id="picker-dropdown")

    def on_mount(self) -> None:
        self._sync_dropdown_options()

    def _sync_dropdown_options(self) -> None:
        from textual.widgets._option_list import Option

        dropdown = self.query_one("#picker-dropdown", PickerDropdown)
        dropdown.clear_options()
        dropdown.add_options(
            [Option(label, id=str(value)) for label, value in self._options]
        )
        for index, (_label, value) in enumerate(self._options):
            if value == self._value:
                dropdown.highlighted = index
                break

    def _label_map(self) -> dict[PickerType, str]:
        return {value: label for label, value in self._options}

    def _button_label(self) -> str:
        if self._value is not None:
            label = self._label_map().get(self._value, str(self._value))
        else:
            label = self._prompt
        return f"{label}  ▾"

    def _update_button(self) -> None:
        try:
            self.query_one("#picker-btn", Button).label = self._button_label()
        except Exception:
            pass

    def set_options(self, options: list[tuple[str, PickerType]]) -> None:
        self._options = list(options)
        labels = self._label_map()
        if self._value not in labels and self._options:
            self._value = self._options[0][1]
        self._update_button()
        if self.is_mounted:
            self._sync_dropdown_options()

    def set_value(self, val: PickerType, *, notify: bool = False) -> None:
        if val == self._value:
            return
        self._value = val
        self._update_button()
        if notify:
            self.post_message(self.Changed(self, val))

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id != "picker-btn":
            return
        self.expanded = not self.expanded

    def _watch_expanded(self, expanded: bool) -> None:
        self.set_class(expanded, "-expanded")
        if not expanded or not self.is_mounted:
            return
        dropdown = self.query_one("#picker-dropdown", PickerDropdown)
        for index, (_label, value) in enumerate(self._options):
            if value == self._value:
                dropdown.highlighted = index
                break
        dropdown.focus(scroll_visible=False)

    @on(PickerDropdown.Dismiss)
    def _on_dropdown_dismiss(self, event: PickerDropdown.Dismiss) -> None:
        event.stop()
        self.expanded = False
        if not event.lost_focus:
            self.focus()

    @on(PickerDropdown.Selected)
    def _on_dropdown_selected(self, event: PickerDropdown.Selected) -> None:
        event.stop()
        option_id = event.option_id
        if option_id is None:
            self.expanded = False
            return
        for _label, value in self._options:
            if str(value) == option_id:
                self.set_value(value, notify=True)
                break
        self.expanded = False
        self.focus()

    def on_focus(self) -> None:
        self.query_one("#picker-btn", Button).focus()


class LoadingBar(Horizontal):
    """App-wide loading strip — spinner + status message."""

    DEFAULT_CSS = """
    LoadingBar {
        height: 1;
        width: 100%;
        background: $primary-darken-2;
        padding: 0 1;
        display: none;
    }
    LoadingBar LoadingIndicator {
        width: 3;
        height: 1;
        margin-right: 1;
    }
    LoadingBar #loading-message {
        width: 1fr;
        height: 1;
        content-align: left middle;
        color: $text;
    }
    """

    def compose(self) -> ComposeResult:
        yield LoadingIndicator()
        yield Static("", id="loading-message")

    def set_message(self, message: str) -> None:
        self.query_one("#loading-message", Static).update(message)
        self.display = True

    def hide(self) -> None:
        self.display = False


class StatCard(Static):
    """Single metric card — one Static, no nested IDs."""

    DEFAULT_CSS = """
    StatCard {
        width: 1fr;
        height: 3;
        content-align: center middle;
        border: solid $accent;
        padding: 0 1;
        text-align: center;
    }
    """

    def __init__(self, label: str, value: str = "—", **kwargs) -> None:
        super().__init__(self._text(label, value), **kwargs)
        self._label = label
        self._value = value

    @staticmethod
    def _text(label: str, value: str) -> str:
        return f"{label}\n[bold]{value}[/bold]"

    def set_value(self, value: str) -> None:
        self._value = value
        self.update(self._text(self._label, value))


class StatsBar(Horizontal):
    """Row of stat cards."""

    DEFAULT_CSS = """
    StatsBar {
        height: 3;
        width: 100%;
    }
    """

    def __init__(self, *labels: str, **kwargs) -> None:
        super().__init__(**kwargs)
        self._labels = labels

    def compose(self) -> ComposeResult:
        for i, label in enumerate(self._labels):
            yield StatCard(label, id=f"stat-{i}")

    def set_values(self, *values: str) -> None:
        for card, value in zip(self.query(StatCard), values):
            card.set_value(value)


class OutputLog(Vertical):
    """Selectable log with a copy action docked bottom-right."""

    ALLOW_SELECT = False

    BINDINGS = [
        Binding("y", "copy_all", "Copy log", show=False),
    ]

    DEFAULT_CSS = """
    OutputLog {
        height: 1fr;
        min-height: 8;
        border: solid $surface-lighten-1;
    }
    OutputLog #log-body {
        height: 1fr;
        min-height: 6;
        padding: 0 1;
        border: none;
        background: transparent;
    }
    OutputLog #log-footer {
        height: 3;
        width: 100%;
        padding: 0 1 0 0;
        align: right middle;
    }
    OutputLog #log-footer Button {
        min-width: 10;
    }
    """

    def __init__(
        self,
        *args,
        markup: bool = False,
        highlight: bool = False,
        copy_label: str = "Copy log",
        **kwargs,
    ) -> None:
        # `markup` kept for call-site compatibility; Log writes plain text.
        super().__init__(*args, **kwargs)
        self._highlight = highlight
        self._copy_label = copy_label

    def compose(self) -> ComposeResult:
        yield Log(id="log-body", highlight=self._highlight)
        with Horizontal(id="log-footer"):
            yield Button(self._copy_label, id="log-copy", variant="default")

    @property
    def _log(self) -> Log:
        return self.query_one("#log-body", Log)

    @property
    def lines(self) -> list[str]:
        return self._log.lines

    def write(self, data: object) -> None:
        self._log.write(str(data))

    def clear(self) -> None:
        self._log.clear()

    def plain_text(self) -> str:
        return "\n".join(self.lines)

    def action_copy_all(self) -> None:
        text = self.plain_text().strip()
        if text:
            self.app.copy_to_clipboard(text)

    async def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "log-copy":
            self.action_copy_all()

    def write_line(self, message: str) -> None:
        from datetime import datetime

        ts = datetime.now().strftime("%H:%M:%S")
        self._log.write_line(f"[{ts}] {message}")

    def write_banner(self, title: str) -> None:
        from datetime import datetime

        ts = datetime.now().strftime("%H:%M:%S")
        self._log.write_line(f"[{ts}] ▶  {title}")
        self._log.write_line("─" * 60)
