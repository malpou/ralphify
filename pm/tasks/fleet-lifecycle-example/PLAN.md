# fleet-lifecycle-example — Sample fleet scenario for testing multi-ralph orchestration

## Summary

Create a self-contained example directory (`examples/fleet-todo-app/`) that demonstrates a full software lifecycle using a fleet of ralphs. The scenario simulates a todo app project with multiple roles (PM, developer, QA/tester) coordinated through kanban-style file conventions. No application code — just the ralph definitions, project scaffolding, and an INBOX.md ready to drive the fleet.

This is research-driven: use web search to find good examples of multi-agent software lifecycles and kanban workflows to inform the design.

## Files to create

- `examples/fleet-todo-app/README.md` — Overview of the example and how to run it
- `examples/fleet-todo-app/ralphs/pm.md` — PM ralph definition
- `examples/fleet-todo-app/ralphs/dev.md` — Developer ralph definition
- `examples/fleet-todo-app/ralphs/qa.md` — QA/tester ralph definition
- `examples/fleet-todo-app/INBOX.md` — Seed inbox with todo app tasks
- `examples/fleet-todo-app/TODO.md` — Initial kanban board
- `examples/fleet-todo-app/fleet.yml` — Fleet configuration

## Steps

- [x] 1. Research multi-agent software lifecycle examples and kanban workflows via web search to inform the design
- [x] 2. Create the example directory structure and fleet.yml configuration
- [x] 3. Write the PM, developer, and QA ralph definitions with realistic prompts and commands
- [x] 4. Create the seed INBOX.md and TODO.md with todo app feature tasks
- [x] 5. Write the README.md explaining the example and how to use it
- [ ] 6. Commit and create draft PR

## Acceptance criteria

- Example directory is self-contained and well-documented
- Ralph definitions use realistic commands and prompts
- Kanban workflow is clearly demonstrated (INBOX → TODO → In Progress → Done)
- No application code — just the orchestration scaffolding
- README explains the fleet concept and how to run the example
