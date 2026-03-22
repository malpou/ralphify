# Fleet example: todo app

A multi-role fleet demonstrating three ralphs working together on a todo app:

- **pm** — Project manager: triages issues, reviews PRs, creates tasks
- **dev** — Developer: picks up ready issues, implements features, creates PRs
- **qa** — QA: reviews open PRs, checks coverage, maintains quality

## How it works

The PM ralph starts first (highest priority). It creates GitHub Issues labeled
`ralph:ready`. The dev ralph depends on PM and picks up those issues. The QA
ralph depends on dev and reviews the resulting PRs.

Each ralph runs in its own git worktree on a separate branch, so they can
modify files without conflicting.

## Usage

```bash
# From your project root:
ralph fleet start examples/fleet-todo-app/fleet.yml

# Check status:
ralph fleet status

# Stop all ralphs:
ralph fleet stop
```

## Customization

- Swap `claude -p --dangerously-skip-permissions` for your preferred agent
- Adjust `stagger_start` and `max_concurrent` in `fleet.yml`
- Add more ralphs (e.g., a docs ralph, a security ralph)
