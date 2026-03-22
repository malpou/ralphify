"""Fleet configuration and orchestration for running multiple ralphs.

A fleet is a group of ralphs that run in parallel, each in its own git
worktree.  The fleet is defined by a ``fleet.yml`` file that specifies
which ralphs to run, their branches, and orchestration settings.
"""

from __future__ import annotations

import subprocess
import threading
import time
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path

import yaml

from ralphify._frontmatter import (
    CMD_FIELD_NAME,
    CMD_FIELD_RUN,
    CMD_FIELD_TIMEOUT,
    FIELD_AGENT,
    FIELD_COMMANDS,
    FIELD_CREDIT,
    RALPH_MARKER,
    parse_frontmatter,
)
from ralphify._run_types import Command, DEFAULT_COMMAND_TIMEOUT, RunConfig, RunStatus
from ralphify.manager import RunManager


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


# ---------------------------------------------------------------------------
# Fleet orchestration
# ---------------------------------------------------------------------------


class FleetStatus(Enum):
    """Lifecycle status of a fleet."""

    PENDING = "pending"
    STARTING = "starting"
    RUNNING = "running"
    STOPPING = "stopping"
    STOPPED = "stopped"


@dataclass
class RalphStatus:
    """Status snapshot for a single ralph in the fleet."""

    name: str
    run_id: str | None = None
    run_status: RunStatus = RunStatus.PENDING
    worktree_path: Path | None = None
    iteration: int = 0
    completed: int = 0
    failed: int = 0


class FleetConfigError(Exception):
    """Raised when a ralph's RALPH.md is missing or invalid."""


def _build_run_config_from_entry(
    entry: RalphEntry,
    worktree_path: Path,
    repo_root: Path,
    state_dir: Path,
) -> RunConfig:
    """Build a :class:`RunConfig` from a fleet ralph entry.

    Reads the RALPH.md file from *worktree_path* (or *repo_root* if the
    ralph runs without a worktree), parses its frontmatter, and returns
    a fully-populated config.

    Raises :class:`FleetConfigError` if the file is missing or invalid.
    """
    ralph_file = worktree_path / entry.file
    if ralph_file.name == RALPH_MARKER and ralph_file.is_file():
        ralph_dir = ralph_file.parent
    elif ralph_file.is_dir():
        ralph_dir = ralph_file
        ralph_file = ralph_file / RALPH_MARKER
    else:
        raise FleetConfigError(
            f"Ralph '{entry.name}': file '{entry.file}' not found "
            f"in {worktree_path}"
        )

    if not ralph_file.exists():
        raise FleetConfigError(
            f"Ralph '{entry.name}': {RALPH_MARKER} not found at '{ralph_file}'"
        )

    text = ralph_file.read_text(encoding="utf-8")
    fm, _ = parse_frontmatter(text)

    agent = fm.get(FIELD_AGENT)
    if not isinstance(agent, str) or not agent.strip():
        raise FleetConfigError(
            f"Ralph '{entry.name}': missing or empty '{FIELD_AGENT}' "
            f"in {RALPH_MARKER} frontmatter"
        )

    commands: list[Command] = []
    raw_commands = fm.get(FIELD_COMMANDS)
    if raw_commands is not None:
        if not isinstance(raw_commands, list):
            raise FleetConfigError(
                f"Ralph '{entry.name}': '{FIELD_COMMANDS}' must be a list"
            )
        for cmd_def in raw_commands:
            if not isinstance(cmd_def, dict):
                raise FleetConfigError(
                    f"Ralph '{entry.name}': each command must be a mapping"
                )
            name = cmd_def.get(CMD_FIELD_NAME, "")
            run_cmd = cmd_def.get(CMD_FIELD_RUN, "")
            if not name or not run_cmd:
                raise FleetConfigError(
                    f"Ralph '{entry.name}': commands need "
                    f"'{CMD_FIELD_NAME}' and '{CMD_FIELD_RUN}'"
                )
            timeout = cmd_def.get(CMD_FIELD_TIMEOUT, DEFAULT_COMMAND_TIMEOUT)
            commands.append(Command(name=name, run=run_cmd, timeout=float(timeout)))

    credit = fm.get(FIELD_CREDIT, True)
    log_dir = state_dir / entry.name / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)

    return RunConfig(
        agent=agent,
        ralph_dir=ralph_dir.resolve(),
        ralph_file=ralph_file.resolve(),
        commands=commands,
        max_iterations=None,
        delay=0,
        timeout=None,
        stop_on_error=False,
        log_dir=log_dir,
        project_root=worktree_path,
        credit=credit if isinstance(credit, bool) else True,
    )


