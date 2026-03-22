# Plan: Game-feel TUI — `ralph watch`

## Summary

Add a `ralph watch` command that opens a Textual TUI dashboard for monitoring ralph runs. Shows real-time iteration progress, streak counter, success rate, elapsed time, and last iteration details. Connects to the existing event emitter system. This is the MVP for issue #15 — XP/achievements deferred to a follow-up.

## Files to modify

- `pyproject.toml` — Add `textual` as a runtime dependency
- `src/ralphify/_tui.py` — New module: Textual app with dashboard layout (iteration progress, streak, stats, last iteration detail, git log panel)
- `src/ralphify/_events.py` — Add `total_elapsed` field to `RunStoppedData`
- `src/ralphify/engine.py` — Compute and include `total_elapsed` in the `RUN_STOPPED` event
- `src/ralphify/cli.py` — Add `ralph watch` command that starts the TUI, wires events to it, and runs the loop
- `tests/test_tui.py` — New: tests for TUI app (widget rendering, event handling)
- `tests/test_engine.py` — Update `RunStoppedData` assertions for new field
- `docs/reference/cli.md` — Document `ralph watch` command

## Steps

- [x] 1. Add `textual` dependency to `pyproject.toml` and run `uv lock`
- [x] 2. Add `total_elapsed: float` field to `RunStoppedData` in `_events.py` and update `engine.py` to compute and emit it; fix any broken tests
- [x] 3. Create `_tui.py` with a Textual App class: header showing ralph name, iteration counter with progress bar, streak counter, success rate, elapsed time, and a scrollable log of iteration results
- [x] 4. Wire the TUI to the event system: implement an emitter that posts events to the Textual app's message queue, updating widgets reactively
- [x] 5. Add `ralph watch` command to `cli.py` that starts the run loop in a background thread with the TUI emitter, and runs the Textual app in the foreground
- [x] 6. Add tests for the TUI module and update existing tests for `RunStoppedData` changes
- [x] 7. Add documentation for `ralph watch` in the CLI reference docs
- [x] 8. Also enhance the existing `ConsoleEmitter` with streak counter and richer summary panel (benefits `ralph run` users too)

## Acceptance criteria

- `uv run pytest` passes with zero failures
- `ralph watch <path>` opens a TUI dashboard that updates in real-time as iterations run
- Dashboard shows: current iteration / max, streak counter, success rate, elapsed time
- Iteration results appear in a scrollable log with color-coded status
- Ctrl+C or `q` cleanly exits the TUI
- `ralph run` also shows streak counter and improved summary (step 8)
