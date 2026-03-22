"""Fleet configuration and orchestration for running multiple ralphs.

A fleet is a group of ralphs that run in parallel, each in its own git
worktree.  The fleet is defined by a ``fleet.yml`` file that specifies
which ralphs to run, their branches, and orchestration settings.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import yaml


FLEET_MARKER = "fleet.yml"
"""Default filename for fleet definitions."""


@dataclass
class RalphEntry:
    """A single ralph within a fleet definition."""

    name: str
    file: str
    branch: str
    worktree: bool = True
    priority: int = 0
    depends_on: list[str] = field(default_factory=list)


@dataclass
class FleetSettings:
    """Orchestration settings for the fleet."""

    max_concurrent: int = 0
    stagger_start: float = 0
    merge_strategy: str = "fifo"
    health_check_interval: float = 60


@dataclass
class FleetConfig:
    """Parsed fleet definition from ``fleet.yml``."""

    name: str
    worktree_dir: str = ".trees"
    state_dir: str = ".ralph/state"
    ralphs: list[RalphEntry] = field(default_factory=list)
    settings: FleetSettings = field(default_factory=FleetSettings)


def _parse_stagger(value: str | int | float) -> float:
    """Parse a stagger_start value, accepting ``"30s"`` or plain numbers."""
    if isinstance(value, (int, float)):
        return float(value)
    s = str(value).strip().lower()
    if s.endswith("s"):
        s = s[:-1]
    try:
        return float(s)
    except ValueError:
        raise ValueError(f"Invalid stagger_start value: {value!r}") from None


def parse_fleet_config(path: Path) -> FleetConfig:
    """Parse a ``fleet.yml`` file into a :class:`FleetConfig`.

    Raises :class:`ValueError` for missing required fields or invalid
    values.  Raises :class:`FileNotFoundError` if the file does not exist.
    """
    if not path.is_file():
        raise FileNotFoundError(f"Fleet config not found: {path}")

    text = path.read_text(encoding="utf-8")
    data = yaml.safe_load(text)
    if not isinstance(data, dict):
        raise ValueError(f"Fleet config must be a YAML mapping, got {type(data).__name__}")

    fleet_section = data.get("fleet", {})
    if not isinstance(fleet_section, dict):
        raise ValueError("'fleet' must be a mapping")

    name = fleet_section.get("name")
    if not name or not isinstance(name, str):
        raise ValueError("'fleet.name' is required and must be a non-empty string")

    worktree_dir = fleet_section.get("worktree_dir", ".trees")
    state_dir = fleet_section.get("state_dir", ".ralph/state")

    # Parse ralph entries
    ralphs_section = data.get("ralphs", {})
    if not isinstance(ralphs_section, dict):
        raise ValueError("'ralphs' must be a mapping")

    ralph_entries: list[RalphEntry] = []
    for ralph_name, ralph_data in ralphs_section.items():
        if not isinstance(ralph_data, dict):
            raise ValueError(f"Ralph '{ralph_name}' must be a mapping")

        file_path = ralph_data.get("file")
        if not file_path or not isinstance(file_path, str):
            raise ValueError(f"Ralph '{ralph_name}' must have a 'file' string field")

        branch = ralph_data.get("branch", f"ralph/{ralph_name}")
        worktree = ralph_data.get("worktree", True)
        priority = ralph_data.get("priority", 0)
        depends_on = ralph_data.get("depends_on", [])

        if not isinstance(worktree, bool):
            raise ValueError(f"Ralph '{ralph_name}.worktree' must be a boolean")
        if not isinstance(priority, int):
            raise ValueError(f"Ralph '{ralph_name}.priority' must be an integer")
        if not isinstance(depends_on, list):
            raise ValueError(f"Ralph '{ralph_name}.depends_on' must be a list")

        ralph_entries.append(
            RalphEntry(
                name=ralph_name,
                file=file_path,
                branch=branch,
                worktree=worktree,
                priority=priority,
                depends_on=depends_on,
            )
        )

    # Sort by priority (higher first), then by name for stability
    ralph_entries.sort(key=lambda r: (-r.priority, r.name))

    # Validate depends_on references
    known_names = {r.name for r in ralph_entries}
    for entry in ralph_entries:
        for dep in entry.depends_on:
            if dep not in known_names:
                raise ValueError(
                    f"Ralph '{entry.name}' depends on unknown ralph '{dep}'"
                )

    # Parse settings
    settings_section = data.get("settings", {})
    if not isinstance(settings_section, dict):
        raise ValueError("'settings' must be a mapping")

    settings = FleetSettings(
        max_concurrent=settings_section.get("max_concurrent", 0),
        stagger_start=_parse_stagger(settings_section.get("stagger_start", 0)),
        merge_strategy=settings_section.get("merge_strategy", "fifo"),
        health_check_interval=float(settings_section.get("health_check_interval", 60)),
    )

    return FleetConfig(
        name=name,
        worktree_dir=worktree_dir,
        state_dir=state_dir,
        ralphs=ralph_entries,
        settings=settings,
    )
