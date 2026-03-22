"""Tests for fleet configuration, worktree lifecycle, and orchestration."""

from __future__ import annotations

import subprocess
from pathlib import Path
from unittest.mock import MagicMock, call, patch

import pytest

from ralphify._fleet import (
    FLEET_MARKER,
    FleetConfig,
    FleetOrchestrator,
    FleetSettings,
    FleetStatus,
    RalphEntry,
    RalphStatus,
    WorktreeError,
    _parse_stagger,
    create_worktree,
    parse_fleet_config,
    prune_worktrees,
    remove_worktree,
    setup_fleet_worktrees,
    teardown_fleet_worktrees,
)
from ralphify._run_types import RunStatus

MOCK_FLEET_SUBPROCESS = "ralphify._fleet.subprocess.run"


# ── Helpers ──────────────────────────────────────────────────────────


def _write_fleet_yml(path: Path, content: str) -> Path:
    """Write a fleet.yml file and return its path."""
    fleet_file = path / FLEET_MARKER
    fleet_file.write_text(content)
    return fleet_file


def _minimal_fleet_yml() -> str:
    return (
        "fleet:\n"
        "  name: test-fleet\n"
        "ralphs:\n"
        "  alpha:\n"
        "    file: ralphs/alpha/RALPH.md\n"
    )


def _multi_ralph_fleet_yml() -> str:
    return (
        "fleet:\n"
        "  name: multi-fleet\n"
        "  worktree_dir: .wt\n"
        "  state_dir: .state\n"
        "ralphs:\n"
        "  pm:\n"
        "    file: ralphs/pm/RALPH.md\n"
        "    branch: ralph/pm\n"
        "    priority: 10\n"
        "  dev:\n"
        "    file: ralphs/dev/RALPH.md\n"
        "    branch: ralph/dev\n"
        "    priority: 5\n"
        "    depends_on:\n"
        "      - pm\n"
        "  qa:\n"
        "    file: ralphs/qa/RALPH.md\n"
        "    worktree: false\n"
        "    priority: 0\n"
        "settings:\n"
        "  max_concurrent: 2\n"
        "  stagger_start: 5s\n"
        "  merge_strategy: fifo\n"
        "  health_check_interval: 30\n"
    )


# ── parse_fleet_config ───────────────────────────────────────────────


class TestParseFleetConfig:
    def test_minimal_config(self, tmp_path):
        fleet_file = _write_fleet_yml(tmp_path, _minimal_fleet_yml())
        config = parse_fleet_config(fleet_file)

        assert config.name == "test-fleet"
        assert config.worktree_dir == ".trees"
        assert config.state_dir == ".ralph/state"
        assert len(config.ralphs) == 1
        assert config.ralphs[0].name == "alpha"
        assert config.ralphs[0].file == "ralphs/alpha/RALPH.md"
        assert config.ralphs[0].branch == "ralph/alpha"
        assert config.ralphs[0].worktree is True
        assert config.ralphs[0].priority == 0
        assert config.ralphs[0].depends_on == []

    def test_full_config(self, tmp_path):
        fleet_file = _write_fleet_yml(tmp_path, _multi_ralph_fleet_yml())
        config = parse_fleet_config(fleet_file)

        assert config.name == "multi-fleet"
        assert config.worktree_dir == ".wt"
        assert config.state_dir == ".state"
        assert len(config.ralphs) == 3

        # Sorted by priority descending then name
        assert config.ralphs[0].name == "pm"
        assert config.ralphs[0].priority == 10
        assert config.ralphs[1].name == "dev"
        assert config.ralphs[1].priority == 5
        assert config.ralphs[1].depends_on == ["pm"]
        assert config.ralphs[2].name == "qa"
        assert config.ralphs[2].worktree is False

    def test_settings_parsed(self, tmp_path):
        fleet_file = _write_fleet_yml(tmp_path, _multi_ralph_fleet_yml())
        config = parse_fleet_config(fleet_file)

        assert config.settings.max_concurrent == 2
        assert config.settings.stagger_start == 5.0
        assert config.settings.merge_strategy == "fifo"
        assert config.settings.health_check_interval == 30.0

    def test_default_settings(self, tmp_path):
        fleet_file = _write_fleet_yml(tmp_path, _minimal_fleet_yml())
        config = parse_fleet_config(fleet_file)

        assert config.settings.max_concurrent == 0
        assert config.settings.stagger_start == 0
        assert config.settings.merge_strategy == "fifo"
        assert config.settings.health_check_interval == 60

    def test_file_not_found(self, tmp_path):
        with pytest.raises(FileNotFoundError, match="Fleet config not found"):
            parse_fleet_config(tmp_path / "nonexistent.yml")

    def test_invalid_yaml_type(self, tmp_path):
        fleet_file = _write_fleet_yml(tmp_path, "just a string")
        with pytest.raises(ValueError, match="must be a YAML mapping"):
            parse_fleet_config(fleet_file)

    def test_missing_fleet_name(self, tmp_path):
        fleet_file = _write_fleet_yml(tmp_path, "fleet:\n  worktree_dir: .trees\n")
        with pytest.raises(ValueError, match="fleet.name"):
            parse_fleet_config(fleet_file)

    def test_invalid_ralphs_type(self, tmp_path):
        content = "fleet:\n  name: test\nralphs: not-a-mapping\n"
        fleet_file = _write_fleet_yml(tmp_path, content)
        with pytest.raises(ValueError, match="'ralphs' must be a mapping"):
            parse_fleet_config(fleet_file)

    def test_ralph_missing_file(self, tmp_path):
        content = (
            "fleet:\n"
            "  name: test\n"
            "ralphs:\n"
            "  bad:\n"
            "    branch: main\n"
        )
        fleet_file = _write_fleet_yml(tmp_path, content)
        with pytest.raises(ValueError, match="must have a 'file' string field"):
            parse_fleet_config(fleet_file)

    def test_invalid_depends_on_reference(self, tmp_path):
        content = (
            "fleet:\n"
            "  name: test\n"
            "ralphs:\n"
            "  a:\n"
            "    file: a.md\n"
            "    depends_on:\n"
            "      - nonexistent\n"
        )
        fleet_file = _write_fleet_yml(tmp_path, content)
        with pytest.raises(ValueError, match="depends on unknown ralph"):
            parse_fleet_config(fleet_file)

    def test_invalid_worktree_type(self, tmp_path):
        content = (
            "fleet:\n"
            "  name: test\n"
            "ralphs:\n"
            "  a:\n"
            "    file: a.md\n"
            "    worktree: maybe\n"
        )
        fleet_file = _write_fleet_yml(tmp_path, content)
        with pytest.raises(ValueError, match="worktree.*must be a boolean"):
            parse_fleet_config(fleet_file)

    def test_invalid_priority_type(self, tmp_path):
        content = (
            "fleet:\n"
            "  name: test\n"
            "ralphs:\n"
            "  a:\n"
            "    file: a.md\n"
            "    priority: high\n"
        )
        fleet_file = _write_fleet_yml(tmp_path, content)
        with pytest.raises(ValueError, match="priority.*must be an integer"):
            parse_fleet_config(fleet_file)


