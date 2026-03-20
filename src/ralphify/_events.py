"""Event types and emitter protocol for the run loop.

The run engine emits structured events during execution so that different
frontends can observe progress without coupling to the engine internals.
"""

from __future__ import annotations

import queue
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Protocol, runtime_checkable


class EventType(Enum):
    """All event types emitted by the run loop.

    Events fall into three groups:

    **Run lifecycle** — emitted once per run start/stop/pause/resume:
    ``RUN_STARTED``, ``RUN_STOPPED``, ``RUN_PAUSED``, ``RUN_RESUMED``.

    **Iteration lifecycle** — emitted once per iteration:
    ``ITERATION_STARTED``, ``ITERATION_COMPLETED``, ``ITERATION_FAILED``,
    ``ITERATION_TIMED_OUT``.

    **Commands** — emitted during command execution:
    ``COMMANDS_STARTED``, ``COMMANDS_COMPLETED``.
    """

    # ── Run lifecycle ───────────────────────────────────────────
    RUN_STARTED = "run_started"
    RUN_STOPPED = "run_stopped"
    RUN_PAUSED = "run_paused"
    RUN_RESUMED = "run_resumed"

    # ── Iteration lifecycle ─────────────────────────────────────
    ITERATION_STARTED = "iteration_started"
    ITERATION_COMPLETED = "iteration_completed"
    ITERATION_FAILED = "iteration_failed"
    ITERATION_TIMED_OUT = "iteration_timed_out"

    # ── Commands ────────────────────────────────────────────────
    COMMANDS_STARTED = "commands_started"
    COMMANDS_COMPLETED = "commands_completed"

    # ── Prompt assembly ─────────────────────────────────────────
    PROMPT_ASSEMBLED = "prompt_assembled"

    # ── Agent activity (live streaming) ─────────────────────────
    AGENT_ACTIVITY = "agent_activity"

    # ── Other ───────────────────────────────────────────────────
    LOG_MESSAGE = "log_message"


@dataclass
class Event:
    """A structured event emitted by the run loop."""

    type: EventType
    run_id: str
    data: dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> dict[str, Any]:
        """Serialize this event to a JSON-compatible dict."""
        return {
            "type": self.type.value,
            "run_id": self.run_id,
            "timestamp": self.timestamp.isoformat(),
            "data": self.data,
        }


@runtime_checkable
class EventEmitter(Protocol):
    """Protocol for objects that receive run-loop events."""

    def emit(self, event: Event) -> None: ...


class NullEmitter:
    """Discards all events silently."""

    def emit(self, event: Event) -> None:
        pass


class QueueEmitter:
    """Pushes events into a :class:`queue.Queue` for async consumption."""

    def __init__(self, q: queue.Queue[Event] | None = None) -> None:
        self.queue: queue.Queue[Event] = q or queue.Queue()

    def emit(self, event: Event) -> None:
        self.queue.put(event)


class FanoutEmitter:
    """Broadcasts events to multiple emitters."""

    def __init__(self, emitters: list[EventEmitter]) -> None:
        self._emitters = emitters

    def emit(self, event: Event) -> None:
        for e in self._emitters:
            e.emit(event)
