# Plan: Improve iteration monitor UI coherence

## Summary

Address GitHub issue #12 — improve the visual coherence of the CLI output. The first bullet (ASCII art only on bare `ralph`) is already done. The remaining work: fix the banner's visual inconsistencies, tighten the run output formatting, and apply a consistent color/icon scheme across the console emitter.

## Files to modify

- `src/ralphify/cli.py` — fix banner ASCII art alignment (line 87 has extra trailing chars vs other lines), clean up tagline/help text spacing
- `src/ralphify/_console_emitter.py` — improve visual consistency: uniform indentation, consistent use of icons/colors, add a subtle run header
- `tests/test_cli.py` — update any banner-related tests if output changes
- `tests/test_console_emitter.py` — update assertions for changed output format

## Steps

- [x] 1. Fix ASCII art banner alignment — shortened tagline, added version, removed redundant help/star lines
- [ ] 2. Improve run output header — add a compact run header line when `ralph run` starts (e.g. ralph name + iteration count if set) so the output has a clear starting point
- [ ] 3. Unify console emitter formatting — make iteration blocks visually consistent: standardize indentation of sub-items (commands, result text), use the same icon style for all status lines
- [ ] 4. Polish run summary line — improve the `Done:` line formatting to match the iteration style (icons, alignment)
- [ ] 5. Run full test suite and fix any broken assertions

## Acceptance criteria

- `uv run pytest` passes with zero failures
- `ralph` (no subcommand) shows a cleanly aligned banner with no ragged edges
- `ralph run` output has a clear visual hierarchy: run header → iteration blocks → summary
- All status lines (success, failure, timeout) use consistent formatting
- No functional behavior changes — only visual output changes
