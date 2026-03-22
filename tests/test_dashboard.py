"""Tests for the dashboard HTTP server and SSE streaming."""

import json
import queue
import threading
import time
import urllib.request

import pytest

from helpers import make_config

from ralphify._dashboard import _DashboardEmitter, start_dashboard
from ralphify._events import Event, EventType
from ralphify._run_types import RunStatus
from ralphify.manager import RunManager


@pytest.fixture()
def manager(tmp_path):
    return RunManager()


@pytest.fixture()
def dashboard(manager):
    """Start a dashboard server on an ephemeral port and tear it down after the test."""
    server = start_dashboard(manager, port=0, open_browser=False)
    port = server.server_address[1]
    yield server, port
    server.shutdown()


def _get(port, path):
    """Make a GET request and return (status, headers, body)."""
    url = f"http://127.0.0.1:{port}{path}"
    req = urllib.request.Request(url)
    with urllib.request.urlopen(req, timeout=5) as resp:
        return resp.status, dict(resp.headers), resp.read()


class TestDashboardEmitter:
    def test_subscribe_returns_queue(self):
        emitter = _DashboardEmitter()
        q = emitter.subscribe()
        assert isinstance(q, queue.Queue)

    def test_emit_fans_out_to_subscribers(self):
        emitter = _DashboardEmitter()
        q1 = emitter.subscribe()
        q2 = emitter.subscribe()

        event = Event(type=EventType.RUN_STARTED, run_id="r1", data={})
        emitter.emit(event)

        assert q1.get_nowait() is event
        assert q2.get_nowait() is event

    def test_unsubscribe_removes_client(self):
        emitter = _DashboardEmitter()
        q = emitter.subscribe()
        emitter.unsubscribe(q)

        event = Event(type=EventType.RUN_STARTED, run_id="r1", data={})
        emitter.emit(event)

        assert q.empty()

    def test_unsubscribe_nonexistent_is_noop(self):
        emitter = _DashboardEmitter()
        q = queue.Queue()
        emitter.unsubscribe(q)  # should not raise


class TestDashboardServer:
    def test_serves_html_at_root(self, dashboard):
        _server, port = dashboard
        status, headers, body = _get(port, "/")
        assert status == 200
        assert "text/html" in headers["Content-Type"]
        assert b"<html" in body.lower()

    def test_serves_html_at_index(self, dashboard):
        _server, port = dashboard
        status, _headers, _body = _get(port, "/index.html")
        assert status == 200

    def test_returns_404_for_unknown_path(self, dashboard):
        _server, port = dashboard
        with pytest.raises(urllib.error.HTTPError) as exc_info:
            _get(port, "/nonexistent")
        assert exc_info.value.code == 404

    def test_api_runs_returns_empty_list(self, dashboard):
        _server, port = dashboard
        status, headers, body = _get(port, "/api/runs")
        assert status == 200
        assert "application/json" in headers["Content-Type"]
        assert json.loads(body) == []

    def test_api_runs_lists_created_runs(self, dashboard, manager, tmp_path):
        _server, port = dashboard
        config = make_config(tmp_path)
        manager.create_run(config)

        status, _headers, body = _get(port, "/api/runs")
        runs = json.loads(body)
        assert len(runs) == 1
        assert runs[0]["status"] == RunStatus.PENDING.value
        assert runs[0]["ralph_name"] == "my-ralph"


class TestDashboardSSE:
    def test_sse_endpoint_returns_event_stream(self, dashboard):
        _server, port = dashboard
        url = f"http://127.0.0.1:{port}/events"
        req = urllib.request.Request(url)
        resp = urllib.request.urlopen(req, timeout=5)
        assert "text/event-stream" in resp.headers["Content-Type"]
        resp.close()

    def test_sse_receives_emitted_events(self, dashboard, manager):
        server, port = dashboard

        # Get the emitter from the handler class
        handler_cls = server.RequestHandlerClass
        emitter = handler_cls.emitter

        url = f"http://127.0.0.1:{port}/events"
        req = urllib.request.Request(url)
        resp = urllib.request.urlopen(req, timeout=5)

        # Emit an event after connection is established
        time.sleep(0.1)
        event = Event(type=EventType.RUN_STARTED, run_id="test-123", data={"ralph_name": "foo"})
        emitter.emit(event)

        # Read SSE lines
        lines = []
        deadline = time.monotonic() + 3
        while time.monotonic() < deadline:
            line = resp.readline().decode()
            lines.append(line)
            if line == "\n" and any("data:" in l for l in lines):
                break

        resp.close()

        full = "".join(lines)
        assert "event: run_started" in full
        assert "test-123" in full


class TestDashboardNewRunsGetEmitter:
    def test_runs_created_after_dashboard_get_emitter(self, dashboard, manager, tmp_path):
        """Runs created after start_dashboard also get the dashboard emitter attached."""
        server, port = dashboard
        handler_cls = server.RequestHandlerClass
        emitter = handler_cls.emitter

        config = make_config(tmp_path)
        managed = manager.create_run(config)

        # The managed run should have the dashboard emitter in its extra emitters
        assert emitter in managed._extra_emitters
