---
description: Copy-pasteable ralphify setups for Python, TypeScript, Rust, Go, documentation, test coverage, and bug fixing loops.
---

# Cookbook

Copy-pasteable setups for common autonomous coding workflows. Each recipe includes the prompt, checks, and contexts you need — create the files, run `ralph run`, and go.

All recipes use the same `ralph.toml` (created by `ralph init`):

```toml
[agent]
command = "claude"
args = ["-p", "--dangerously-skip-permissions"]
ralph = "RALPH.md"
```

!!! tip "Use named ralphs for multiple workflows"
    Instead of editing `RALPH.md` each time, save recipes as named ralphs in `.ralphify/ralphs/` and switch between them:

    ```bash
    ralph run docs           # Documentation loop
    ralph run tests          # Test coverage loop
    ralph run bugfix         # Bug fixing loop
    ```

    See [Named ralphs](primitives.md#ralphs) for details.

---

## Python project

A general-purpose loop for a Python project using pytest and ruff.

**`RALPH.md`**

```markdown
---
checks: [tests, lint]
contexts: [git-log]
---

# Prompt

You are an autonomous coding agent running in a loop. Each iteration
starts with a fresh context. Your progress lives in the code and git.

{{ contexts.git-log }}

Read TODO.md for the current task list. Pick the top uncompleted task,
implement it fully, then mark it done.

## Rules

- One task per iteration
- No placeholder code — full, working implementations only
- Run tests before committing
- Commit with a descriptive message like `feat: add X` or `fix: resolve Y`
- Mark the completed task in TODO.md
```

**`.ralphify/checks/tests/CHECK.md`**

```markdown
---
command: uv run pytest -x
timeout: 120
---
Fix all failing tests. Do not skip or delete tests.
Do not add `# type: ignore` or `# noqa` comments.
```

**`.ralphify/checks/lint/CHECK.md`**

```markdown
---
command: uv run ruff check .
timeout: 60
---
Fix all lint errors. Do not suppress warnings with noqa comments.
```

**`.ralphify/contexts/git-log/CONTEXT.md`**

```markdown
---
command: git log --oneline -10
---
## Recent commits
```

### Setup commands

```bash
ralph init
mkdir -p .ralphify/checks/tests .ralphify/checks/lint .ralphify/contexts/git-log
# Then create the CHECK.md and CONTEXT.md files as shown above
```

---

## TypeScript / Node.js project

Loop for a Node.js or TypeScript project using npm scripts.

**`RALPH.md`**

```markdown
---
checks: [tests, lint]
contexts: [git-log]
---

# Prompt

You are an autonomous coding agent running in a loop. Each iteration
starts with a fresh context. Your progress lives in the code and git.

{{ contexts.git-log }}

Read TODO.md for the current task list. Pick the top uncompleted task,
implement it fully, then mark it done.

## Rules

- One task per iteration
- No placeholder code — full, working implementations only
- Run `npm test` before committing
- Commit with a descriptive message like `feat: add X` or `fix: resolve Y`
- Mark the completed task in TODO.md
```

**`.ralphify/checks/tests/CHECK.md`**

```markdown
---
command: npm test
timeout: 120
---
Fix all failing tests. Do not skip or delete tests.
```

**`.ralphify/checks/lint/CHECK.md`**

```markdown
---
command: npx eslint .
timeout: 60
---
Fix all lint errors. Do not disable rules with eslint-disable comments.
```

**`.ralphify/contexts/git-log/CONTEXT.md`**

```markdown
---
command: git log --oneline -10
---
## Recent commits
```

---

## Rust project

Loop for a Rust project using cargo's built-in toolchain.

**`RALPH.md`**

```markdown
---
checks: [tests, clippy, fmt]
contexts: [git-log]
---

# Prompt

You are an autonomous coding agent running in a loop. Each iteration
starts with a fresh context. Your progress lives in the code and git.

{{ contexts.git-log }}

Read TODO.md for the current task list. Pick the top uncompleted task,
implement it fully, then mark it done.

## Rules

- One task per iteration
- No placeholder code — full, working implementations only
- All code must pass `cargo test`, `cargo clippy`, and `cargo fmt --check`
- Commit with a descriptive message like `feat: add X` or `fix: resolve Y`
- Mark the completed task in TODO.md
```

**`.ralphify/checks/tests/CHECK.md`**

```markdown
---
command: cargo test
timeout: 180
---
Fix all failing tests. Do not ignore or delete tests.
```

**`.ralphify/checks/clippy/CHECK.md`**

```markdown
---
command: cargo clippy -- -D warnings
timeout: 60
---
Fix all clippy warnings. Do not add `#[allow(...)]` attributes to suppress them.
```

**`.ralphify/checks/fmt/CHECK.md`**

```markdown
---
command: cargo fmt --check
timeout: 30
---
Code is not formatted. Run `cargo fmt` to fix formatting.
```

**`.ralphify/contexts/git-log/CONTEXT.md`**

```markdown
---
command: git log --oneline -10
---
## Recent commits
```

---

## Go project

Loop for a Go project using standard tooling.

**`RALPH.md`**

```markdown
---
checks: [tests, vet]
contexts: [git-log]
---

# Prompt

You are an autonomous coding agent running in a loop. Each iteration
starts with a fresh context. Your progress lives in the code and git.

{{ contexts.git-log }}

Read TODO.md for the current task list. Pick the top uncompleted task,
implement it fully, then mark it done.

## Rules

- One task per iteration
- No placeholder code — full, working implementations only
- All code must pass `go test ./...` and `go vet ./...`
- Use `gofmt` conventions — do not fight the formatter
- Commit with a descriptive message like `feat: add X` or `fix: resolve Y`
- Mark the completed task in TODO.md
```

**`.ralphify/checks/tests/CHECK.md`**

```markdown
---
command: go test ./...
timeout: 180
---
Fix all failing tests. Do not skip or delete tests.
```

**`.ralphify/checks/vet/CHECK.md`**

```markdown
---
command: go vet ./...
timeout: 60
---
Fix all issues reported by `go vet`.
```

**`.ralphify/contexts/git-log/CONTEXT.md`**

```markdown
---
command: git log --oneline -10
---
## Recent commits
```

---

## Bug fixing

Fix bugs from failing tests. The agent sees which tests are broken and focuses on fixing them one at a time.

**`RALPH.md`**

```markdown
---
checks: [tests]
contexts: [git-log, failing-tests]
---

# Prompt

You are an autonomous bug-fixing agent running in a loop. Each iteration
starts with a fresh context. Your progress lives in the code and git.

{{ contexts.git-log }}

{{ contexts.failing-tests }}

Review the failing tests above. Pick the most important failure, trace it
to the root cause in the source code, and fix it. Write a regression test
if one doesn't already exist.

## Rules

- One bug fix per iteration
- Fix the source code, not the tests — unless the test itself is wrong
- Do not skip, delete, or mark tests as expected failures
- Run the full test suite before committing to check for regressions
- Commit with `fix: resolve X that caused Y`
```

**`.ralphify/checks/tests/CHECK.md`**

```markdown
---
command: uv run pytest -x
timeout: 120
---
Tests are still failing. Fix the root cause — do not skip or delete tests.
```

**`.ralphify/contexts/failing-tests/run.sh`** (script-based — needs shell pipes):

```bash
#!/bin/bash
uv run pytest --tb=short -q 2>&1 || true
```

**`.ralphify/contexts/failing-tests/CONTEXT.md`**

```markdown
---
timeout: 120
---
## Current test results
```

**`.ralphify/contexts/git-log/CONTEXT.md`**

```markdown
---
command: git log --oneline -10
---
## Recent commits
```

Make the script executable: `chmod +x .ralphify/contexts/failing-tests/run.sh`

---

## Improve project docs

Improve project documentation one page at a time.

**`RALPH.md`**

```markdown
---
checks: [docs-build]
contexts: [git-log]
---

# Prompt

You are an autonomous documentation agent running in a loop. Each iteration
starts with a fresh context. Your progress lives in the code and git.

{{ contexts.git-log }}

Read the codebase and existing docs. Identify the biggest gap between
what the code can do and what the docs explain. Write or improve one
page per iteration.

## Rules

- Do one meaningful documentation improvement per iteration
- Search before creating anything new
- No placeholder content — full, accurate, useful writing only
- Verify any code examples actually run before committing
- Commit with a descriptive message like `docs: explain X for users who want to Y`
```

**`.ralphify/checks/docs-build/CHECK.md`**

```markdown
---
command: uv run mkdocs build --strict
timeout: 60
---
The docs build failed. Fix any warnings or errors in the markdown files.
Check for broken cross-links, missing pages in mkdocs.yml nav, and
invalid admonition syntax.
```

**`.ralphify/contexts/git-log/CONTEXT.md`**

```markdown
---
command: git log --oneline -10
---
## Recent commits
```

---

## Increase test coverage

Uses script-based checks and contexts to track and enforce a coverage threshold.

**`RALPH.md`**

```markdown
---
checks: [tests, coverage-threshold]
contexts: [coverage]
---

# Prompt

You are an autonomous test-writing agent running in a loop. Each iteration
starts with a fresh context. Your progress lives in the code and git.

{{ contexts.coverage }}

Read the coverage report above. Find the module with the lowest coverage
that has meaningful logic worth testing. Write thorough tests for that
module — cover the happy path, edge cases, and error conditions.

## Rules

- One module per iteration — write all tests for it, then move on
- Write tests that verify behavior, not implementation details
- Do NOT modify source code to make it easier to test — test it as-is
- Run the full test suite before committing to check for regressions
- Commit with `test: add tests for <module name>`
- Skip modules that already have 90%+ coverage
```

**`.ralphify/checks/tests/CHECK.md`**

```markdown
---
command: uv run pytest -x
timeout: 120
---
Fix all failing tests. Do not skip or delete existing tests.
If a new test is failing, the test is likely wrong — fix the test,
not the source code.
```

**`.ralphify/checks/coverage-threshold/run.sh`** (script-based — needs shell features):

```bash
#!/bin/bash
set -e
uv run pytest --cov=src --cov-report=term-missing --cov-fail-under=80
```

**`.ralphify/checks/coverage-threshold/CHECK.md`**

```markdown
---
timeout: 120
---
Coverage has dropped below the minimum threshold. Check which tests
are missing and add them. Do not lower the threshold.
```

**`.ralphify/contexts/coverage/run.sh`**:

```bash
#!/bin/bash
uv run pytest --cov=src --cov-report=term-missing -q 2>/dev/null || true
```

**`.ralphify/contexts/coverage/CONTEXT.md`**

```markdown
---
timeout: 60
---
## Current test coverage
```

Make scripts executable: `chmod +x .ralphify/checks/coverage-threshold/run.sh .ralphify/contexts/coverage/run.sh`
