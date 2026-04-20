# Author: Julian Bolivar
# Version: 1.0.0
# Date: 2026-04-19
"""Tests for resume_cmd magi-conditions.md detection (Plan D Task 9)."""

from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import pytest

import resume_cmd


def _write_state(root: Path, phase: str) -> None:
    state_dir = root / ".claude"
    state_dir.mkdir(parents=True, exist_ok=True)
    (state_dir / "session-state.json").write_text(
        json.dumps(
            {
                "plan_path": "planning/claude-plan-tdd.md",
                "current_task_id": None,
                "current_task_title": None,
                "current_phase": phase,
                "phase_started_at_commit": "abc1234",
                "last_verification_at": "2026-04-19T16:30:00Z",
                "last_verification_result": "passed",
                "plan_approved_at": "2026-04-19T10:00:00Z",
            }
        ),
        encoding="utf-8",
    )


def test_decide_delegation_with_magi_conditions_pending(
    tmp_path: Path,
) -> None:
    _write_state(tmp_path, "done")
    (tmp_path / ".claude" / "magi-conditions.md").write_text(
        "# MAGI conditions iter 1\n\n- Apply refactor X\n", encoding="utf-8"
    )
    state = SimpleNamespace(current_phase="done")
    runtime = {
        "auto-run.json": True,
        "magi-verdict.json": False,
        "magi-conditions.md": True,
    }
    module_name, extra = resume_cmd._decide_delegation(
        state, tree_dirty=False, runtime=runtime
    )
    assert module_name == "magi-conditions-pending"
    assert extra == []


def test_resume_stdout_when_conditions_pending(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    _write_state(tmp_path, "done")
    (tmp_path / ".claude" / "plugin.local.md").write_text(
        "---\nstack: python\n---\n", encoding="utf-8"
    )
    (tmp_path / ".claude" / "magi-conditions.md").write_text(
        "# MAGI conditions iter 1\n\n- Apply refactor X\n", encoding="utf-8"
    )
    # Shim subprocess so diagnostic / environment checks pass.
    monkeypatch.setattr(resume_cmd, "_recheck_environment", lambda root: None)
    monkeypatch.setattr(
        resume_cmd,
        "_report_diagnostic",
        lambda root: {
            "state": SimpleNamespace(current_phase="done"),
            "head_sha": "abc1234",
            "tree_dirty": False,
            "runtime": {
                "auto-run.json": True,
                "magi-verdict.json": False,
                "magi-conditions.md": True,
            },
        },
    )
    rc = resume_cmd.main(["--project-root", str(tmp_path)])
    captured = capsys.readouterr()
    assert rc == 0
    assert "magi-conditions.md" in captured.out
    assert "sbtdd close-phase" in captured.out


def test_diagnostic_snapshot_includes_magi_conditions_md(tmp_path: Path) -> None:
    _write_state(tmp_path, "done")
    (tmp_path / ".claude" / "magi-conditions.md").write_text(
        "# MAGI conditions iter 1\n", encoding="utf-8"
    )
    # Initialise git so diagnostic runs.
    import subprocess

    subprocess.run(
        ["git", "init", "--initial-branch", "main"],
        cwd=tmp_path,
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "commit", "--allow-empty", "-m", "init"],
        cwd=tmp_path,
        check=True,
        capture_output=True,
    )
    report = resume_cmd._report_diagnostic(tmp_path)
    assert report["runtime"].get("magi-conditions.md") is True
