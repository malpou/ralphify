Set up a Ralphify project manager ralph in this repository.

## Prerequisites

Make sure `ralphify` is installed (`uv tool install ralphify` or `pip install ralphify`). Make sure `gh` CLI is authenticated for this repo.

## What to create

Create a `pm/` directory in the project root with the following files. Do NOT add `pm/` to `.gitignore` and do NOT track it in git. The `pm/` directory should be purely local — it exists on disk but is invisible to git. This ensures state persists across branch switches without polluting the repo.

### pm/RALPH.md

```yaml
---
agent: claude -p --dangerously-skip-permissions
idle:
  delay: 30s
  backoff: 2
  max_delay: 5m
  max: 30m
commands:
  - name: status
    run: ./show-status.sh
  - name: inbox
    run: ./show-inbox.sh
  - name: active-task
    run: ./show-active-task.sh
  - name: questions
    run: ./show-questions.sh
  - name: tests
    run: $TEST_COMMAND
    timeout: 120
  - name: git-log
    run: git log --oneline -15
  - name: git-status
    run: git status --short
---
```

For the `tests` command, detect the project's test runner:
- Python with pytest: `uv run pytest -x` or `pytest -x`
- Node.js: `npm test`
- Go: `go test ./...`
- Rust: `cargo test`
- If unclear, ask the user what test command to use

The prompt body should follow this structure:

#### Role section
Tell the agent it is an autonomous project manager and developer for this specific project. Each iteration is stateless — all state lives in files and git. State files live in `pm/` (INBOX.md, TODO.md, QUESTIONS.md, tasks/).

#### State section
Inject all command outputs using placeholders:
- `{{ commands.status }}` — workflow phase
- `{{ commands.inbox }}` — pending work items
- `{{ commands.active-task }}` — current task and its plan
- `{{ commands.questions }}` — unanswered blocker questions
- `{{ commands.tests }}` — test results
- `{{ commands.git-log }}` — recent commits
- `{{ commands.git-status }}` — working tree state

#### Decision tree section
The agent follows this priority order each iteration:
1. **Tests failing?** Fix them first.
2. **Blocked on questions?** If `pm/QUESTIONS.md` has unanswered questions for the active task, stop and wait.
3. **Active task with incomplete plan steps?** Implement the next unchecked step in `pm/tasks/<slug>/PLAN.md`, test, commit, check off the step.
4. **Active task fully complete?** Create a draft PR (`gh pr create --draft`), mark done in `pm/TODO.md`, switch back to main.
5. **Inbox has items?** Pick top unchecked item from `pm/INBOX.md`. If it's a GitHub issue URL, run `gh issue view <number>`. Create `pm/tasks/<slug>/PLAN.md` with summary, files to modify, 3-8 numbered steps with checkboxes, and acceptance criteria. Add to `pm/TODO.md`, mark inbox item done, create branch `pm/<slug>`.
6. **Nothing to do?** Idle. Output a short status summary, then output exactly `<!-- ralph:state idle -->` so the loop engine can back off.

#### Rules section
- One plan step per iteration
- Always run tests before committing
- Commit conventions: `feat:`, `fix:`, `refactor:`, `docs:`
- Never hack tests to make them pass
- Work on `pm/<slug>` branches, not main
- No force pushes or rebases
- State files always use `pm/` prefix paths
- If blocked, write to `pm/QUESTIONS.md` under `## Open`: `- **<task-slug>**: <question>`

### pm/show-status.sh

