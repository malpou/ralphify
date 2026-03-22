"""Fleet configuration and orchestration for running multiple ralphs.

A fleet is a group of ralphs that run in parallel, each in its own git
worktree.  The fleet is defined by a ``fleet.yml`` file that specifies
which ralphs to run, their branches, and orchestration settings.
"""

from __future__ import annotations

import subprocess
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


# ---------------------------------------------------------------------------
# Worktree lifecycle
# ---------------------------------------------------------------------------

_SUBPROCESS_KWARGS = {"capture_output": True, "text": True, "encoding": "utf-8"}


class WorktreeError(Exception):
    """Raised when a git worktree operation fails."""


def _run_git(args: list[str], *, cwd: Path) -> subprocess.CompletedProcess[str]:
    """Run a git command, raising :class:`WorktreeError` on failure."""
    cmd = ["git", *args]
    result = subprocess.run(cmd, cwd=cwd, **_SUBPROCESS_KWARGS)
    if result.returncode != 0:
        raise WorktreeError(
            f"git {' '.join(args)} failed (rc={result.returncode}): "
            f"{result.stderr.strip()}"
        )
    return result


def create_worktree(
    *,
    repo_root: Path,
    worktree_path: Path,
    branch: str,
) -> Path:
    """Create a git worktree for a ralph at *worktree_path* on *branch*.

    If the branch does not exist, it is created from HEAD.  Returns the
    resolved worktree path.

    Raises :class:`WorktreeError` if the worktree already exists or the
    git command fails.
    """
    if worktree_path.exists():
        raise WorktreeError(f"Worktree path already exists: {worktree_path}")

    # Check if the branch exists
    check = subprocess.run(
        ["git", "rev-parse", "--verify", branch],
        cwd=repo_root,
        **_SUBPROCESS_KWARGS,
    )
    if check.returncode == 0:
        # Branch exists — check it out in the new worktree
        _run_git(["worktree", "add", str(worktree_path), branch], cwd=repo_root)
    else:
        # Branch doesn't exist — create it with -b
        _run_git(
            ["worktree", "add", "-b", branch, str(worktree_path)],
            cwd=repo_root,
        )

    return worktree_path.resolve()


def remove_worktree(*, repo_root: Path, worktree_path: Path) -> None:
    """Remove a git worktree at *worktree_path*.

    Uses ``git worktree remove --force`` to handle dirty worktrees.
    Raises :class:`WorktreeError` if the removal fails.
    """
    _run_git(
        ["worktree", "remove", "--force", str(worktree_path)],
        cwd=repo_root,
    )


def prune_worktrees(*, repo_root: Path) -> None:
    """Prune stale worktree metadata from the repository.

    This cleans up administrative data for worktrees whose directories
    have been deleted externally (e.g. ``rm -rf``).
    """
    _run_git(["worktree", "prune"], cwd=repo_root)


def setup_fleet_worktrees(
    *, config: FleetConfig, repo_root: Path
) -> dict[str, Path]:
    """Create worktrees for all ralphs in a fleet that have ``worktree=True``.

    Returns a mapping of ralph name → resolved worktree path.  Ralphs
    with ``worktree=False`` are skipped (they run in the main working
    tree) and their path is set to *repo_root*.

    State directory is created if it doesn't exist.
    """
    base = repo_root / config.worktree_dir
    state = repo_root / config.state_dir
    state.mkdir(parents=True, exist_ok=True)

    paths: dict[str, Path] = {}
    for entry in config.ralphs:
        if not entry.worktree:
            paths[entry.name] = repo_root
            continue

        wt_path = base / entry.name
        paths[entry.name] = create_worktree(
            repo_root=repo_root,
            worktree_path=wt_path,
            branch=entry.branch,
        )

    return paths


def teardown_fleet_worktrees(
    *, config: FleetConfig, repo_root: Path
) -> None:
    """Remove all worktrees created for a fleet and prune stale metadata."""
    base = repo_root / config.worktree_dir

    for entry in config.ralphs:
        if not entry.worktree:
            continue
        wt_path = base / entry.name
        if wt_path.exists():
            try:
                remove_worktree(repo_root=repo_root, worktree_path=wt_path)
            except WorktreeError:
                pass  # Best-effort cleanup

    prune_worktrees(repo_root=repo_root)

    # Remove the worktree base directory if empty
    if base.exists() and not any(base.iterdir()):
        base.rmdir()
