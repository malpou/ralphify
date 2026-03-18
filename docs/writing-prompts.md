---
description: How to write effective RALPH.md prompts for autonomous coding loops — structure, patterns, anti-patterns, and real examples.
---

# Writing Prompts

Your `RALPH.md` is the single most important file in a ralph loop. It's the only thing the agent reads each iteration — everything it does follows from what you write here. A good prompt turns an AI coding agent into a productive autonomous worker. A bad one produces noise.

This guide covers the patterns that work, the mistakes that waste iterations, and how to tune your prompt while the loop is running.

## The anatomy of a good prompt

Every effective ralph prompt has three parts:

### 1. Role and orientation

Tell the agent what it is, how it works, and where progress lives. This prevents the agent from trying to have a conversation, ask questions, or wait for input.

```markdown
You are an autonomous coding agent running in a loop. Each iteration
starts with a fresh context. Your progress lives in the code and git.
```

This framing matters because the agent has **no memory between iterations**. Without it, the agent may try to pick up where it "left off" or reference work it can't see.

### 2. Task source

Point the agent at something concrete to work on. The most common mistake is being vague ("improve the codebase"). Instead, give the agent a **specific place to look** for work:

| Pattern | When to use |
|---|---|
| `Read TODO.md and pick the top uncompleted task` | When you maintain a task list |
| `Read PLAN.md and implement the next step` | For sequential multi-step work |
| `Find the module with the lowest test coverage` | For coverage-driven testing |
| `Read the codebase and find the biggest documentation gap` | For open-ended improvement |
| `Fix the failing tests` | When checks feed failures back |

The key is that the agent can **find work without you telling it what to do each time**. The task source is what makes the loop autonomous.

### 3. Rules and constraints

Constraints are more important than instructions. The agent knows how to code — what it doesn't know is your project's conventions, what to avoid, and when to stop.

```markdown
## Rules

- One task per iteration
- No placeholder code — full, working implementations only
- Run tests before committing
- Commit with a descriptive message like `feat: add X` or `fix: resolve Y`
- Do not modify existing tests to make them pass
```

Rules prevent the agent from:

- Doing too much in one iteration (context window bloat, messy commits)
- Leaving TODO comments instead of writing real code
- Breaking things it shouldn't touch
- Committing without validation

## Patterns that work

### The TODO-driven loop

Maintain a `TODO.md` that the agent reads and updates each iteration. This gives you a clear task queue and visible progress.

```markdown
# Prompt

You are an autonomous coding agent running in a loop. Each iteration
starts with a fresh context. Your progress lives in the code and git.

Read TODO.md for the current task list. Pick the top uncompleted task,
implement it fully, then mark it done.

## Rules

- One task per iteration
- No placeholder code — full implementations only
- Run `uv run pytest -x` before committing
- Commit with a descriptive message
- Mark the completed task in TODO.md
```

**Why it works:** The agent always knows what to do next. You control priority by reordering the list. You can add tasks while the loop runs.

### The self-healing loop

