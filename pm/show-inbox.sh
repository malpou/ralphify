#!/bin/bash
# Show unprocessed inbox items

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
