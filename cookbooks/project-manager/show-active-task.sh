#!/bin/bash
# Show the active task and its PLAN.md

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

if [ ! -f "TODO.md" ]; then
    echo "(no TODO.md found)"
    exit 0
fi

# Find first unchecked item under ## Active
active_line=$(sed -n '/^## Active/,/^## /p' TODO.md | grep -m1 '^\- \[ \]' 2>/dev/null)

if [ -z "$active_line" ]; then
    echo "(no active task)"
    exit 0
fi

# Extract task slug (first word after checkbox)
slug=$(echo "$active_line" | sed 's/^- \[ \] \([^ ]*\).*/\1/')
echo "Active: ${active_line}"
echo ""

# Show the plan if it exists
plan_file="tasks/${slug}/PLAN.md"
if [ -f "$plan_file" ]; then
    echo "--- PLAN.md ---"
    cat "$plan_file"

    # Show progress
    echo ""
    total=$(grep -cE '^[0-9]+\. \[' "$plan_file" 2>/dev/null || true)
    done=$(grep -cE '^[0-9]+\. \[x\]' "$plan_file" 2>/dev/null || true)
    total=${total:-0}
    done=${done:-0}
    echo "Progress: ${done}/${total} steps completed"
else
    echo "(no plan yet — tasks/${slug}/PLAN.md does not exist)"
fi
