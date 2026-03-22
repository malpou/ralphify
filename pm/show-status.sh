#!/bin/bash
# Determine current workflow phase from file state

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

branch=$(git branch --show-current 2>/dev/null || echo "unknown")

# Count pending inbox items
pending_inbox=0
if [ -f "INBOX.md" ]; then
    count=$(grep -c '^\- \[ \]' INBOX.md 2>/dev/null)
    if [ $? -eq 0 ]; then pending_inbox=$count; fi
fi

# Find active task
active_task=""
if [ -f "TODO.md" ]; then
    active_line=$(sed -n '/^## Active/,/^## /p' TODO.md | grep -m1 '^\- \[ \]' 2>/dev/null)
    if [ -n "$active_line" ]; then
        active_task=$(echo "$active_line" | sed 's/^- \[ \] \([^ ]*\).*/\1/')
    fi
fi

# Count open questions
open_questions=0
if [ -f "QUESTIONS.md" ]; then
    count=$(sed -n '/^## Open/,/^## /p' QUESTIONS.md | grep -c '^\- \*\*' 2>/dev/null)
    if [ $? -eq 0 ]; then open_questions=$count; fi
fi

# Determine phase
phase="IDLE"
if [ -n "$active_task" ]; then
    # Check if blocked on questions
    if [ "$open_questions" -gt 0 ]; then
        task_blocked=$(sed -n '/^## Open/,/^## /p' QUESTIONS.md | grep -c "\*\*${active_task}\*\*" 2>/dev/null)
        if [ "$task_blocked" -gt 0 ] 2>/dev/null; then
            phase="BLOCKED"
        fi
    fi

    if [ "$phase" != "BLOCKED" ] && [ -f "tasks/${active_task}/PLAN.md" ]; then
        # Check if all steps are done
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