class FleetOrchestrator:
    """Manage a fleet of ralphs running in git worktrees.

    The orchestrator handles the full lifecycle: set up worktrees, build
    run configs, launch ralphs via :class:`RunManager` with staggered
    starts and dependency ordering, and provide stop/status methods.
    """

    def __init__(self, config: FleetConfig, repo_root: Path) -> None:
        self._config = config
        self._repo_root = repo_root.resolve()
        self._manager = RunManager()
        self._status = FleetStatus.PENDING
        self._worktree_paths: dict[str, Path] = {}
        self._ralph_run_ids: dict[str, str] = {}
        self._lock = threading.Lock()

    @property
    def status(self) -> FleetStatus:
        return self._status

    @property
    def config(self) -> FleetConfig:
        return self._config

    def start(self) -> None:
        """Set up worktrees and launch all ralphs.

        Ralphs are started in dependency order with staggered delays.
        Raises :class:`FleetConfigError` if any ralph config is invalid.
        Raises :class:`WorktreeError` if worktree setup fails.
        """
        with self._lock:
            if self._status not in (FleetStatus.PENDING, FleetStatus.STOPPED):
                raise RuntimeError(f"Cannot start fleet in {self._status.value} state")
            self._status = FleetStatus.STARTING

        # Set up worktrees
        self._worktree_paths = setup_fleet_worktrees(
            config=self._config, repo_root=self._repo_root
        )

        state_dir = self._repo_root / self._config.state_dir

        # Build run configs for all ralphs
        run_configs: dict[str, RunConfig] = {}
        for entry in self._config.ralphs:
            wt_path = self._worktree_paths[entry.name]
            run_configs[entry.name] = _build_run_config_from_entry(
                entry, wt_path, self._repo_root, state_dir
            )

        # Create all runs (but don't start them yet)
        for entry in self._config.ralphs:
            managed = self._manager.create_run(run_configs[entry.name])
            self._ralph_run_ids[entry.name] = managed.state.run_id

        # Start ralphs in dependency order with stagger
        started: set[str] = set()
        launch_order = self._resolve_launch_order()
        max_concurrent = self._config.settings.max_concurrent
        stagger = self._config.settings.stagger_start

        for name in launch_order:
            # Wait for dependencies to be running
            entry = self._get_entry(name)
            for dep in entry.depends_on:
                self._wait_for_running(dep)

            # Respect max_concurrent: wait until a slot opens
            if max_concurrent > 0:
                while self._count_active_runs() >= max_concurrent:
                    time.sleep(0.5)

            run_id = self._ralph_run_ids[name]
            self._manager.start_run(run_id)
            started.add(name)

            # Stagger start delay (skip after last ralph)
            if stagger > 0 and len(started) < len(launch_order):
                time.sleep(stagger)

        with self._lock:
            self._status = FleetStatus.RUNNING

    def stop(self) -> None:
        """Stop all running ralphs and tear down worktrees."""
        with self._lock:
            if self._status not in (FleetStatus.RUNNING, FleetStatus.STARTING):
                return
            self._status = FleetStatus.STOPPING

        # Signal all runs to stop
        for run_id in self._ralph_run_ids.values():
            try:
                self._manager.stop_run(run_id)
            except KeyError:
                pass

        # Wait for all threads to finish
        for managed in self._manager.list_runs():
            if managed.thread is not None:
                managed.thread.join(timeout=30)

        # Tear down worktrees
        teardown_fleet_worktrees(
            config=self._config, repo_root=self._repo_root
        )

        with self._lock:
            self._status = FleetStatus.STOPPED

    def get_ralph_statuses(self) -> list[RalphStatus]:
        """Return status snapshots for all ralphs in the fleet."""
        statuses: list[RalphStatus] = []
        for entry in self._config.ralphs:
            run_id = self._ralph_run_ids.get(entry.name)
            rs = RalphStatus(
                name=entry.name,
                worktree_path=self._worktree_paths.get(entry.name),
            )
            if run_id:
                managed = self._manager.get_run(run_id)
                if managed:
                    rs.run_id = run_id
                    rs.run_status = managed.state.status
                    rs.iteration = managed.state.iteration
                    rs.completed = managed.state.completed
                    rs.failed = managed.state.failed
            statuses.append(rs)
        return statuses

    def stop_ralph(self, name: str) -> None:
        """Stop a single ralph by name."""
        run_id = self._ralph_run_ids.get(name)
        if run_id is None:
            raise KeyError(f"No ralph named '{name}' in fleet")
        self._manager.stop_run(run_id)

    def _get_entry(self, name: str) -> RalphEntry:
        """Look up a ralph entry by name."""
        for entry in self._config.ralphs:
            if entry.name == name:
                return entry
        raise KeyError(f"No ralph named '{name}'")

    def _resolve_launch_order(self) -> list[str]:
        """Topological sort of ralphs by depends_on, preserving priority order.

        Raises :class:`ValueError` if there is a circular dependency.
        """
        # Build adjacency: name -> set of names it depends on
        deps: dict[str, set[str]] = {
            e.name: set(e.depends_on) for e in self._config.ralphs
        }
        # Priority-ordered names as fallback ordering
        priority_order = [e.name for e in self._config.ralphs]

        order: list[str] = []
        visited: set[str] = set()
        visiting: set[str] = set()

        def visit(name: str) -> None:
            if name in visited:
                return
            if name in visiting:
                raise ValueError(f"Circular dependency involving '{name}'")
            visiting.add(name)
            for dep in deps.get(name, set()):
                visit(dep)
            visiting.remove(name)
            visited.add(name)
            order.append(name)

        for name in priority_order:
            visit(name)

        return order

    def _wait_for_running(self, name: str, timeout: float = 60) -> None:
        """Wait until a ralph has started its first iteration."""
        run_id = self._ralph_run_ids.get(name)
        if run_id is None:
            return
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            managed = self._manager.get_run(run_id)
            if managed and managed.state.status in (
                RunStatus.RUNNING,
                RunStatus.COMPLETED,
                RunStatus.STOPPED,
                RunStatus.FAILED,
            ):
                return
            time.sleep(0.5)

    def _count_active_runs(self) -> int:
        """Count runs that are currently active (running or paused)."""
        count = 0
        for managed in self._manager.list_runs():
            if managed.state.status in (RunStatus.RUNNING, RunStatus.PAUSED):
                count += 1
        return count
