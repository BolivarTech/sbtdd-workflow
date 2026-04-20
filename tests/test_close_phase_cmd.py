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


def _install_happy_path_patches(
    monkeypatch: pytest.MonkeyPatch, captured: dict[str, object]
) -> None:
    """Patch drift + verification + git rev-parse + commits.create."""
    from types import SimpleNamespace

    captured.setdefault("commit_calls", [])
    captured.setdefault("new_sha", "abc9999")

    monkeypatch.setattr("close_phase_cmd.detect_drift", lambda *a, **k: None)
    monkeypatch.setattr(
        "close_phase_cmd.superpowers_dispatch.verification_before_completion",
        lambda *a, **k: None,
    )

    def fake_run(cmd, timeout=0, cwd=None):  # type: ignore[no-untyped-def]
        if "rev-parse" in cmd:
            return SimpleNamespace(returncode=0, stdout=str(captured["new_sha"]) + "\n", stderr="")
        return SimpleNamespace(returncode=0, stdout="", stderr="")

    monkeypatch.setattr("close_phase_cmd.subprocess_utils.run_with_timeout", fake_run)

    def fake_commit(prefix, message, cwd=None):  # type: ignore[no-untyped-def]
        calls = captured["commit_calls"]
        assert isinstance(calls, list)
        calls.append((prefix, message))
        return ""

    monkeypatch.setattr("close_phase_cmd.commit_create", fake_commit)


def test_close_phase_red_emits_test_prefix_commit(
    tmp_path, monkeypatch: pytest.MonkeyPatch
) -> None:  # type: ignore[no-untyped-def]
    import close_phase_cmd

    _seed_state(tmp_path, current_phase="red")
    captured: dict[str, object] = {}
    _install_happy_path_patches(monkeypatch, captured)

    rc = close_phase_cmd.main(["--project-root", str(tmp_path), "--message", "add parser"])
    assert rc == 0
    calls = captured["commit_calls"]
    assert isinstance(calls, list)
    assert calls == [("test", "add parser")]


def test_close_phase_green_feat_emits_feat(tmp_path, monkeypatch: pytest.MonkeyPatch) -> None:  # type: ignore[no-untyped-def]
    import close_phase_cmd

    _seed_state(tmp_path, current_phase="green")
    captured: dict[str, object] = {}
    _install_happy_path_patches(monkeypatch, captured)

    close_phase_cmd.main(
        [
            "--project-root",
            str(tmp_path),
            "--message",
            "impl parser",
            "--variant",
            "feat",
        ]
    )
    calls = captured["commit_calls"]
    assert isinstance(calls, list)
    assert calls == [("feat", "impl parser")]


def test_close_phase_green_fix_emits_fix(tmp_path, monkeypatch: pytest.MonkeyPatch) -> None:  # type: ignore[no-untyped-def]
    import close_phase_cmd

    _seed_state(tmp_path, current_phase="green")
    captured: dict[str, object] = {}
    _install_happy_path_patches(monkeypatch, captured)

    close_phase_cmd.main(
        [
            "--project-root",
            str(tmp_path),
            "--message",
            "patch parser",
            "--variant",
            "fix",
        ]
    )
    calls = captured["commit_calls"]
    assert isinstance(calls, list)
    assert calls == [("fix", "patch parser")]


def test_close_phase_advances_state_red_to_green(tmp_path, monkeypatch: pytest.MonkeyPatch) -> None:  # type: ignore[no-untyped-def]
    import json as _json

    import close_phase_cmd

    _seed_state(tmp_path, current_phase="red")
    captured: dict[str, object] = {}
    _install_happy_path_patches(monkeypatch, captured)

    close_phase_cmd.main(["--project-root", str(tmp_path), "--message", "m"])
    state = _json.loads((tmp_path / ".claude" / "session-state.json").read_text(encoding="utf-8"))
    assert state["current_phase"] == "green"


def test_close_phase_advances_state_green_to_refactor(
    tmp_path, monkeypatch: pytest.MonkeyPatch
) -> None:  # type: ignore[no-untyped-def]
    import json as _json

    import close_phase_cmd

    _seed_state(tmp_path, current_phase="green")
    captured: dict[str, object] = {}
    _install_happy_path_patches(monkeypatch, captured)

    close_phase_cmd.main(["--project-root", str(tmp_path), "--message", "m", "--variant", "feat"])
    state = _json.loads((tmp_path / ".claude" / "session-state.json").read_text(encoding="utf-8"))
    assert state["current_phase"] == "refactor"


