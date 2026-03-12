---
description: Install ralphify, set up your first autonomous coding loop with checks and contexts, and run a self-healing AI agent in 10 minutes.
---

# Getting Started

This tutorial walks through setting up ralphify on a project, adding checks and contexts, and running a productive autonomous loop. By the end, you'll have a self-healing coding loop that validates its own work.

## Prerequisites

- **Python 3.11+**
- **An AI coding agent CLI** — this tutorial uses Claude Code, but ralphify works with [any agent that accepts piped input](agents.md)
- **A project with a test suite** (we'll use this for the feedback loop)

### Install Claude Code (if you don't have it)

```bash
npm install -g @anthropic-ai/claude-code
```

Then authenticate:

```bash
claude  # Opens an interactive session — follow the login prompts
```

Once authenticated, verify it works non-interactively:

```bash
echo "Say hello" | claude -p
```

You should see a text response. If this works, you're ready.

!!! tip "Using a different agent?"
    See [Using with Different Agents](agents.md) for setup guides for Aider, Codex CLI, or your own custom wrapper.

## Step 1: Install ralphify

=== "uv (recommended)"

    ```bash
    uv tool install ralphify
    ```

=== "pipx"

    ```bash
    pipx install ralphify
    ```

=== "pip"

    ```bash
    pip install ralphify
    ```

Verify it's working:

```bash
ralph --version
```

## Step 2: Initialize your project

Navigate to your project and run:

```bash
ralph init
```

This creates two files:

**`ralph.toml`** — configuration for the loop:

```toml
[agent]
command = "claude"
args = ["-p", "--dangerously-skip-permissions"]
ralph = "RALPH.md"
```

!!! info "What does `--dangerously-skip-permissions` do?"
    Claude Code normally asks for your approval before running shell commands, editing files, or making git commits. The `--dangerously-skip-permissions` flag disables these interactive prompts so the agent can work autonomously without waiting for input. The `-p` flag enables non-interactive ("print") mode, which reads the prompt from stdin instead of opening a chat session.

    This is safe to use when ralphify is the only thing running the agent, because **checks** act as your guardrails — they validate the agent's work after each iteration and feed failures back for the agent to fix.

**`RALPH.md`** — the prompt that gets piped to the agent each iteration. The default is a generic starting point — you'll customize it next.

## Step 3: Write your ralph

Replace the contents of `RALPH.md` with a prompt tailored to your project. Here's an example for a Python project with a TODO list:

```markdown
# Prompt

You are an autonomous coding agent running in a loop. Each iteration
starts with a fresh context. Your progress lives in the code and git.

Read TODO.md for the current task list. Pick the top uncompleted task,
implement it fully, then mark it done.

## Rules

- One task per iteration
- No placeholder code — full, working implementations only
- Run `uv run pytest -x` before committing
- Commit with a descriptive message like `feat: add X` or `fix: resolve Y`
- Mark the completed task in TODO.md
```

!!! tip "Be specific"
    The more specific your prompt, the better the results. "Run tests" is less effective than the exact command `uv run pytest -x`. Point the agent at a concrete file like `TODO.md` rather than saying "find something to work on."

## Step 4: Do a test run

Before setting up checks and contexts, verify the basic loop works:

```bash
ralph run -n 1 --log-dir ralph_logs
```

This runs a single iteration and saves the output to `ralph_logs/`. Review the log to see what the agent did:

```bash
ls ralph_logs/
cat ralph_logs/001_*.log
```

!!! tip "Add `ralph_logs/` to `.gitignore`"
    Log files are useful for debugging but shouldn't be committed. Add them to your `.gitignore`:

    ```bash
    echo "ralph_logs/" >> .gitignore
    ```

If the agent produced useful work, you're ready to add guardrails.

## Step 5: Add a test check

Checks run **after** each iteration to validate the agent's work. If a check fails, its output is fed into the next iteration so the agent can fix the problem.

Create a check that runs your test suite:

```bash
ralph new check tests
```

This creates `.ralphify/checks/tests/CHECK.md`. Edit it:

```markdown
---
command: uv run pytest -x
timeout: 120
enabled: true
---
Fix all failing tests. Do not skip or delete tests.
Do not add `# type: ignore` or `# noqa` comments.
```

The text below the frontmatter is the **failure instruction** — it gets included in the prompt when the check fails, telling the agent how to handle the failure.

## Step 6: Add a lint check

Add a second check for linting:

```bash
ralph new check lint
```

Edit `.ralphify/checks/lint/CHECK.md`:

```markdown
---
command: uv run ruff check .
timeout: 60
enabled: true
---
Fix all lint errors. Do not suppress warnings with noqa comments.
```

## Step 7: Add a context

Contexts inject dynamic data into the prompt before each iteration. A useful default is recent git history — it helps the agent understand what's already been done.

```bash
ralph new context git-log
```

Edit `.ralphify/contexts/git-log/CONTEXT.md`:

```markdown
---
command: git log --oneline -10
timeout: 10
enabled: true
---
## Recent commits
```

The command runs each iteration and its output is appended to the prompt. The body text ("## Recent commits") appears above the command output as a label.

### Place the context in your prompt

By default, context output is appended to the end of the prompt. You can control placement with a placeholder in `RALPH.md`:

```markdown
# Prompt

{{ contexts.git-log }}

You are an autonomous coding agent running in a loop...
```

Or use `{{ contexts }}` to place all contexts at once:

```markdown
{{ contexts }}

You are an autonomous coding agent...
```

## Step 8: Verify and run

Check that everything is configured correctly:

```bash
ralph status
```

If it says "Ready to run", you're good.

Start with a few iterations to verify things work as expected:

```bash
ralph run -n 3 --log-dir ralph_logs
```

Watch the output. After each iteration, you'll see check results:

```
── Iteration 1 ──
✓ Iteration 1 completed (45.2s) → ralph_logs/001_20250115-142301.log
  Checks: 2 passed
    ✓ lint
    ✓ tests
```

If a check fails, the next iteration automatically gets the failure details:

```
── Iteration 2 ──
✗ Iteration 2 failed with exit code 1 (23.1s)
  Checks: 1 passed, 1 failed
    ✓ lint
    ✗ tests (exit 1)

── Iteration 3 ──
```

The agent in iteration 3 receives the test failure output and the failure instruction ("Fix all failing tests..."), so it can fix the problem.

Once you're confident the loop works, drop the `-n 3` to let it run indefinitely. Press `Ctrl+C` to stop.

## Tips from real usage

**Use a plan file.** Give the agent a `PLAN.md` or `TODO.md` to read and update. This provides continuity across iterations — the agent sees what's done and what's next without needing memory.

**Add signs, not essays.** When the agent does something dumb, add a short constraint to the prompt. `RALPH.md` is re-read every iteration, so changes take effect immediately:

```markdown
- Do NOT refactor existing code unless the task requires it
- Do NOT create new utility files
```

Each sign should be specific, negative ("do NOT"), and observable from a git diff.

**Use checks for hard rules, the prompt for soft rules.** If you can write a command that returns exit 0 or 1, make it a check. If it's a judgment call, put it in the prompt.

**Order checks fast to strict.** Checks run alphabetically. Name them `01-lint`, `02-typecheck`, `03-tests` so fast checks run first.

**Start small.** Always `ralph run -n 3` on a new setup. Review the logs. Only scale up once you're confident the loop is productive.

## Next steps

- [Cookbook](cookbook.md) — complete setups for Python, TypeScript, bug fixing, docs, and CI
- [Primitives](primitives.md) — full reference for checks, contexts, instructions, and named ralphs
- [CLI Reference](cli.md) — all commands and options
