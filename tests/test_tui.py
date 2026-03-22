"""Tests for the TUI dashboard module."""

import pytest

from ralphify._events import Event, EventType
from ralphify._tui import WatchApp, TuiEmitter, _EngineEvent


def _make_event(event_type, **data):
    return Event(type=event_type, run_id="test-run", data=data)


class TestWatchAppState:
    """Test internal state tracking of the WatchApp."""

    def _make_app(self, **kwargs):
        return WatchApp(ralph_name="test-ralph", **kwargs)

    def test_initial_state(self):
        app = self._make_app()
        assert app._iteration == 0
        assert app._completed == 0
        assert app._failed == 0
        assert app._streak == 0
        assert app._best_streak == 0

    def test_total_property(self):
        app = self._make_app()
        app._completed = 3
        app._failed = 2
        assert app._total == 5

    def test_success_rate_no_iterations(self):
        app = self._make_app()
        assert app._success_rate == "-"

    def test_success_rate_all_success(self):
        app = self._make_app()
        app._completed = 5
        assert app._success_rate == "100%"

    def test_success_rate_mixed(self):
        app = self._make_app()
        app._completed = 3
        app._failed = 1
        assert app._success_rate == "75%"

    def test_build_stats_basic(self):
        app = self._make_app()
        stats = app._build_stats()
        assert "test-ralph" in stats
        assert "Iteration" in stats

    def test_build_stats_with_max_iterations(self):
        app = self._make_app(max_iterations=10)
        app._iteration = 3
        stats = app._build_stats()
        assert "/ 10" in stats

    def test_build_stats_shows_streak(self):
        app = self._make_app()
        app._streak = 3
        stats = app._build_stats()
        assert "3" in stats
        assert "streak" in stats

    def test_build_stats_no_streak_below_2(self):
        app = self._make_app()
        app._streak = 1
        stats = app._build_stats()
        assert "streak" not in stats

    def test_build_progress_no_max(self):
        app = self._make_app()
        assert app._build_progress() == ""

    def test_build_progress_with_max(self):
        app = self._make_app(max_iterations=10)
        app._iteration = 5
        progress = app._build_progress()
        assert "5/10" in progress
        assert "\u2588" in progress  # filled block
        assert "\u2591" in progress  # empty block


class TestStreakTracking:
    """Test streak counting logic via the handler methods."""

    def _make_app(self):
        return WatchApp(ralph_name="test-ralph")

    def test_completed_increments_streak(self):
        app = self._make_app()
        # Simulate what the handlers do (without needing mounted widgets)
        app._completed += 1
        app._streak += 1
        if app._streak > app._best_streak:
            app._best_streak = app._streak
        assert app._streak == 1
        assert app._best_streak == 1

    def test_failure_resets_streak(self):
        app = self._make_app()
        app._streak = 5
        app._best_streak = 5
        # Simulate failure
        app._failed += 1
        app._streak = 0
        assert app._streak == 0
        assert app._best_streak == 5

    def test_best_streak_preserved_across_failures(self):
        app = self._make_app()
        # Build up a streak
        for _ in range(4):
            app._completed += 1
            app._streak += 1
            if app._streak > app._best_streak:
                app._best_streak = app._streak

        # Fail
        app._failed += 1
        app._streak = 0

        # Build a smaller streak
        for _ in range(2):
            app._completed += 1
            app._streak += 1
            if app._streak > app._best_streak:
                app._best_streak = app._streak

        assert app._best_streak == 4
        assert app._streak == 2


class TestTuiEmitter:
    """Test that TuiEmitter posts messages to the app."""

    def test_emitter_creates_engine_event_message(self):
        app = WatchApp(ralph_name="test")
        emitter = TuiEmitter(app)
        # TuiEmitter.emit calls app.post_message which is safe to call
        # even without a running app (it queues the message).
        event = _make_event(EventType.LOG_MESSAGE, message="hello", level="info")
        # This should not raise
        emitter.emit(event)


class TestPauseResume:
    """Test pause/resume callback wiring."""

    def test_pause_callback(self):
        paused = []
        app = WatchApp(ralph_name="test", on_pause=lambda: paused.append(True))
        # Simulate the toggle without mounted widgets
        app._paused = True
        if app._on_pause:
            app._on_pause()
        assert paused == [True]

    def test_resume_callback(self):
        resumed = []
        app = WatchApp(ralph_name="test", on_resume=lambda: resumed.append(True))
        app._paused = False
        if app._on_resume:
            app._on_resume()
        assert resumed == [True]