# ── _parse_stagger ───────────────────────────────────────────────────


class TestParseStagger:
    def test_integer(self):
        assert _parse_stagger(10) == 10.0

    def test_float(self):
        assert _parse_stagger(2.5) == 2.5

    def test_string_with_s_suffix(self):
        assert _parse_stagger("30s") == 30.0

    def test_plain_string_number(self):
        assert _parse_stagger("15") == 15.0

    def test_invalid_string(self):
        with pytest.raises(ValueError, match="Invalid stagger_start"):
            _parse_stagger("fast")


# ── Worktree lifecycle ───────────────────────────────────────────────


def _ok_git(*args, **kwargs):
    return subprocess.CompletedProcess(args=[], returncode=0, stdout="", stderr="")


def _fail_git(*args, **kwargs):
    return subprocess.CompletedProcess(args=[], returncode=1, stdout="", stderr="error")


class TestCreateWorktree:
    @patch(MOCK_FLEET_SUBPROCESS)
    def test_creates_worktree_new_branch(self, mock_run, tmp_path):
        repo_root = tmp_path / "repo"
        repo_root.mkdir()
        wt_path = tmp_path / "worktrees" / "alpha"

        # First call: rev-parse fails (branch doesn't exist)
        # Second call: worktree add -b succeeds
        mock_run.side_effect = [_fail_git(), _ok_git()]

        result = create_worktree(
            repo_root=repo_root, worktree_path=wt_path, branch="ralph/alpha"
        )

        assert result == wt_path.resolve()
        assert mock_run.call_count == 2
        # Second call should use -b to create new branch
        second_call_args = mock_run.call_args_list[1][0][0]
        assert "-b" in second_call_args
        assert "ralph/alpha" in second_call_args

    @patch(MOCK_FLEET_SUBPROCESS)
    def test_creates_worktree_existing_branch(self, mock_run, tmp_path):
        repo_root = tmp_path / "repo"
        repo_root.mkdir()
        wt_path = tmp_path / "worktrees" / "alpha"

        # Both calls succeed (branch exists)
        mock_run.side_effect = [_ok_git(), _ok_git()]

        create_worktree(
            repo_root=repo_root, worktree_path=wt_path, branch="ralph/alpha"
        )

        assert mock_run.call_count == 2
        second_call_args = mock_run.call_args_list[1][0][0]
        assert "-b" not in second_call_args

    def test_raises_if_path_exists(self, tmp_path):
        repo_root = tmp_path / "repo"
        repo_root.mkdir()
        wt_path = tmp_path / "worktrees" / "alpha"
        wt_path.mkdir(parents=True)

        with pytest.raises(WorktreeError, match="already exists"):
            create_worktree(
                repo_root=repo_root, worktree_path=wt_path, branch="ralph/alpha"
            )

    @patch(MOCK_FLEET_SUBPROCESS)
    def test_raises_on_git_failure(self, mock_run, tmp_path):
        repo_root = tmp_path / "repo"
        repo_root.mkdir()
        wt_path = tmp_path / "worktrees" / "alpha"

        # rev-parse fails, then worktree add also fails
        mock_run.side_effect = [_fail_git(), _fail_git()]

        with pytest.raises(WorktreeError, match="failed"):
            create_worktree(
                repo_root=repo_root, worktree_path=wt_path, branch="ralph/alpha"
            )


