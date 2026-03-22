# Plan: Improve iteration monitor UI

## Summary

Improve the `ralph run` iteration monitor UI to be more coherent and polished (issue #12). The ASCII art banner is already correctly scoped to `ralph` with no subcommand — no change needed there. The focus is on making the `ralph run` output more visually consistent: add a run header, improve iteration formatting, and polish the summary.

## Notes

- Issue mentions "Read simplify UX research" but no such file exists in the repo. Proceeding with sensible UI improvements.
- The ASCII art already only shows when running `ralph` with no subcommand (item 1 of the issue is already done).

## Files to modify

- `src/ralphify/_console_emitter.py` — improve iteration monitor rendering (header, iteration blocks, summary)
- `tests/test_console_emitter.py` — update tests for any changed output

## Steps

- [x] 1. Add a run header to `_on_run_started` — show a styled "Ralph is running" header with the ralph name, plus the existing timeout/commands info, to give a clear visual start to each run
- [x] 2. Improve iteration block formatting — add consistent indentation for iteration content (commands, log file), use a cleaner separator style, and show iteration duration inline with the status icon
- [x] 3. Polish the run summary in `_on_run_stopped` — add a visual separator before the summary, show elapsed total time if available, and make the Done line more visually distinct
- [x] 4. Update tests to match the new output format
- [x] 5. Manual review — run `ralph` and `ralph run --help` to verify banner behavior is unchanged

## Acceptance criteria

- `ralph` (no subcommand) still shows the ASCII banner + help
- `ralph run` shows a polished, coherent iteration monitor with: run header, clean iteration blocks, and a styled summary
- All tests pass
- No new dependencies added
