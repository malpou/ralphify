"""Template placeholder resolution for contexts and args.

Only named placeholders are supported:

``{{ kind.name }}`` inserts a specific primitive's content.

Contexts not referenced by a named placeholder are excluded from the
prompt.  This forces explicit placement and avoids accidental data dumps.
"""

import re


def resolve_placeholders(
    prompt: str,
    available: dict[str, str],
    kind: str,
) -> str:
    """Replace named template placeholders in a prompt string.

    *kind* is the placeholder category (e.g. "contexts").

    - ``{{ kind.name }}`` → replaced with the matching content
    - Unknown names → replaced with empty string
    - Unreferenced items are silently excluded
    """
    if not available:
        return prompt

    named_pattern = re.compile(r"\{\{\s*" + re.escape(kind) + r"\.([a-zA-Z0-9_-]+)\s*\}\}")

    def _replace_named(match: re.Match) -> str:
        name = match.group(1)
        if name in available:
            return available[name]
        return ""

    return named_pattern.sub(_replace_named, prompt)


def resolve_args(prompt: str, user_args: dict[str, str]) -> str:
    """Replace ``{{ args.name }}`` placeholders with user-supplied values.

    Delegates to :func:`resolve_placeholders` with ``kind="args"``.
    When *user_args* is empty, clears any remaining ``{{ args.* }}``
    placeholders so they don't leak into the assembled prompt.
    """
    if not user_args:
        # Clear unmatched args placeholders
        return re.sub(r"\{\{\s*args\.[a-zA-Z0-9_-]+\s*\}\}", "", prompt)
    return resolve_placeholders(prompt, user_args, "args")
