# Plan: Render iteration result_text as markdown

## Summary

The `result_text` from iteration completions is currently displayed as plain dim text. Render it using Rich's built-in `Markdown` class so that agent output (which often contains markdown formatting like headers, bold, lists, code blocks) is displayed in a readable, formatted way in the terminal.

This change is added to the existing `pm/iteration-monitor-ui` branch and PR #3.

## Files to modify

- `src/ralphify/_console_emitter.py` — import `rich.markdown.Markdown` and use it to render `result_text` instead of plain text
- `tests/test_console_emitter.py` — update tests for `result_text` rendering to verify markdown rendering is used
- PR #3 — update title/description to mention markdown rendering

## Steps

- [x] 1. In `_console_emitter.py`, import `Markdown` from `rich.markdown` and change `_on_iteration_ended` to render `result_text` as Markdown instead of escaped dim text
- [x] 2. Update tests in `test_console_emitter.py` for the new markdown rendering behavior
- [x] 3. Run full test suite and verify everything passes
- [x] 4. Update PR #3 title and description to include the markdown rendering feature

## Acceptance criteria

- `result_text` containing markdown (headers, bold, lists, code blocks) renders formatted in the terminal
- Plain text `result_text` still displays correctly
- All existing tests pass
- PR #3 description reflects the new feature