Rely on [checks](primitives.md#checks) to define "done" and let failures guide the agent. The prompt focuses on the work; the checks handle quality.

```markdown
---
checks: [tests, lint, typecheck]
contexts: [git-log]
---

# Prompt

{{ contexts.git-log }}

You are an autonomous coding agent. Read PLAN.md and implement the
next incomplete step. If the previous iteration left failing checks,
fix those first before moving on.

## Rules

- Fix check failures before starting new work
- One step per iteration
- Commit each completed step separately
```

**Why it works:** Failed checks automatically inject their output into the next iteration. The agent sees exactly what broke and how to fix it. You don't need to write error-handling instructions for every possible failure — the checks do it for you.

### The edit-while-running loop

The agent re-reads `RALPH.md` every iteration. This means you can steer the loop in real time by editing the prompt while it runs.

```markdown
# Prompt

You are an autonomous agent improving this project's documentation.

## Current focus

<!-- Edit this section while the loop runs to steer the agent -->
Focus on the API reference docs. Each endpoint needs a working
curl example and a description of the response format.

## Rules

- One page per iteration
- Verify all code examples run correctly
- Commit with `docs: ...` prefix
```

**Why it works:** When the agent does something you don't want, you add a constraint. When you want it to shift focus, you edit the "Current focus" section. The next iteration picks up your changes immediately.

### The context-rich loop

Use [contexts](primitives.md#contexts) to give the agent situational awareness without bloating the prompt with static text.

```markdown
---
checks: [tests]
contexts: [git-log, test-status, open-issues]
---

# Prompt

{{ contexts.git-log }}

{{ contexts.test-status }}

{{ contexts.open-issues }}

You are an autonomous bug-fixing agent. Review the open issues and
test failures above. Pick the most important one and fix it.

## Rules

- One fix per iteration
- Write a regression test for every bug fix
- Commit with `fix: resolve #<issue-number>`
```

**Why it works:** The agent sees fresh data every iteration — what was recently committed, what tests are failing, what issues are open. It makes informed decisions about what to work on without you updating the prompt.

## Anti-patterns to avoid

### Too vague

```markdown
<!-- DON'T -->
Improve the codebase. Make things better.
```

The agent doesn't know what "better" means to you. It might refactor code that works fine, add unnecessary abstractions, or reorganize files in ways that break your workflow. Always point at a concrete task source.

### Too many tasks per iteration

```markdown
<!-- DON'T -->
Implement user authentication, add rate limiting, write tests for
both, update the API docs, and deploy to staging.
```

One iteration = one task. If the agent tries to do five things, it'll do all of them poorly. The context window fills up, the commit is a mess, and if something breaks you can't tell which change caused it.

### No validation step

```markdown
<!-- DON'T -->
Read TODO.md, implement the next task, and commit.
```

Without "run tests before committing", the agent will commit broken code. Then the next iteration starts with a broken codebase, wastes time understanding what went wrong, and may make it worse. Always include a validation step, either in the prompt or via checks.

### Instructions that fight the checks

```markdown
<!-- DON'T — the lint check already enforces this -->
---
checks: [lint]
---
Make sure all code passes ruff lint checks before committing.
Run `ruff check .` and fix any issues.
```

If you have a lint check, you don't need lint instructions in the prompt. The check runs automatically, and its failure output tells the agent exactly what to fix. Duplicating the instruction wastes prompt space and can create contradictions if the check command differs from what the prompt says.

### No commit instructions

```markdown
<!-- DON'T -->
Fix bugs from the issue tracker.
```

Ralphify doesn't commit for the agent — the agent must do it. Without explicit commit instructions, some agents won't commit at all, and progress is lost when the next iteration starts fresh. Always include:

```markdown
- Commit with a descriptive message like `fix: resolve X that caused Y`
```

## Tuning a running loop

The most powerful feature of ralph loops is that you can edit `RALPH.md` while the loop is running. Here's how to use this effectively:

**When the agent does something dumb, add a sign.** This is the core insight from the [Ralph Wiggum technique](https://ghuntley.com/ralph/). If the agent keeps deleting tests instead of fixing them:

```markdown
## Rules
- Do NOT delete or skip failing tests — fix the code instead
```

**When the agent gets stuck in a loop,** it's usually because the prompt is ambiguous about what to do when something fails. Add explicit fallback instructions:

```markdown
- If you can't fix a failing test after one attempt, move on to the next task
  and leave a TODO comment explaining the issue
```

**When you want to shift focus,** edit the task source. Change "Read TODO.md" to "Focus only on the API module" and the next iteration follows the new direction.

**When the agent is too ambitious,** tighten the scope constraint:

```markdown
- Touch at most 3 files per iteration
- Do not refactor code that isn't directly related to the current task
```

## Prompt size and context windows

Keep your prompt focused. A long prompt with every possible instruction eats into the agent's context window, leaving less room for the actual codebase.

Rules of thumb:

- **Core prompt:** 20-50 lines is the sweet spot. Enough to be specific, short enough to leave room for work.
- **Contexts:** Use `{{ contexts.name }}` placeholders to inject only the data the agent needs. Don't dump everything — pick the 2-3 most useful signals.
- **User args:** Use `{{ args.name }}` to make ralphs reusable — pass project-specific values from the CLI instead of hardcoding them in the prompt.
- **Check failure output:** This is injected automatically and can be long. If your checks produce verbose output, consider using scripts that filter to the relevant lines.

## Parameterized ralphs

Use [user arguments](primitives.md#user-arguments) to make a ralph reusable across different projects or configurations:

```markdown
---
description: Research agent for any codebase
args: [dir, focus]
---

Research the codebase at {{ args.dir }}.

Focus area: {{ args.focus }}

## Rules

- Read the code before making claims
- Cite specific file paths and line numbers
- Summarize findings in RESEARCH.md
```

Run the same ralph against different projects:

```bash
ralph run research --dir ./api --focus "error handling"
ralph run research --dir ./frontend --focus "state management"
```

## Next steps

- [Getting Started](getting-started.md) — set up your first loop
- [Primitives](primitives.md) — full reference for checks, contexts, and ralphs
- [Cookbook](cookbook.md) — copy-pasteable setups for common use cases
