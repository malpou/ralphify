# Plan: Add context placeholders for ralph name, iteration, and max_iterations

## Summary

Allow ralph prompts to use `{{ context.name }}`, `{{ context.iteration }}`, and `{{ context.max_iterations }}` placeholders so the agent knows its own identity and progress through the loop. Closes #14.

## Files to modify

- `src/ralphify/_frontmatter.py` — add `FIELD_CONTEXT = "context"` constant
- `src/ralphify/_resolver.py` — extend `_ALL_PATTERN` and `resolve_all` to support `context` as a third placeholder kind
- `src/ralphify/engine.py` — build context dict and pass it to `resolve_all` / `_assemble_prompt`
- `tests/test_resolver.py` — add tests for context placeholders
- `tests/test_engine.py` — add test verifying context values appear in assembled prompt
- `docs/writing-prompts.md` (or equivalent) — document the new placeholders
- `src/ralphify/skills/new-ralph/SKILL.md` — mention context placeholders

## Steps

- [ ] 1. Add `FIELD_CONTEXT` constant to `_frontmatter.py` and update `_resolver.py` to support `{{ context.<name> }}` as a third placeholder kind in `resolve_all`
- [ ] 2. Update `engine.py` to build the context dict (`name`, `iteration`, `max_iterations`) and pass it through `_assemble_prompt` to `resolve_all`
- [ ] 3. Add resolver tests for context placeholders in `tests/test_resolver.py`
- [ ] 4. Add engine test verifying context values appear in assembled prompt
- [ ] 5. Update docs and SKILL.md to document context placeholders

## Acceptance criteria

- `{{ context.name }}` resolves to the ralph directory name
- `{{ context.iteration }}` resolves to the current iteration number (1-based)
- `{{ context.max_iterations }}` resolves to the configured max or empty string if unlimited
- Existing `{{ commands.* }}` and `{{ args.* }}` placeholders still work
- All tests pass
- Docs updated
