# Author: Julian Bolivar
# Version: 1.0.0
# Date: 2026-04-19
"""Tests for /sbtdd status read-only subcomando (sec.S.5.5)."""

from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest


def test_status_cmd_module_importable() -> None:
    import status_cmd

    assert hasattr(status_cmd, "main")
    assert hasattr(status_cmd, "run")


def test_status_cmd_run_is_main_alias() -> None:
    import status_cmd

    assert callable(status_cmd.main) and callable(status_cmd.run)


@pytest.fixture
def repo_with_state(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Create a tmp project with state file + 3-task plan, monkeypatch git HEAD."""
    claude_dir = tmp_path / ".claude"
    claude_dir.mkdir()
    planning_dir = tmp_path / "planning"
    planning_dir.mkdir()
    fixtures_root = Path(__file__).parent / "fixtures"
    shutil.copy(
        fixtures_root / "plans" / "three-tasks-mixed.md",
        planning_dir / "claude-plan-tdd.md",
    )
    state_payload = {
        "plan_path": "planning/claude-plan-tdd.md",
        "current_task_id": "2",
        "current_task_title": "Second task (in-progress)",
        "current_phase": "red",
        "phase_started_at_commit": "abc1234",
        "last_verification_at": None,
        "last_verification_result": None,
        "plan_approved_at": "2026-04-19T10:00:00Z",
    }
    (claude_dir / "session-state.json").write_text(
        json.dumps(state_payload, indent=2), encoding="utf-8"
    )

    def fake_run(cmd: list[str], timeout: int = 0, cwd: str | None = None):  # type: ignore[no-untyped-def]
        from types import SimpleNamespace

        return SimpleNamespace(returncode=0, stdout="abc1234|test: seed commit\n", stderr="")

    monkeypatch.setattr("status_cmd.subprocess_utils.run_with_timeout", fake_run)
    # Neutralize drift detection for Task 2 tests (Task 3 adds real drift cases).
    monkeypatch.setattr("status_cmd.detect_drift", lambda *a, **k: None)
    return tmp_path


def test_status_reports_active_task_phase_and_plan_counts(
    repo_with_state: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    import status_cmd

    rc = status_cmd.main(["--project-root", str(repo_with_state)])
    out = capsys.readouterr().out
    assert rc == 0
    assert "Second task" in out
    assert "red" in out
    assert "1/3" in out


def test_status_prints_last_verification_null_when_unset(
    repo_with_state: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    import status_cmd

    status_cmd.main(["--project-root", str(repo_with_state)])
    out = capsys.readouterr().out
    assert "null" in out  # both last_verif_at and last_verif_result are null


def test_status_missing_state_file_prints_manual_mode(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    import status_cmd

    rc = status_cmd.main(["--project-root", str(tmp_path)])
    out = capsys.readouterr().out
    assert rc == 0
    assert "manual mode" in out or "no active" in out.lower()
