"""Minimal HTTP server for the ralphify dashboard.

Serves a single-page dashboard UI and streams run events via Server-Sent
Events (SSE).  Uses only the stdlib ``http.server`` module — no extra
dependencies.
"""

from __future__ import annotations

import json
import queue
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from importlib import resources
from typing import TYPE_CHECKING

from ralphify._events import Event, EventEmitter, QueueEmitter
from ralphify._run_types import RunStatus

if TYPE_CHECKING:
    from ralphify.manager import RunManager


class _DashboardEmitter:
    """Broadcasts events to all connected SSE clients.

    Implements :class:`EventEmitter` so it can be registered as a listener
    on each :class:`ManagedRun`.  Incoming events are fanned out to every
    connected client's individual queue.
    """

    def __init__(self) -> None:
        self._clients: list[queue.Queue[Event]] = []
        self._lock = threading.Lock()

    def subscribe(self) -> queue.Queue[Event]:
        q: queue.Queue[Event] = queue.Queue()
        with self._lock:
            self._clients.append(q)
        return q

    def unsubscribe(self, q: queue.Queue[Event]) -> None:
        with self._lock:
            try:
                self._clients.remove(q)
            except ValueError:
                pass

    def emit(self, event: Event) -> None:
        with self._lock:
            for q in self._clients:
                q.put(event)


class _DashboardHandler(BaseHTTPRequestHandler):
    """HTTP request handler for dashboard routes."""

    manager: RunManager
    emitter: _DashboardEmitter

    def log_message(self, format: str, *args: object) -> None:  # noqa: A002
        # Silence default stderr logging.
        pass

    def do_GET(self) -> None:  # noqa: N802
        if self.path == "/" or self.path == "/index.html":
            self._serve_html()
        elif self.path == "/events":
            self._serve_sse()
        elif self.path == "/api/runs":
            self._serve_runs()
        else:
            self.send_error(404)

    def _serve_html(self) -> None:
        html = resources.files("ralphify").joinpath(
            "_dashboard_static/index.html",
        ).read_text(encoding="utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write(html.encode())

    def _serve_runs(self) -> None:
        runs = []
        for managed in self.manager.list_runs():
            s = managed.state
            runs.append({
                "run_id": s.run_id,
                "status": s.status.value,
                "iteration": s.iteration,
                "completed": s.completed,
                "failed": s.failed,
                "timed_out": s.timed_out,
                "ralph_name": managed.config.ralph_dir.name,
            })
        payload = json.dumps(runs).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(payload)

    def _serve_sse(self) -> None:
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream")
        self.send_header("Cache-Control", "no-cache")
        self.send_header("Connection", "keep-alive")
        self.end_headers()

        client_q = self.emitter.subscribe()
        try:
            while True:
                try:
                    event = client_q.get(timeout=15)
                except queue.Empty:
                    # Send keepalive comment to prevent connection timeout.
                    self.wfile.write(b": keepalive\n\n")
                    self.wfile.flush()
                    continue

                data = json.dumps(event.to_dict())
                self.wfile.write(f"event: {event.type.value}\n".encode())
                self.wfile.write(f"data: {data}\n\n".encode())
                self.wfile.flush()
        except (BrokenPipeError, ConnectionResetError, OSError):
            pass
        finally:
            self.emitter.unsubscribe(client_q)


def start_dashboard(
    manager: RunManager,
    *,
    port: int = 8420,
    open_browser: bool = True,
) -> HTTPServer:
    """Start the dashboard HTTP server in a daemon thread.

    Returns the :class:`HTTPServer` instance so the caller can call
    ``server.shutdown()`` to stop it.
    """
    emitter = _DashboardEmitter()

    # Attach the emitter to all existing runs.
    for managed in manager.list_runs():
        managed.add_listener(emitter)

    # Monkey-patch create_run so future runs also get the emitter.
    _original_create = manager.create_run

    def _patched_create(config):  # type: ignore[no-untyped-def]
        managed = _original_create(config)
        managed.add_listener(emitter)
        return managed

    manager.create_run = _patched_create  # type: ignore[method-assign]

    # Create a handler subclass that closes over the manager and emitter.
    # Setting attributes on a functools.partial does not propagate to
    # handler instances, so a dynamic subclass is the simplest approach.
    handler_cls = type(
        "_BoundHandler",
        (_DashboardHandler,),
        {"manager": manager, "emitter": emitter},
    )

    server = HTTPServer(("127.0.0.1", port), handler_cls)
    thread = threading.Thread(target=server.serve_forever, daemon=True, name="dashboard")
    thread.start()

    if open_browser:
        import webbrowser

        webbrowser.open(f"http://127.0.0.1:{port}")

    return server