```bash
#!/bin/bash
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

branch=$(git branch --show-current 2>/dev/null || echo "unknown")

pending_inbox=0
if [ -f "INBOX.md" ]; then
    count=$(grep -c '^\- \[ \]' INBOX.md 2>/dev/null)
    if [ $? -eq 0 ]; then pending_inbox=$count; fi
fi

active_task=""
if [ -f "TODO.md" ]; then
    active_line=$(sed -n '/^## Active/,/^## /p' TODO.md | grep -m1 '^\- \[ \]' 2>/dev/null)
    if [ -n "$active_line" ]; then
        active_task=$(echo "$active_line" | sed 's/^- \[ \] \([^ ]*\).*/\1/')
    fi
fi

open_questions=0
if [ -f "QUESTIONS.md" ]; then
    count=$(sed -n '/^## Open/,/^## /p' QUESTIONS.md | grep -c '^\- \*\*' 2>/dev/null)
    if [ $? -eq 0 ]; then open_questions=$count; fi
fi

phase="IDLE"
if [ -n "$active_task" ]; then
    if [ "$open_questions" -gt 0 ]; then
        task_blocked=$(sed -n '/^## Open/,/^## /p' QUESTIONS.md | grep -c "\*\*${active_task}\*\*" 2>/dev/null)
        if [ "$task_blocked" -gt 0 ] 2>/dev/null; then
            phase="BLOCKED"
        fi
    fi
    if [ "$phase" != "BLOCKED" ] && [ -f "tasks/${active_task}/PLAN.md" ]; then
        total_steps=$(grep -cE '^[0-9]+\. \[' "tasks/${active_task}/PLAN.md" 2>/dev/null || true)
        done_steps=$(grep -cE '^[0-9]+\. \[x\]' "tasks/${active_task}/PLAN.md" 2>/dev/null || true)
        total_steps=${total_steps:-0}
        done_steps=${done_steps:-0}
        if [ "$total_steps" -gt 0 ] && [ "$total_steps" -eq "$done_steps" ]; then
            phase="PR_READY"
        else
            phase="IMPLEMENTING"
        fi
    fi
elif [ "$pending_inbox" -gt 0 ]; then
    phase="PLANNING"
fi

echo "Phase: ${phase}"
echo "Branch: ${branch}"
echo "Active task: ${active_task:-none}"
echo "Pending inbox items: ${pending_inbox}"
echo "Open questions: ${open_questions}"
```

### pm/show-inbox.sh

```bash
#!/bin/bash
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

if [ ! -f "INBOX.md" ]; then
    echo "(no INBOX.md found)"
    exit 0
fi

pending=$(grep '^\- \[ \]' INBOX.md 2>/dev/null)
if [ -z "$pending" ]; then
    echo "(empty inbox — all items processed)"
else
    echo "$pending"
fi
```

### pm/show-active-task.sh

```bash
#!/bin/bash
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

if [ ! -f "TODO.md" ]; then
    echo "(no TODO.md found)"
    exit 0
fi

active_line=$(sed -n '/^## Active/,/^## /p' TODO.md | grep -m1 '^\- \[ \]' 2>/dev/null)

if [ -z "$active_line" ]; then
    echo "(no active task)"
    exit 0
fi

slug=$(echo "$active_line" | sed 's/^- \[ \] \([^ ]*\).*/\1/')
echo "Active: ${active_line}"
echo ""

plan_file="tasks/${slug}/PLAN.md"
if [ -f "$plan_file" ]; then
    echo "--- PLAN.md ---"
    cat "$plan_file"
    echo ""
    total=$(grep -cE '^[0-9]+\. \[' "$plan_file" 2>/dev/null || true)
    done=$(grep -cE '^[0-9]+\. \[x\]' "$plan_file" 2>/dev/null || true)
    total=${total:-0}
    done=${done:-0}
    echo "Progress: ${done}/${total} steps completed"
else
    echo "(no plan yet — pm/tasks/${slug}/PLAN.md does not exist)"
fi
```

### pm/show-questions.sh

```bash
#!/bin/bash
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

if [ ! -f "QUESTIONS.md" ]; then
    echo "(no QUESTIONS.md found)"
    exit 0
fi

open_section=$(sed -n '/^## Open/,/^## /p' QUESTIONS.md | grep '^\- ' 2>/dev/null)

if [ -z "$open_section" ]; then
    echo "(no open questions)"
else
    echo "$open_section"
fi
```

### pm/INBOX.md

```markdown
# Inbox

<!-- Add work items here. Use checkboxes. The agent picks the top unchecked item. -->
<!-- Formats: plain text descriptions, GitHub issue URLs, or ideas -->
```

### pm/TODO.md

```markdown
# Tasks

## Active

## Done
```

### pm/QUESTIONS.md

```markdown
# Questions

## Open

## Answered
```

## After creating all files

1. Make all `.sh` files executable: `chmod +x pm/show-*.sh`
2. Verify scripts work by running `cd pm && ./show-status.sh`
3. Tell the user they can now:
   - Add items to `pm/INBOX.md` (with `- [ ]` checkbox format)
   - Run: `ralph run pm -n 20 --timeout 600 --log-dir ralph_logs`
   - Answer questions in `pm/QUESTIONS.md` when the agent gets blocked
   - Review draft PRs on GitHub