class TestRemoveWorktree:
    @patch(MOCK_FLEET_SUBPROCESS, side_effect=[_ok_git()])
    def test_removes_worktree(self, mock_run, tmp_path):
        repo_root = tmp_path / "repo"
        repo_root.mkdir()
        wt_path = tmp_path / "worktrees" / "alpha"

        remove_worktree(repo_root=repo_root, worktree_path=wt_path)

        cmd = mock_run.call_args[0][0]
        assert cmd == ["git", "worktree", "remove", "--force", str(wt_path)]

    @patch(MOCK_FLEET_SUBPROCESS, side_effect=[_fail_git()])
    def test_raises_on_failure(self, mock_run, tmp_path):
        repo_root = tmp_path / "repo"
        repo_root.mkdir()
        wt_path = tmp_path / "worktrees" / "alpha"

        with pytest.raises(WorktreeError):
            remove_worktree(repo_root=repo_root, worktree_path=wt_path)


class TestPruneWorktrees:
    @patch(MOCK_FLEET_SUBPROCESS, side_effect=[_ok_git()])
    def test_runs_prune(self, mock_run, tmp_path):
        repo_root = tmp_path / "repo"
        repo_root.mkdir()

        prune_worktrees(repo_root=repo_root)

        cmd = mock_run.call_args[0][0]
        assert cmd == ["git", "worktree", "prune"]


class TestSetupFleetWorktrees:
    @patch(MOCK_FLEET_SUBPROCESS)
    def test_creates_worktrees_for_all_ralphs(self, mock_run, tmp_path):
        mock_run.return_value = _ok_git()

        config = FleetConfig(
            name="test",
            worktree_dir=".trees",
            state_dir=".state",
            ralphs=[
                RalphEntry(name="alpha", file="a.md", branch="ralph/alpha"),
                RalphEntry(name="beta", file="b.md", branch="ralph/beta"),
            ],
        )

        paths = setup_fleet_worktrees(config=config, repo_root=tmp_path)

        assert "alpha" in paths
        assert "beta" in paths
        # State dir should be created
        assert (tmp_path / ".state").is_dir()

    @patch(MOCK_FLEET_SUBPROCESS)
    def test_skips_worktree_false(self, mock_run, tmp_path):
        mock_run.return_value = _ok_git()

        config = FleetConfig(
            name="test",
            ralphs=[
                RalphEntry(name="alpha", file="a.md", branch="b", worktree=False),
            ],
        )

        paths = setup_fleet_worktrees(config=config, repo_root=tmp_path)

        assert paths["alpha"] == tmp_path
        # No git commands should have been called for worktree creation
        mock_run.assert_not_called()


class TestTeardownFleetWorktrees:
    @patch(MOCK_FLEET_SUBPROCESS)
    def test_removes_worktrees_and_prunes(self, mock_run, tmp_path):
        mock_run.return_value = _ok_git()

        config = FleetConfig(
            name="test",
            worktree_dir=".trees",
            ralphs=[
                RalphEntry(name="alpha", file="a.md", branch="ralph/alpha"),
            ],
        )

        # Create the worktree directory so teardown finds it
        wt_dir = tmp_path / ".trees" / "alpha"
        wt_dir.mkdir(parents=True)

        teardown_fleet_worktrees(config=config, repo_root=tmp_path)

        # Should have called remove then prune
        assert mock_run.call_count == 2

    @patch(MOCK_FLEET_SUBPROCESS)
    def test_skips_nonexistent_worktree(self, mock_run, tmp_path):
        mock_run.return_value = _ok_git()

        config = FleetConfig(
            name="test",
            worktree_dir=".trees",
            ralphs=[
                RalphEntry(name="alpha", file="a.md", branch="ralph/alpha"),
            ],
        )

        # Don't create the worktree directory
        teardown_fleet_worktrees(config=config, repo_root=tmp_path)

        # Only prune should be called (no remove since dir doesn't exist)
        assert mock_run.call_count == 1
        cmd = mock_run.call_args[0][0]
        assert cmd == ["git", "worktree", "prune"]

    @patch(MOCK_FLEET_SUBPROCESS)
    def test_skips_worktree_false_entries(self, mock_run, tmp_path):
        mock_run.return_value = _ok_git()

        config = FleetConfig(
            name="test",
            worktree_dir=".trees",
            ralphs=[
                RalphEntry(name="alpha", file="a.md", branch="b", worktree=False),
            ],
        )

        teardown_fleet_worktrees(config=config, repo_root=tmp_path)

        # Only prune, no remove
        assert mock_run.call_count == 1


