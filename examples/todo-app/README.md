# Lifecycle example: todo app

A multi-role example demonstrating three ralphs working together through a
software development lifecycle to build a simple Node.js todo CLI app.

- **pm** — Project manager: triages the inbox, writes specs, manages the kanban board
- **dev** — Developer: picks up ready tasks, implements features, runs tests
- **qa** — QA: verifies completed work against specs, accepts or rejects

## How it works

The ralphs share state through plain files:

- `INBOX.md` — Pre-seeded feature requests (PM reads these)
- `TODO.md` — Kanban board with Backlog / In Progress / Done columns
- `specs/` — Detailed specs written by PM, read by dev and QA
- `package.json` — The Node.js project that dev builds into

Run each ralph individually with `ralph run`. They communicate through the
shared files — no fleet features required.

## Usage

```bash
# Run the PM ralph to triage inbox and create specs:
ralph run examples/todo-app/ralphs/pm

# Run the dev ralph to implement a task:
ralph run examples/todo-app/ralphs/dev

# Run the QA ralph to verify completed work:
ralph run examples/todo-app/ralphs/qa
```

Run them in order (PM first, then dev, then QA) or run PM a few times to
build up the board before letting dev work through tasks.

## Customization

- Swap `claude -p` for your preferred agent command
- Add more feature requests to `INBOX.md`
- Adjust the spec format in the PM ralph prompt
