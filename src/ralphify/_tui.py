"""Textual TUI dashboard for monitoring ralph runs.

The ``WatchApp`` renders a live dashboard that connects to the engine's
event system, showing iteration progress, streak counters, success rate,
and a scrollable log of iteration results.
"""

from __future__ import annotations

import threading
from typing import Any

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.message import Message
from textual.widgets import Footer, RichLog, Static

from ralphify._events import (
    STOP_COMPLETED,
    Event,
    EventEmitter,
    EventType,
    IterationEndedData,
    RunStartedData,
    RunStoppedData,
)
from ralphify._output import format_duration

_ICON_SUCCESS = "\u2713"
_ICON_FAILURE = "\u2717"
_ICON_TIMEOUT = "\u23f1"
_ICON_FIRE = "\U0001f525"


class _EngineEvent(Message):
    """Bridges engine events into Textual's message system."""

    def __init__(self, event: Event) -> None:
        self.event = event
        super().__init__()


class TuiEmitter(EventEmitter):
    """Posts engine events to a Textual app via thread-safe messaging."""

    def __init__(self, app: WatchApp) -> None:
        self._app = app

    def emit(self, event: Event) -> None:
        self._app.post_message(_EngineEvent(event))


class WatchApp(App[None]):
    """Live dashboard for monitoring a ralph run."""

    CSS = """
    Screen {
        layout: vertical;
    }

    #stats-bar {
        width: 100%;
        height: 3;
        border: solid $accent;
        padding: 0 1;
    }

    #progress-line {
        width: 100%;
        height: 1;
        padding: 0 1;
    }

    RichLog {
        width: 100%;
        height: 1fr;
        border: solid $surface;
        padding: 0 1;
    }
    """

    BINDINGS = [
        Binding("q", "quit", "Quit"),
        Binding("p", "toggle_pause", "Pause/Resume"),
    ]

    def __init__(
        self,
        ralph_name: str,
        max_iterations: int | None = None,
        on_pause: Any | None = None,
        on_resume: Any | None = None,
    ) -> None:
        super().__init__()
        self._ralph_name = ralph_name
        self._max_iterations = max_iterations
        self._on_pause = on_pause
        self._on_resume = on_resume

        # Tracking state
        self._iteration = 0
        self._completed = 0
        self._failed = 0
        self._timed_out = 0
        self._streak = 0
        self._best_streak = 0
        self._paused = False

    @property
    def _total(self) -> int:
        return self._completed + self._failed

    @property
    def _success_rate(self) -> str:
        if self._total == 0:
            return "-"
        pct = (self._completed / self._total) * 100
        return f"{pct:.0f}%"

    def compose(self) -> ComposeResult:
        yield Static(self._build_stats(), id="stats-bar")
        yield Static("", id="progress-line")
        yield RichLog(id="log", markup=True)
        yield Footer()

    def _build_stats(self) -> str:
        parts = [
            f"[bold]{self._ralph_name}[/bold]",
            f"Iteration [bold]{self._iteration}[/bold]",
        ]
        if self._max_iterations:
            parts[-1] += f" / {self._max_iterations}"

        parts.append(f"Success [bold]{self._success_rate}[/bold]")

        if self._streak >= 2:
            parts.append(f"{_ICON_FIRE} [bold]{self._streak}[/bold] streak")

        return "  |  ".join(parts)

    def _build_progress(self) -> str:
        if not self._max_iterations:
            return ""
        filled = self._iteration
        total = self._max_iterations
        bar_width = 20
        fill_count = min(int((filled / total) * bar_width), bar_width)
        empty_count = bar_width - fill_count
        bar = "\u2588" * fill_count + "\u2591" * empty_count
        return f"  [{bar}] {filled}/{total}"

    def _update_display(self) -> None:
        self.query_one("#stats-bar", Static).update(self._build_stats())
        self.query_one("#progress-line", Static).update(self._build_progress())

    def on__engine_event(self, message: _EngineEvent) -> None:
        event = message.event
        handler = self._event_handlers.get(event.type)
        if handler:
            handler(self, event.data)

    def _handle_run_started(self, data: dict[str, Any]) -> None:
        log = self.query_one(RichLog)
        info_parts = []
        timeout = data.get("timeout")
        if timeout and timeout > 0:
            info_parts.append(f"Timeout: {format_duration(timeout)}/iter")
        commands = data.get("commands", 0)
        if commands > 0:
            info_parts.append(f"{commands} command(s)")
        if info_parts:
            log.write(f"[dim]{' | '.join(info_parts)}[/dim]")
        log.write("[dim]Run started...[/dim]")

    def _handle_iteration_started(self, data: dict[str, Any]) -> None:
        self._iteration = data["iteration"]
        self._update_display()
        log = self.query_one(RichLog)
        header = f"\n[bold blue]\u2500\u2500 Iteration {self._iteration}"
        if self._max_iterations:
            header += f" / {self._max_iterations}"
        header += " \u2500\u2500[/bold blue]"
        log.write(header)

    def _handle_iteration_completed(self, data: dict[str, Any]) -> None:
        self._completed += 1
        self._streak += 1
        if self._streak > self._best_streak:
            self._best_streak = self._streak
        self._log_iteration_end(data, "green", _ICON_SUCCESS)
        self._update_display()

    def _handle_iteration_failed(self, data: dict[str, Any]) -> None:
        self._failed += 1
        self._streak = 0
        self._log_iteration_end(data, "red", _ICON_FAILURE)
        self._update_display()

    def _handle_iteration_timed_out(self, data: dict[str, Any]) -> None:
        self._failed += 1
        self._timed_out += 1
        self._streak = 0
        self._log_iteration_end(data, "yellow", _ICON_TIMEOUT)
        self._update_display()

    def _log_iteration_end(self, data: dict[str, Any], color: str, icon: str) -> None:
        log = self.query_one(RichLog)
        detail = data.get("detail", "")
        line = f"[{color}]{icon} Iteration {data['iteration']} {detail}[/{color}]"
        log.write(line)
        result_text = data.get("result_text")
        if result_text:
            log.write(f"  [dim]{result_text}[/dim]")
        if self._streak >= 2:
            log.write(f"  {_ICON_FIRE} [bold]{self._streak} streak![/bold]")

    def _handle_commands_completed(self, data: dict[str, Any]) -> None:
        count = data.get("count", 0)
        if count:
            log = self.query_one(RichLog)
            log.write(f"  [bold]Commands:[/bold] {count} ran")

    def _handle_log_message(self, data: dict[str, Any]) -> None:
        log = self.query_one(RichLog)
        msg = data.get("message", "")
        level = data.get("level", "info")
        if level == "error":
            log.write(f"[red]{msg}[/red]")
        else:
            log.write(f"[dim]{msg}[/dim]")

    def _handle_run_stopped(self, data: dict[str, Any]) -> None:
        log = self.query_one(RichLog)
        reason = data.get("reason", "")
        total = data.get("total", 0)
        completed = data.get("completed", 0)
        failed = data.get("failed", 0)
        timed_out = data.get("timed_out", 0)
        total_elapsed = data.get("total_elapsed", 0.0)

        log.write("")
        if reason == STOP_COMPLETED:
            non_timeout = failed - timed_out
            parts = [f"{completed} succeeded"]
            if non_timeout:
                parts.append(f"{non_timeout} failed")
            if timed_out:
                parts.append(f"{timed_out} timed out")
            detail = ", ".join(parts)
            log.write(
                f"[green bold]Done: {total} iteration(s) \u2014 {detail}[/green bold]"
            )
        else:
            log.write(f"[yellow]Run stopped ({reason})[/yellow]")

        if total_elapsed > 0:
            log.write(f"[dim]Total time: {format_duration(total_elapsed)}[/dim]")
        if self._best_streak >= 2:
            log.write(f"[dim]Best streak: {_ICON_FIRE} {self._best_streak}[/dim]")

        log.write("")
        log.write("[dim]Press q to exit.[/dim]")

    _event_handlers: dict[EventType, Any] = {
        EventType.RUN_STARTED: _handle_run_started,
        EventType.ITERATION_STARTED: _handle_iteration_started,
        EventType.ITERATION_COMPLETED: _handle_iteration_completed,
        EventType.ITERATION_FAILED: _handle_iteration_failed,
        EventType.ITERATION_TIMED_OUT: _handle_iteration_timed_out,
        EventType.COMMANDS_COMPLETED: _handle_commands_completed,
        EventType.LOG_MESSAGE: _handle_log_message,
        EventType.RUN_STOPPED: _handle_run_stopped,
    }

    def action_toggle_pause(self) -> None:
        if self._paused:
            self._paused = False
            if self._on_resume:
                self._on_resume()
            log = self.query_one(RichLog)
            log.write("[dim]Resumed[/dim]")
        else:
            self._paused = True
            if self._on_pause:
                self._on_pause()
            log = self.query_one(RichLog)
            log.write("[yellow]Paused \u2014 press p to resume[/yellow]")
