"""Template placeholder resolution for commands and args.

Only named placeholders are supported:

``{{ kind.name }}`` inserts a specific value's content.

Items not referenced by a named placeholder are excluded from the
prompt.  This forces explicit placement and avoids accidental data dumps.
"""

import re
from functools import lru_cache


@lru_cache(maxsize=2)
def _get_pattern(kind: str) -> re.Pattern[str]:
    """Return a compiled regex for the given placeholder kind, caching the result."""
    return re.compile(
        r"\{\{\s*" + re.escape(kind) + r"\.([a-zA-Z0-9_-]+)\s*\}\}"
    )


def resolve_placeholders(
    prompt: str,
    available: dict[str, str],
    kind: str,
) -> str:
    """Replace named template placeholders in a prompt string.

    *kind* is the placeholder category (e.g. "commands", "args").

    - ``{{ kind.name }}`` → replaced with the matching content
    - Unknown names → replaced with empty string
    - Unreferenced items are silently excluded
    """
    if not available:
        return prompt

    named_pattern = _get_pattern(kind)

    def _replace_named(match: re.Match) -> str:
        name = match.group(1)
        if name in available:
            return available[name]
        return ""

    return named_pattern.sub(_replace_named, prompt)


def _resolve_kind(prompt: str, available: dict[str, str], kind: str) -> str:
    """Resolve placeholders of a given *kind*, clearing them when *available* is empty."""
    if not available:
        return _get_pattern(kind).sub("", prompt)
    return resolve_placeholders(prompt, available, kind)


def resolve_commands(prompt: str, command_outputs: dict[str, str]) -> str:
    """Replace ``{{ commands.name }}`` placeholders with command outputs.

    When *command_outputs* is empty, clears any remaining
    ``{{ commands.* }}`` placeholders so they don't leak into the
    assembled prompt.
    """
    return _resolve_kind(prompt, command_outputs, "commands")


def resolve_args(prompt: str, user_args: dict[str, str]) -> str:
    """Replace ``{{ args.name }}`` placeholders with user-supplied values.

    When *user_args* is empty, clears any remaining ``{{ args.* }}``
    placeholders so they don't leak into the assembled prompt.
    """
    return _resolve_kind(prompt, user_args, "args")
