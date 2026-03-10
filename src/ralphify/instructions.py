import re
from dataclasses import dataclass
from pathlib import Path

from ralphify._frontmatter import discover_primitives
from ralphify.resolver import resolve_placeholders


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
    return [
        Instruction(
            name=entry.name,
            path=entry,
            enabled=frontmatter.get("enabled", True),
            content=body,
        )
        for entry, frontmatter, body in discover_primitives(root, "instructions", "INSTRUCTION.md")
    ]


def resolve_instructions(prompt: str, instructions: list[Instruction]) -> str:
    """Replace instruction placeholders in a prompt string.

    - {{ instructions.<name> }} → specific instruction content
    - {{ instructions }} → all enabled instructions not already placed
    - If no placeholders found → append all at end
    """
    available = {i.name: i.content for i in instructions if i.enabled and i.content}
    return resolve_placeholders(prompt, available, _NAMED_PATTERN, _BULK_PATTERN)
