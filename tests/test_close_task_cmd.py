# Author: Julian Bolivar
# Version: 1.0.0
# Date: 2026-04-19
"""Tests for /sbtdd close-task subcomando (sec.S.5.4)."""

from __future__ import annotations

import pytest


def test_close_task_cmd_module_importable() -> None:
    import close_task_cmd

    assert hasattr(close_task_cmd, "main")
    assert hasattr(close_task_cmd, "run")


def test_close_task_cmd_help_exits_zero() -> None:
    import close_task_cmd

    with pytest.raises(SystemExit) as ei:
        close_task_cmd.main(["--help"])
    assert ei.value.code == 0


def _seed_state(tmp_path, *, current_phase: str):  # type: ignore[no-untyped-def]
    import json
    import shutil
    from pathlib import Path

    claude = tmp_path / ".claude"
    claude.mkdir()
    planning = tmp_path / "planning"
    planning.mkdir()
    fixtures_root = Path(__file__).parent / "fixtures"
    shutil.copy(
        fixtures_root / "plans" / "three-tasks-mixed.md",
        planning / "claude-plan-tdd.md",
    )
    payload = {
        "plan_path": "planning/claude-plan-tdd.md",
        "current_task_id": "2",
        "current_task_title": "Second task (in-progress)",
        "current_phase": current_phase,
        "phase_started_at_commit": "abc1234",
        "last_verification_at": None,
        "last_verification_result": None,
        "plan_approved_at": "2026-04-19T10:00:00Z",
    }
    (claude / "session-state.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")


def test_close_task_aborts_when_state_missing(tmp_path) -> None:  # type: ignore[no-untyped-def]
    import close_task_cmd
    from errors import PreconditionError

    with pytest.raises(PreconditionError):
        close_task_cmd.main(["--project-root", str(tmp_path)])


def test_close_task_aborts_when_phase_not_refactor(
    tmp_path, monkeypatch: pytest.MonkeyPatch
) -> None:  # type: ignore[no-untyped-def]
    import close_task_cmd
    from errors import PreconditionError

    _seed_state(tmp_path, current_phase="green")
    monkeypatch.setattr("close_task_cmd.detect_drift", lambda *a, **k: None)
    with pytest.raises(PreconditionError) as ei:
        close_task_cmd.main(["--project-root", str(tmp_path)])
    msg = str(ei.value)
    assert "refactor" in msg
    assert "green" in msg


def test_close_task_aborts_on_drift(tmp_path, monkeypatch: pytest.MonkeyPatch) -> None:  # type: ignore[no-untyped-def]
    import close_task_cmd
    from drift import DriftReport
    from errors import DriftError

    _seed_state(tmp_path, current_phase="refactor")

    def fake_drift(*a, **k):  # type: ignore[no-untyped-def]
        return DriftReport(
            state_value="refactor",
            git_value="feat",
            plan_value="[ ]",
            reason="synthetic",
        )

    monkeypatch.setattr("close_task_cmd.detect_drift", fake_drift)
    with pytest.raises(DriftError):
        close_task_cmd.main(["--project-root", str(tmp_path)])
