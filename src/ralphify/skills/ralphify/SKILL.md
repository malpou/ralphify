---
name: ralphify
description: Learn how to use ralphify — the framework for running AI coding agents in autonomous loops
argument-hint: ""
disable-model-invocation: true
---

You have access to **ralphify**, a CLI tool that runs AI coding agents in autonomous loops. Use this reference to create, configure, and run ralphs.

## What is ralphify?

Ralphify pipes prompts to AI coding agents in a loop. Each iteration: run commands to capture fresh data, resolve placeholders in the prompt, pipe the assembled prompt to the agent, wait for the agent to finish, then repeat. The agent gets fresh context every iteration — progress lives in the code and git history.

## Installation

```bash
uv tool install ralphify   # recommended
pipx install ralphify      # alternative
pip install ralphify        # fallback
```

## CLI commands

### `ralph run` — start the loop

```bash
ralph run my-ralph                    # Run forever (Ctrl+C to stop)
ralph run my-ralph -n 5               # Run 5 iterations
ralph run my-ralph --stop-on-error    # Stop if agent exits non-zero or times out
ralph run my-ralph --delay 10         # Wait 10s between iterations
ralph run my-ralph --timeout 300      # Kill agent after 5 min per iteration
ralph run my-ralph --log-dir logs     # Save iteration output to log files
ralph run my-ralph --dir ./src        # Pass user arguments
```

| Option | Short | Default | Description |
|---|---|---|---|
| `PATH` | | (required) | Path to ralph directory or RALPH.md file |
| `-n` | | unlimited | Max iterations |
| `--stop-on-error` | `-s` | off | Stop on agent non-zero exit or timeout |
| `--delay` | `-d` | `0` | Seconds between iterations |
| `--timeout` | `-t` | none | Max seconds per iteration |
| `--log-dir` | `-l` | none | Directory for log files |

### `ralph init` — scaffold from template

```bash
ralph init my-task      # Creates my-task/RALPH.md with a starter template
ralph init              # Creates RALPH.md in current directory
```

### `ralph new` — AI-guided creation

```bash
ralph new               # Interactive AI-guided ralph creation
ralph new my-task       # Start with name pre-filled
```

## What is a ralph?

A ralph is a directory containing a `RALPH.md` file. That's it.

```
my-ralph/
├── RALPH.md              # Prompt + configuration (required)
├── check-coverage.sh     # Supporting script (optional)
└── data.json             # Any supporting file (optional)
```

## RALPH.md format

YAML frontmatter for configuration, then a markdown body for the prompt:

```markdown
---
agent: claude -p --dangerously-skip-permissions
commands:
  - name: tests
    run: uv run pytest -x
  - name: git-log
    run: git log --oneline -10
args: [dir, focus]
---

You are an autonomous coding agent running in a loop.
Each iteration starts with fresh context. Progress lives in code and git.

## Recent changes

{{ commands.git-log }}

## Test results

{{ commands.tests }}

Fix any failing tests before starting new work.

## Task

Work on files in {{ args.dir }}. Focus on {{ args.focus }}.
```

### Frontmatter fields

| Field | Type | Required | Description |
|---|---|---|---|
| `agent` | string | yes | Full agent command (prompt piped via stdin) |
| `commands` | list | no | Commands to run each iteration |
| `args` | list | no | Declared argument names for `{{ args.<name> }}` |
| `credit` | bool | no | Append co-author trailer instruction (default: `true`) |

### Command fields

| Field | Type | Default | Description |
|---|---|---|---|
| `name` | string | required | Identifier for `{{ commands.<name> }}` placeholder |
| `run` | string | required | Command to execute. `./` paths run from ralph dir; others from project root |
| `timeout` | number | `60` | Max seconds before killed |

Commands are parsed with `shlex.split()` — no shell features (pipes, `&&`, redirects). Use a script for those.

## Placeholders

| Syntax | Resolves to |
|---|---|
| `{{ commands.<name> }}` | Output of the named command (stdout + stderr) |
| `{{ args.<name> }}` | Value of the named user argument |

Unmatched placeholders resolve to empty string.

## The loop

Each iteration:

1. Re-read `RALPH.md` body from disk (frontmatter parsed once at startup)
2. Run all commands in order, capture output
3. Resolve `{{ commands.* }}` and `{{ args.* }}` placeholders
4. Pipe assembled prompt to agent via stdin
5. Wait for agent to exit
6. Repeat

The prompt body is re-read every iteration — you can edit it while the loop runs. HTML comments (`<!-- ... -->`) are stripped before the prompt reaches the agent.

## Prompt writing tips

- **Start with role and loop awareness**: "You are an autonomous X agent running in a loop."
- **Mention fresh context**: "Each iteration starts with fresh context. Your progress lives in code and git."
- **Use command output for feedback**: Include `{{ commands.tests }}` so the agent sees test results each iteration.
- **Be specific about one iteration of work**: Define what a single cycle should accomplish.
- **Include stop/commit conventions**: Tell the agent when and how to commit.

## Common patterns

### Minimal ralph

```markdown
---
agent: claude -p --dangerously-skip-permissions
---

Read TODO.md and implement the next task. Commit when done.
```

### Self-healing with test feedback

```markdown
---
agent: claude -p --dangerously-skip-permissions
commands:
  - name: tests
    run: uv run pytest -x
---

{{ commands.tests }}

Fix failing tests before starting new work.
Read TODO.md and implement the next task.
```

### Parameterized ralph

```markdown
---
agent: claude -p --dangerously-skip-permissions
args: [dir, focus]
---

Research the codebase at {{ args.dir }}.
Focus area: {{ args.focus }}.
```

```bash
ralph run research --dir ./api --focus "error handling"
```

### Debug a single iteration

```bash
ralph run my-ralph -n 1 --log-dir ralph_logs
cat ralph_logs/001_*.log
```
