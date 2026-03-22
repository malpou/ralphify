# Plan: Ralphify agent skill

## Summary

Add a bundled agent skill that teaches AI coding agents how to use ralphify — creating ralphs, running them, and understanding the core concepts. This is the "meta" skill from issue #3: an agent with this skill installed can autonomously create and manage ralphs. The existing `new-ralph` skill helps users *create* a ralph interactively; this new skill gives agents *reference knowledge* about ralphify so they can use it independently.

## Files to modify

- `src/ralphify/skills/ralphify/SKILL.md` — New bundled skill file with ralphify usage instructions
- `src/ralphify/skills/ralphify/__init__.py` — Package init (required for importlib.resources)
- `docs/changelog.md` — Add entry for the new skill

## Steps

- [x] 1. Create the `ralphify` skill directory and `SKILL.md` with comprehensive ralphify usage instructions covering: what ralphify is, RALPH.md format, CLI commands (run, new, init), frontmatter fields, placeholders, commands, args, and best practices for writing effective prompts.
- [x] 2. Add `__init__.py` to the skill package directory so `importlib.resources` can find it.
- [x] 3. Add a test that verifies the skill can be read via `read_bundled_skill("ralphify")` and contains expected content.
- [x] 4. Add a changelog entry documenting the new skill.

## Acceptance criteria

- `read_bundled_skill("ralphify")` returns the skill content without error
- The skill content covers: installation, CLI usage (run/new/init), RALPH.md format, frontmatter fields, placeholders, commands, args, and prompt-writing guidance
- All existing tests still pass
- New test validates the skill is readable and has expected sections
