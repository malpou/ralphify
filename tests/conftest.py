"""Shared pytest fixtures for ralphify tests."""

import pytest


@pytest.fixture(autouse=True)
def _disable_streaming(monkeypatch):
    """Disable the Popen-based streaming path in all tests."""
    monkeypatch.setattr("ralphify._agent._supports_stream_json", lambda cmd: False)
