# dashboard-poc — Visual dashboard for ralphify (#15)

## Summary

Add a `ralph dashboard` CLI command that launches a local web server serving a real-time dashboard UI. The dashboard connects to the existing event system via `RunManager` and displays live run status, iteration history, and terminal output in a cyberpunk-styled interface matching the reference design (`pm/dashboard-ref.html`).

This is a **proof-of-concept** — the draft PR will include a POC disclaimer.

## Architecture

- New module `_dashboard.py` — HTTP server (stdlib `http.server` + threading) serving a single-page HTML dashboard
- New module `_dashboard_ws.py` — Simple WebSocket server for real-time event streaming (using stdlib or minimal approach)
- Actually, simpler: use **SSE (Server-Sent Events)** over HTTP — no extra deps needed
- The dashboard HTML is embedded as a string or served from a `_dashboard_static/` directory
- `cli.py` gets a new `dashboard` command that starts the server and optionally opens a browser
- The dashboard connects to running ralphs via `RunManager` event queues

## Files to modify

- `src/ralphify/cli.py` — Add `ralph dashboard` command
- `src/ralphify/_dashboard.py` — New: HTTP server + SSE endpoint + static HTML
- `src/ralphify/_dashboard_static/index.html` — New: Dashboard HTML (based on reference design)
- `tests/test_dashboard.py` — New: Tests for dashboard server
- `docs/changelog.md` — Add entry

## Steps

- [ ] 1. Create `_dashboard.py` with a minimal HTTP server that serves static HTML and exposes an SSE `/events` endpoint that streams RunManager events as JSON
- [ ] 2. Create `_dashboard_static/index.html` — the dashboard UI adapted from the reference design, connecting to the SSE endpoint for live updates
- [ ] 3. Add `ralph dashboard` command to `cli.py` that starts the dashboard server (with `--port` option, default 8420)
- [ ] 4. Write tests for the dashboard server (server starts, serves HTML, SSE endpoint streams events)
- [ ] 5. Add changelog entry and create draft PR with POC disclaimer

## Acceptance criteria

- `ralph dashboard` starts a local web server and serves the dashboard UI
- The dashboard displays live run events via SSE when ralphs are running
- All existing tests still pass
- Draft PR includes a clear POC disclaimer
- No new runtime dependencies (uses stdlib http.server)
