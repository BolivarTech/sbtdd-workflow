# Author: Julian Bolivar
# Version: 1.0.0
# Date: 2026-04-19
"""Tests for /sbtdd pre-merge subcommand (sec.S.5.6)."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest


def _seed_state(
    tmp_path: Path,
    *,
    current_phase: str = "done",
    current_task_id: str | None = None,
    current_task_title: str | None = None,
    plan_approved_at: str | None = "2026-04-20T03:30:00Z",
) -> Path:
    """Write a minimal valid state file into tmp_path/.claude."""
    claude = tmp_path / ".claude"
    claude.mkdir(parents=True, exist_ok=True)
    state = {
        "plan_path": "planning/claude-plan-tdd.md",
        "current_task_id": current_task_id,
        "current_task_title": current_task_title,
        "current_phase": current_phase,
        "phase_started_at_commit": "abc1234",
        "last_verification_at": "2026-04-20T03:30:00Z",
        "last_verification_result": "passed",
        "plan_approved_at": plan_approved_at,
    }
    state_path = claude / "session-state.json"
    state_path.write_text(json.dumps(state), encoding="utf-8")
    return state_path


def _seed_plan_all_done(tmp_path: Path) -> Path:
    """Write a plan where every task has all checkboxes marked [x]."""
    planning = tmp_path / "planning"
    planning.mkdir(parents=True, exist_ok=True)
    plan = planning / "claude-plan-tdd.md"
    plan.write_text(
        "# Plan\n\n### Task 1: done\n- [x] step\n\n### Task 2: done\n- [x] step\n",
        encoding="utf-8",
    )
    return plan


def _setup_git_repo(tmp_path: Path) -> None:
    """Init a git repo with one initial commit so HEAD resolves."""
    subprocess.run(["git", "init", "-q"], cwd=str(tmp_path), check=True, capture_output=True)
    subprocess.run(
        ["git", "config", "user.email", "tester@example.com"],
        cwd=str(tmp_path),
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "config", "user.name", "Tester"],
        cwd=str(tmp_path),
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "config", "commit.gpgsign", "false"],
        cwd=str(tmp_path),
        check=True,
        capture_output=True,
    )
    (tmp_path / "README.md").write_text("initial\n", encoding="utf-8")
    subprocess.run(["git", "add", "README.md"], cwd=str(tmp_path), check=True, capture_output=True)
    subprocess.run(
        ["git", "commit", "-m", "chore: initial"],
        cwd=str(tmp_path),
        check=True,
        capture_output=True,
    )


def test_pre_merge_cmd_module_importable() -> None:
    import pre_merge_cmd

    assert hasattr(pre_merge_cmd, "main")


def test_pre_merge_aborts_when_state_not_done(tmp_path: Path) -> None:
    import pre_merge_cmd
    from errors import PreconditionError

    _setup_git_repo(tmp_path)
    _seed_state(tmp_path, current_phase="green", current_task_id="1", current_task_title="t")
    _seed_plan_all_done(tmp_path)
    with pytest.raises(PreconditionError):
        pre_merge_cmd.main(["--project-root", str(tmp_path)])


def test_pre_merge_aborts_on_drift(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    import pre_merge_cmd
    from drift import DriftReport
    from errors import DriftError

    _setup_git_repo(tmp_path)
    _seed_state(tmp_path, current_phase="done")
    _seed_plan_all_done(tmp_path)
    monkeypatch.setattr(
        pre_merge_cmd,
        "detect_drift",
        lambda *a, **kw: DriftReport("done", "test", "[ ]", "stub"),
    )
    with pytest.raises(DriftError):
        pre_merge_cmd.main(["--project-root", str(tmp_path)])
