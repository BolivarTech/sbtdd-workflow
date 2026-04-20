# Author: Julian Bolivar
# Version: 1.0.0
# Date: 2026-04-19
"""Tests for /sbtdd close-phase subcomando (sec.S.5.3)."""

from __future__ import annotations

import pytest


def test_close_phase_cmd_module_importable() -> None:
    import close_phase_cmd

    assert hasattr(close_phase_cmd, "main")


def test_close_phase_cmd_parses_help() -> None:
    import close_phase_cmd

    with pytest.raises(SystemExit):
        close_phase_cmd.main(["--help"])


def _seed_state(
    tmp_path,  # type: ignore[no-untyped-def]
    *,
    current_phase: str,
    plan_approved_at: str | None = "2026-04-19T10:00:00Z",
) -> None:
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
        "plan_approved_at": plan_approved_at,
    }
    (claude / "session-state.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")


def test_close_phase_aborts_on_drift(tmp_path, monkeypatch: pytest.MonkeyPatch) -> None:  # type: ignore[no-untyped-def]
    import close_phase_cmd
    from drift import DriftReport
    from errors import DriftError

    _seed_state(tmp_path, current_phase="red")

    def fake_drift(*a, **k):  # type: ignore[no-untyped-def]
        return DriftReport(
            state_value="red",
            git_value="refactor",
            plan_value="[ ]",
            reason="synthetic",
        )

    monkeypatch.setattr("close_phase_cmd.detect_drift", fake_drift)
    with pytest.raises(DriftError):
        close_phase_cmd.main(["--project-root", str(tmp_path), "--message", "x"])


def test_close_phase_aborts_on_state_missing(tmp_path) -> None:  # type: ignore[no-untyped-def]
    import close_phase_cmd
    from errors import PreconditionError

    with pytest.raises(PreconditionError):
        close_phase_cmd.main(["--project-root", str(tmp_path), "--message", "x"])


def test_close_phase_aborts_when_plan_not_approved(
    tmp_path, monkeypatch: pytest.MonkeyPatch
) -> None:  # type: ignore[no-untyped-def]
    import close_phase_cmd
    from errors import PreconditionError

    _seed_state(tmp_path, current_phase="red", plan_approved_at=None)
    monkeypatch.setattr("close_phase_cmd.detect_drift", lambda *a, **k: None)
    with pytest.raises(PreconditionError) as ei:
        close_phase_cmd.main(["--project-root", str(tmp_path), "--message", "x"])
    assert "plan_approved_at" in str(ei.value)


def test_close_phase_aborts_when_verification_fails(
    tmp_path, monkeypatch: pytest.MonkeyPatch
) -> None:  # type: ignore[no-untyped-def]
    import close_phase_cmd
    from errors import ValidationError

    _seed_state(tmp_path, current_phase="red")
    monkeypatch.setattr("close_phase_cmd.detect_drift", lambda *a, **k: None)

    def fake_verif(*a, **k):  # type: ignore[no-untyped-def]
        raise ValidationError("verification failed")

    monkeypatch.setattr(
        "close_phase_cmd.superpowers_dispatch.verification_before_completion",
        fake_verif,
    )
    with pytest.raises(ValidationError):
        close_phase_cmd.main(["--project-root", str(tmp_path), "--message", "x"])


def test_close_phase_does_not_commit_when_verification_fails(
    tmp_path, monkeypatch: pytest.MonkeyPatch
) -> None:  # type: ignore[no-untyped-def]
    """If verification raises, commit_create must not be invoked."""
    import close_phase_cmd
    from errors import ValidationError

    _seed_state(tmp_path, current_phase="red")
    monkeypatch.setattr("close_phase_cmd.detect_drift", lambda *a, **k: None)
    called: dict[str, bool] = {"commit": False}

    def fake_verif(*a, **k):  # type: ignore[no-untyped-def]
        raise ValidationError("verification failed")

    monkeypatch.setattr(
        "close_phase_cmd.superpowers_dispatch.verification_before_completion",
        fake_verif,
    )

    # Also patch commit_create so if it were called we would see it.
    # Task 8 does not yet invoke commit_create, but we defend against future wiring.
    def fake_commit(prefix, message, cwd=None):  # type: ignore[no-untyped-def]
        called["commit"] = True
        return ""

    # commit_create only exists after Task 9 wiring; skip import there.
    if hasattr(close_phase_cmd, "commit_create"):
        monkeypatch.setattr("close_phase_cmd.commit_create", fake_commit)

    with pytest.raises(ValidationError):
        close_phase_cmd.main(["--project-root", str(tmp_path), "--message", "x"])
    assert called["commit"] is False
