---
name: new-ralph
description: Create a new ralph from a plain-English description of what you want to automate
argument-hint: "[name]"
disable-model-invocation: true
---

You are helping the user create a new **ralph** — a reusable automation for autonomous AI coding loops powered by ralphify. The user does NOT need to know how ralphify works internally. Your job is to translate their plain description into a working ralph setup.

## What you need from the user

Ask the user to **describe what they want to automate** in plain language. For example:
- "I want to write tests for my Python project until I hit 90% coverage"
- "I want to refactor all my JavaScript files to TypeScript"
- "I want to fix linting errors across the codebase"

If `$ARGUMENTS` was provided, use it as the ralph name. Otherwise, derive a short kebab-case name from their description.

Ask **only what you need** to build a good setup:
- What does "done" look like for one cycle of work?
- What language/tools/framework is the project using?
- Any conventions or constraints to follow?

Do NOT ask the user about checks, contexts, frontmatter, or other ralphify internals. Figure those out yourself based on their description.

## How ralphs work (internal reference — do not expose to user)

A ralph is a directory at `.ralphify/ralphs/<name>/` containing a prompt and optional validation and data injection.

### RALPH.md — the prompt

```markdown
---
description: What this ralph does (one line)
checks: [global-check-name]          # optional: include global checks
contexts: [global-context-name]      # optional: include global contexts
args: [dir, focus]                   # optional: declare positional CLI arg names
enabled: true
---

Prompt text piped to the agent each iteration.
Use {{ contexts.context-name }} to place context output.
Use {{ args.name }} for user arguments passed from the CLI.
```

### Checks — post-iteration validation

Location: `.ralphify/ralphs/<name>/checks/<check-name>/CHECK.md`

```markdown
---
command: pytest -x
timeout: 120
enabled: true
---
Fix all failing tests. Do not skip or delete tests.
```

- `command` is parsed with `shlex.split()` — no shell features (pipes, `&&`, redirections)
- Body text = failure instruction shown to the agent when the check fails
- For shell features, create a `run.sh` or `run.py` script instead of using `command`

### Contexts — dynamic data injected before each iteration

Location: `.ralphify/ralphs/<name>/contexts/<context-name>/CONTEXT.md`

```markdown
---
command: git log --oneline -10
timeout: 30
enabled: true
---
## Recent commits
```

- Body text appears as a label above the command output
- Reference in the prompt with `{{ contexts.context-name }}`

### User arguments

Ralphs can accept CLI arguments, making them reusable across different projects or configurations:

- **Named flags**: `ralph run research --dir ./src --focus "perf"` → `{{ args.dir }}`, `{{ args.focus }}`
- **Positional args**: `ralph run research ./src "perf"` — requires `args: [dir, focus]` in frontmatter
- Missing args resolve to empty string
- Context and check scripts receive them as `RALPH_ARG_<KEY>` environment variables (uppercase, hyphens → underscores)

Use args when a ralph could be reused across different directories, files, thresholds, or configurations.

### Scripts

For commands needing shell features, create `run.sh` / `run.py` in the primitive directory. Script takes precedence over `command`. Remember `chmod +x`.

### Execution order

Primitives run alphabetically. Use number prefixes: `01-lint/`, `02-tests/`.

### Output truncation

All primitive output is truncated to 5000 characters.

## Your workflow

1. **Understand the task.** Get a plain-English description. Ask short clarifying questions if needed — no more than 2-3.

2. **Design the ralph.** Based on the description, decide:
   - What prompt to write
   - What checks will catch mistakes (tests, lint, type checks, builds, etc.)
   - What context the agent needs each iteration (git log, coverage reports, file listings, etc.)
   - Whether user arguments would make the ralph more reusable

3. **Create everything:**
   - `RALPH.md` with a clear, specific prompt. Follow these patterns:
     - Start with role and loop awareness: "You are an autonomous X agent running in a loop."
     - Include: "Each iteration starts with a fresh context. Your progress lives in the code and git."
     - Be specific about what one iteration of work looks like
     - Include rules as a bulleted list
     - End with commit conventions
   - Checks for any validation that matters (tests, linting, type checking, builds)
   - Contexts for dynamic data the agent needs
   - `chmod +x` on any scripts

4. **Present a summary** to the user:
   - Show the file tree of what you created
   - Briefly explain what the ralph will do in each iteration
   - Mention any checks that will catch errors
   - Suggest running: `ralph run <name> -n 1`