# ── Fleet orchestration ──────────────────────────────────────────────


class TestFleetOrchestratorLaunchOrder:
    """Test the topological sort for dependency ordering."""

    def test_no_dependencies(self):
        config = FleetConfig(
            name="test",
            ralphs=[
                RalphEntry(name="a", file="a.md", branch="a", priority=0),
                RalphEntry(name="b", file="b.md", branch="b", priority=5),
            ],
        )
        orch = FleetOrchestrator(config, Path("/fake"))
        order = orch._resolve_launch_order()

        # No deps — topo sort preserves input order from config.ralphs
        assert order == ["a", "b"]

    def test_dependency_ordering(self):
        config = FleetConfig(
            name="test",
            ralphs=[
                RalphEntry(name="pm", file="pm.md", branch="pm", priority=10),
                RalphEntry(
                    name="dev", file="dev.md", branch="dev",
                    priority=5, depends_on=["pm"],
                ),
                RalphEntry(
                    name="qa", file="qa.md", branch="qa",
                    priority=0, depends_on=["dev"],
                ),
            ],
        )
        orch = FleetOrchestrator(config, Path("/fake"))
        order = orch._resolve_launch_order()

        assert order.index("pm") < order.index("dev")
        assert order.index("dev") < order.index("qa")

    def test_circular_dependency_raises(self):
        config = FleetConfig(
            name="test",
            ralphs=[
                RalphEntry(name="a", file="a.md", branch="a", depends_on=["b"]),
                RalphEntry(name="b", file="b.md", branch="b", depends_on=["a"]),
            ],
        )
        orch = FleetOrchestrator(config, Path("/fake"))

        with pytest.raises(ValueError, match="Circular dependency"):
            orch._resolve_launch_order()


class TestFleetOrchestratorStatus:
    def test_initial_status_is_pending(self, tmp_path):
        config = FleetConfig(name="test", ralphs=[])
        orch = FleetOrchestrator(config, tmp_path)
        assert orch.status == FleetStatus.PENDING

    def test_cannot_start_from_running_state(self, tmp_path):
        config = FleetConfig(name="test", ralphs=[])
        orch = FleetOrchestrator(config, tmp_path)
        orch._status = FleetStatus.RUNNING

        with pytest.raises(RuntimeError, match="Cannot start fleet"):
            orch.start()

    def test_get_ralph_statuses_empty_fleet(self, tmp_path):
        config = FleetConfig(name="test", ralphs=[])
        orch = FleetOrchestrator(config, tmp_path)
        assert orch.get_ralph_statuses() == []

    def test_stop_ralph_unknown_name(self, tmp_path):
        config = FleetConfig(name="test", ralphs=[])
        orch = FleetOrchestrator(config, tmp_path)

        with pytest.raises(KeyError, match="No ralph named"):
            orch.stop_ralph("nonexistent")

    def test_stop_noop_when_pending(self, tmp_path):
        config = FleetConfig(name="test", ralphs=[])
        orch = FleetOrchestrator(config, tmp_path)
        # Should not raise
        orch.stop()
        assert orch.status == FleetStatus.PENDING


class TestRalphEntryDefaults:
    def test_defaults(self):
        entry = RalphEntry(name="test", file="test.md", branch="main")
        assert entry.worktree is True
        assert entry.priority == 0
        assert entry.depends_on == []


class TestFleetSettingsDefaults:
    def test_defaults(self):
        settings = FleetSettings()
        assert settings.max_concurrent == 0
        assert settings.stagger_start == 0
        assert settings.merge_strategy == "fifo"
        assert settings.health_check_interval == 60


class TestFleetConfigDefaults:
    def test_defaults(self):
        config = FleetConfig(name="test")
        assert config.worktree_dir == ".trees"
        assert config.state_dir == ".ralph/state"
        assert config.ralphs == []
        assert isinstance(config.settings, FleetSettings)


class TestRalphStatusDefaults:
    def test_defaults(self):
        status = RalphStatus(name="test")
        assert status.run_id is None
        assert status.run_status == RunStatus.PENDING
        assert status.worktree_path is None
        assert status.iteration == 0
        assert status.completed == 0
        assert status.failed == 0
