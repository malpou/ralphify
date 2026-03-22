# Fleet Todo App

A multi-ralph example that simulates a software team building a todo app. Three ralphs — PM, developer, and QA — work together using a shared kanban board and spec files to move features from idea to accepted.

## How it works

The fleet follows a pipeline:

1. **PM** reads the inbox, writes specs, and adds tasks to the board
2. **Dev** picks up ready tasks, implements them, and marks them done
3. **QA** verifies done tasks against specs and either accepts or rejects them

All coordination happens through files:

- `INBOX.md` — raw feature requests
- `TODO.md` — kanban board with Ready / In Progress / Done / Accepted columns
- `specs/<slug>.md` — detailed specs with acceptance criteria

Each ralph reads the current state of these files via `commands` in its frontmatter, makes a decision, and updates the files. No direct communication between ralphs — just shared state on disk.

## Directory structure

```
fleet-todo-app/
├── fleet.yml            # Fleet configuration (roles, dependencies, settings)
├── INBOX.md             # Seed feature requests
├── TODO.md              # Kanban board
├── specs/               # Specs written by PM, read by dev and QA
└── ralphs/
    ├── pm.md            # PM ralph — triages inbox, writes specs, reviews work
    ├── dev.md           # Dev ralph — implements tasks, writes tests
    └── qa.md            # QA ralph — verifies work against specs
```

## Running the ralphs

Fleet orchestration (`ralph fleet`) is not yet implemented. For now, run each ralph individually in separate terminals:

```bash
cd examples/fleet-todo-app

# Terminal 1 — start the PM
ralph run ralphs/pm.md

# Terminal 2 — start the developer (after PM has created some specs)
ralph run ralphs/dev.md

# Terminal 3 — start QA (after dev has completed some work)
ralph run ralphs/qa.md
```

When fleet support lands, you'll be able to run the whole team with:

```bash
ralph fleet fleet.yml
```

The `fleet.yml` defines the dependency order (`dev` depends on `pm`, `qa` depends on `dev`), concurrency limits, and stagger timing so ralphs don't step on each other.

## The workflow

Starting from the seed inbox, a typical run looks like:

1. PM reads `INBOX.md`, picks "Add POST /todos endpoint", writes `specs/create-todo.md`, adds it to `## Ready` on the board
2. Dev sees the ready task, reads the spec, implements it, writes tests, moves it to `## Done`
3. QA picks up the done task, runs tests, checks acceptance criteria, moves it to `## Accepted`
4. PM sees nothing in inbox or done — goes idle. Dev picks the next ready task. The cycle continues.

Each ralph processes one task per iteration and goes idle when there's nothing to do. The loop harness restarts them with fresh state each time.

## Customizing

This example uses `claude` as the agent, but you can swap in any agent that accepts piped input. Edit the `agent` field in each ralph's frontmatter:

```yaml
agent: aider --yes-always
```

The board format and file conventions are just that — conventions. Adapt them to match your team's workflow.
