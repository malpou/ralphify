#!/bin/bash
# Show unanswered questions from QUESTIONS.md

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

if [ ! -f "QUESTIONS.md" ]; then
    echo "(no QUESTIONS.md found)"
    exit 0
fi

# Extract the Open section
open_section=$(sed -n '/^## Open/,/^## /p' QUESTIONS.md | grep '^\- ' 2>/dev/null)

if [ -z "$open_section" ]; then
    echo "(no open questions)"
else
    echo "$open_section"
fi
