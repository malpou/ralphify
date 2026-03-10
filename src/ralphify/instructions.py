import re
from dataclasses import dataclass
from pathlib import Path

from ralphify.checks import parse_check_md


@dataclass
class Instruction:
    name: str
    path: Path
    enabled: bool = True
    content: str = ""


_NAMED_PATTERN = re.compile(r"\{\{\s*instructions\.([a-zA-Z0-9_-]+)\s*\}\}")
_BULK_PATTERN = re.compile(r"\{\{\s*instructions\s*\}\}")


def discover_instructions(root: Path = Path(".")) -> list[Instruction]:
    """Discover instructions in root/.ralph/instructions/ directories."""
    instructions_dir = root / ".ralph" / "instructions"
    if not instructions_dir.is_dir():
        return []

    instructions = []
    for entry in sorted(instructions_dir.iterdir()):
        if not entry.is_dir():
            continue

        instruction_md = entry / "INSTRUCTION.md"
        if not instruction_md.exists():
            continue

        text = instruction_md.read_text()
        frontmatter, body = parse_check_md(text)

        instructions.append(
            Instruction(
                name=entry.name,
                path=entry,
                enabled=frontmatter.get("enabled", True),
                content=body,
            )
        )

    return instructions


def resolve_instructions(prompt: str, instructions: list[Instruction]) -> str:
    """Replace instruction placeholders in a prompt string.

    - {{ instructions.<name> }} → specific instruction content
    - {{ instructions }} → all enabled instructions not already placed
    - If no placeholders found → append all at end
    """
    available = {i.name: i.content for i in instructions if i.enabled and i.content}

    if not available:
        return prompt

    placed: set[str] = set()
    has_named = False

    def _replace_named(match: re.Match) -> str:
        nonlocal has_named
        has_named = True
        name = match.group(1)
        if name in available:
            placed.add(name)
            return available[name]
        return ""

    result = _NAMED_PATTERN.sub(_replace_named, prompt)

    has_bulk = _BULK_PATTERN.search(result) is not None

    remaining = [content for name, content in sorted(available.items()) if name not in placed]
    bulk_text = "\n\n".join(remaining)

    if has_bulk:
        result = _BULK_PATTERN.sub(bulk_text, result)
    elif not has_named and not has_bulk:
        # No placeholders found at all → append
        if bulk_text:
            result = result + "\n\n" + bulk_text

    return result
