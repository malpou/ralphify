"""Rich console renderer for run-loop events.

The ``ConsoleEmitter`` translates structured :class:`Event` objects into
Rich-formatted terminal output.
"""

from __future__ import annotations

import time
from collections.abc import Callable
from functools import partial

from rich.console import Console, ConsoleOptions, RenderResult
from rich.live import Live
from rich.markup import escape as escape_markup
from rich.panel import Panel
from rich.spinner import Spinner
from rich.text import Text

from ralphify._events import (
    LOG_ERROR,
    STOP_COMPLETED,
    CommandsCompletedData,
    Event,
    EventType,
    IterationEndedData,
    IterationStartedData,
    LogMessageData,
    RunStartedData,
    RunStoppedData,
)
from ralphify._output import format_duration

_ICON_SUCCESS = "\u2713"
_ICON_FAILURE = "\u2717"
_ICON_TIMEOUT = "\u23f1"
_ICON_ARROW = "\u2192"
_ICON_DASH = "\u2014"
_ICON_FIRE = "\U0001f525"

_LIVE_REFRESH_RATE = 4  # Hz — how often the spinner redraws


class _IterationSpinner:
    """Rich renderable that shows a spinner with elapsed time."""

    def __init__(self) -> None:
        self._spinner = Spinner("dots")
        self._start = time.monotonic()

    def __rich_console__(self, console: Console, options: ConsoleOptions) -> RenderResult:
        elapsed = time.monotonic() - self._start
        text = Text(f" {format_duration(elapsed)}", style="dim")
        yield self._spinner
        yield text


class ConsoleEmitter:
    """Renders engine events to the Rich console."""

    def __init__(self, console: Console) -> None:
        self._console = console
        self._live: Live | None = None
        self._max_iterations: int | None = None
        self._streak: int = 0
        self._best_streak: int = 0
        self._handlers: dict[EventType, Callable[..., None]] = {
            EventType.RUN_STARTED: self._on_run_started,
            EventType.ITERATION_STARTED: self._on_iteration_started,
            EventType.ITERATION_COMPLETED: partial(self._on_iteration_ended, color="green", icon=_ICON_SUCCESS, success=True),
            EventType.ITERATION_FAILED: partial(self._on_iteration_ended, color="red", icon=_ICON_FAILURE, success=False),
            EventType.ITERATION_TIMED_OUT: partial(self._on_iteration_ended, color="yellow", icon=_ICON_TIMEOUT, success=False),
            EventType.COMMANDS_COMPLETED: self._on_commands_completed,
            EventType.LOG_MESSAGE: self._on_log_message,
            EventType.RUN_STOPPED: self._on_run_stopped,
        }

    def emit(self, event: Event) -> None:
        handler = self._handlers.get(event.type)
        if handler is not None:
            handler(event.data)

    def _on_run_started(self, data: RunStartedData) -> None:
        self._max_iterations = data.get("max_iterations")
        timeout = data["timeout"]
        if timeout is not None and timeout > 0:
            self._console.print(f"[dim]Timeout: {format_duration(timeout)} per iteration[/dim]")
        command_count = data["commands"]
        if command_count > 0:
            self._console.print(f"[dim]Commands: {command_count} configured[/dim]")

    def _start_live(self) -> None:
        spinner = _IterationSpinner()
        self._live = Live(
            spinner,
            console=self._console,
            transient=True,
            refresh_per_second=_LIVE_REFRESH_RATE,
        )
        self._live.start()

    def _stop_live(self) -> None:
        if self._live is not None:
            self._live.stop()
            self._live = None

    def _on_iteration_started(self, data: IterationStartedData) -> None:
        iteration = data["iteration"]
        header = f"\n[bold blue]{_ICON_DASH}{_ICON_DASH} Iteration {iteration}"
        if self._max_iterations:
            header += f" / {self._max_iterations}"
        header += f" {_ICON_DASH}{_ICON_DASH}[/bold blue]"
        self._console.print(header)
        self._start_live()

    def _on_iteration_ended(self, data: IterationEndedData, color: str, icon: str, success: bool) -> None:
        self._stop_live()

        if success:
            self._streak += 1
            if self._streak > self._best_streak:
                self._best_streak = self._streak
        else:
            self._streak = 0

        iteration = data["iteration"]
        detail = data["detail"]
        status_msg = f"[{color}]{icon} Iteration {iteration} {detail}"
        log_file = data["log_file"]
        if log_file:
            status_msg += f" {_ICON_ARROW}\n{escape_markup(log_file)}"
        status_msg += f"[/{color}]"
        self._console.print(status_msg)
        result_text = data["result_text"]
        if result_text:
            self._console.print(f"  [dim]{escape_markup(result_text)}[/dim]")
        if self._streak >= 2:
            self._console.print(f"  {_ICON_FIRE} [bold]{self._streak} streak[/bold]")

    def _on_commands_completed(self, data: CommandsCompletedData) -> None:
        count = data["count"]
        if count:
            self._console.print(f"  [bold]Commands:[/bold] {count} ran")

    def _on_log_message(self, data: LogMessageData) -> None:
        msg = escape_markup(data["message"])
        level = data["level"]
        if level == LOG_ERROR:
            self._console.print(f"[red]{msg}[/red]")
            tb = data.get("traceback")
            if tb:
                self._console.print(f"[dim]{escape_markup(tb)}[/dim]")
        else:
            self._console.print(f"[dim]{msg}[/dim]")

    def _on_run_stopped(self, data: RunStoppedData) -> None:
        self._stop_live()
        if data["reason"] != STOP_COMPLETED:
            return

        total = data["total"]
        completed = data["completed"]
        failed = data["failed"]
        timed_out_count = data["timed_out"]
        total_elapsed = data.get("total_elapsed", 0.0)

        # timed_out is a subset of failed — show non-timeout failures
        # and timeouts as separate categories for clarity.
        non_timeout_failures = failed - timed_out_count
        parts = [f"{completed} succeeded"]
        if non_timeout_failures:
            parts.append(f"{non_timeout_failures} failed")
        if timed_out_count:
            parts.append(f"{timed_out_count} timed out")
        detail = ", ".join(parts)

        # Build summary lines
        lines = [f"[bold]{total} iteration(s)[/bold] {_ICON_DASH} {detail}"]
        if total > 0:
            rate = (completed / total) * 100
            lines.append(f"Success rate: [bold]{rate:.0f}%[/bold]")
        if self._best_streak >= 2:
            lines.append(f"Best streak: {_ICON_FIRE} [bold]{self._best_streak}[/bold]")
        if total_elapsed > 0:
            lines.append(f"Total time: [bold]{format_duration(total_elapsed)}[/bold]")

        summary = "\n".join(lines)
        self._console.print()
        self._console.print(Panel(summary, title="[green]Done[/green]", border_style="green"))