def test_close_phase_updates_phase_started_at_commit_to_new_sha(
    tmp_path, monkeypatch: pytest.MonkeyPatch
) -> None:  # type: ignore[no-untyped-def]
    import json as _json

    import close_phase_cmd

    _seed_state(tmp_path, current_phase="red")
    captured: dict[str, object] = {"new_sha": "beefcaf"}
    _install_happy_path_patches(monkeypatch, captured)

    close_phase_cmd.main(["--project-root", str(tmp_path), "--message", "m"])
    state = _json.loads((tmp_path / ".claude" / "session-state.json").read_text(encoding="utf-8"))
    assert state["phase_started_at_commit"] == "beefcaf"


def test_close_phase_updates_last_verification_fields(
    tmp_path, monkeypatch: pytest.MonkeyPatch
) -> None:  # type: ignore[no-untyped-def]
    import json as _json

    import close_phase_cmd

    _seed_state(tmp_path, current_phase="red")
    captured: dict[str, object] = {}
    _install_happy_path_patches(monkeypatch, captured)

    close_phase_cmd.main(["--project-root", str(tmp_path), "--message", "m"])
    state = _json.loads((tmp_path / ".claude" / "session-state.json").read_text(encoding="utf-8"))
    assert state["last_verification_at"] is not None
    assert state["last_verification_at"].endswith("Z")
    assert state["last_verification_result"] == "passed"


def test_close_phase_green_without_variant_raises_validation_error(
    tmp_path, monkeypatch: pytest.MonkeyPatch
) -> None:  # type: ignore[no-untyped-def]
    import close_phase_cmd
    from errors import ValidationError

    _seed_state(tmp_path, current_phase="green")
    captured: dict[str, object] = {}
    _install_happy_path_patches(monkeypatch, captured)

    with pytest.raises(ValidationError):
        close_phase_cmd.main(["--project-root", str(tmp_path), "--message", "m"])


def test_close_phase_refactor_cascades_to_close_task(
    tmp_path, monkeypatch: pytest.MonkeyPatch
) -> None:  # type: ignore[no-untyped-def]
    import close_phase_cmd
    import close_task_cmd

    _seed_state(tmp_path, current_phase="refactor")
    captured: dict[str, object] = {}
    _install_happy_path_patches(monkeypatch, captured)

    cascade_calls: list[list[str] | None] = []

    def fake_close_task_main(argv=None):  # type: ignore[no-untyped-def]
        cascade_calls.append(argv)
        return 0

    monkeypatch.setattr(close_task_cmd, "main", fake_close_task_main)

    rc = close_phase_cmd.main(["--project-root", str(tmp_path), "--message", "refa"])
    assert rc == 0
    assert len(cascade_calls) == 1
    argv = cascade_calls[0]
    assert argv is not None
    assert "--project-root" in argv
    assert str(tmp_path) in argv


def test_close_phase_refactor_creates_refactor_commit_before_cascade(
    tmp_path, monkeypatch: pytest.MonkeyPatch
) -> None:  # type: ignore[no-untyped-def]
    """Verify the refactor commit is recorded BEFORE close_task_cmd.main runs."""
    import close_phase_cmd
    import close_task_cmd

    _seed_state(tmp_path, current_phase="refactor")
    captured: dict[str, object] = {}
    _install_happy_path_patches(monkeypatch, captured)

    order: list[str] = []
    original_fake_commit = None  # placeholder

    def track_commit(prefix, message, cwd=None):  # type: ignore[no-untyped-def]
        order.append(f"commit:{prefix}")
        return ""

    monkeypatch.setattr("close_phase_cmd.commit_create", track_commit)

    def track_cascade(argv=None):  # type: ignore[no-untyped-def]
        order.append("cascade")
        return 0

    monkeypatch.setattr(close_task_cmd, "main", track_cascade)

    close_phase_cmd.main(["--project-root", str(tmp_path), "--message", "pulir"])
    # refactor commit must happen first, cascade afterwards.
    assert order == ["commit:refactor", "cascade"]
    assert original_fake_commit is None  # placeholder use avoids unused-var lint


def test_close_phase_refactor_returns_cascade_rc_on_failure(
    tmp_path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:  # type: ignore[no-untyped-def]
    """If close_task_cmd.main returns non-zero, propagate that rc + warn on stderr."""
    import close_phase_cmd
    import close_task_cmd

    _seed_state(tmp_path, current_phase="refactor")
    captured: dict[str, object] = {}
    _install_happy_path_patches(monkeypatch, captured)

    monkeypatch.setattr(close_task_cmd, "main", lambda argv=None: 7)

    rc = close_phase_cmd.main(["--project-root", str(tmp_path), "--message", "m"])
    assert rc == 7
    err = capsys.readouterr().err
    assert "close-task cascade failed" in err
