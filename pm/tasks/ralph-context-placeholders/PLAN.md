# Plan: Ralph context placeholders (name, iteration, max iterations)

## Summary

Add a new `{{ context.X }}` placeholder family so ralphs can access runtime metadata: their own name, current iteration number, and max iterations. This addresses [issue #14](https://github.com/computerlovetech/ralphify/issues/14). The placeholders are resolved alongside existing `{{ commands.X }}` and `{{ args.X }}` in a single pass.

## Files to modify

- `src/ralphify/_resolver.py` — Add `resolve_context()` and integrate into `resolve_all()`
- `src/ralphify/engine.py` — Pass context dict (name, iteration, max_iterations) to resolver
- `tests/test_resolver.py` — Tests for new `{{ context.X }}` placeholders
- `tests/test_engine.py` — Verify context placeholders flow through the engine
- `docs/writing-prompts.md` (or equivalent) — Document the new placeholders
- `docs/reference/quick-reference.md` (or equivalent) — Add context placeholders
- `src/ralphify/skills/new-ralph/SKILL.md` — Mention context placeholders

## Steps

- [x] 1. Add `resolve_context()` to `_resolver.py` and integrate into `resolve_all()` — support `{{ context.name }}`, `{{ context.iteration }}`, `{{ context.max_iterations }}`
- [x] 2. Update `engine.py` `_assemble_prompt()` to build and pass a context dict to the resolver
- [x] 3. Add unit tests in `test_resolver.py` for context placeholder resolution
- [x] 4. Add integration tests in `test_engine.py` verifying context flows end-to-end
- [x] 5. Update user-facing docs (writing prompts guide, quick reference, SKILL.md, changelog)

## Acceptance criteria

- `{{ context.name }}` resolves to the ralph directory name
- `{{ context.iteration }}` resolves to the current iteration number (1-based)
- `{{ context.max_iterations }}` resolves to the max iterations value, or empty string if unlimited
- All 431+ existing tests still pass
- New tests cover: basic resolution, missing context keys left untouched, unlimited max_iterations case
- Docs updated with examples
