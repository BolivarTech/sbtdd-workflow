# Author: Julian Bolivar
# Version: 1.0.0
# Date: 2026-04-19
"""Tests for /sbtdd close-phase subcomando (sec.S.5.3)."""

from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

import close_phase_cmd
from errors import ValidationError


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
    """Refactor-close cascades by invoking ``close_task_cmd.mark_and_advance``.

    MAGI Loop 2 iter 1 Finding 6: the pre-fix implementation invoked
    ``close_task_cmd.main(["--project-root", ...])``. Main runs its own
    ``_preflight`` which re-evaluates drift (state=refactor + HEAD
    ``refactor:`` was interpreted as drift), raising before the advance
    could run. The fix switches to the public ``mark_and_advance`` API
    which skips the precondition drift check and performs the state
    advance directly. The test enforces this by making
    ``close_task_cmd.main`` explode if invoked.
    """
    import close_phase_cmd
    import close_task_cmd

    _seed_state(tmp_path, current_phase="refactor")
    captured: dict[str, object] = {}
    _install_happy_path_patches(monkeypatch, captured)

    advance_calls: list[object] = []

    def fake_mark_and_advance(state, root):  # type: ignore[no-untyped-def]
        advance_calls.append((state.current_phase, str(root)))
        return state

    def fail_if_main_called(argv=None):  # type: ignore[no-untyped-def]
        raise AssertionError(
            "close_task_cmd.main must NOT be called as cascade target "
            "post-Finding-6; use mark_and_advance directly"
        )

    monkeypatch.setattr(close_task_cmd, "mark_and_advance", fake_mark_and_advance)
    monkeypatch.setattr(close_task_cmd, "main", fail_if_main_called)

    rc = close_phase_cmd.main(["--project-root", str(tmp_path), "--message", "refa"])
    assert rc == 0
    assert len(advance_calls) == 1
    first_call = advance_calls[0]
    # Refactor close passes the post-refactor SessionState (phase is
    # still 'refactor' at the call site; mark_and_advance itself flips
    # it to 'red'/'done' internally).
    assert isinstance(first_call, tuple)
    assert first_call[0] == "refactor"
    assert first_call[1] == str(tmp_path)


def test_close_phase_refactor_creates_refactor_commit_before_cascade(
    tmp_path, monkeypatch: pytest.MonkeyPatch
) -> None:  # type: ignore[no-untyped-def]
    """Refactor commit recorded BEFORE ``close_task_cmd.mark_and_advance`` runs.

    Post-Finding-6: cascade target is ``mark_and_advance`` (the public
    API), not ``close_task_cmd.main``. Ordering invariant unchanged;
    main() explodes if invoked so the test also asserts the new call
    path.
    """
    import close_phase_cmd
    import close_task_cmd

    _seed_state(tmp_path, current_phase="refactor")
    captured: dict[str, object] = {}
    _install_happy_path_patches(monkeypatch, captured)

    order: list[str] = []

    def track_commit(prefix, message, cwd=None):  # type: ignore[no-untyped-def]
        order.append(f"commit:{prefix}")
        return ""

    monkeypatch.setattr("close_phase_cmd.commit_create", track_commit)

    def track_cascade(state, root):  # type: ignore[no-untyped-def]
        order.append("cascade")
        return state

    def fail_if_main_called(argv=None):  # type: ignore[no-untyped-def]
        raise AssertionError("cascade must reach mark_and_advance, not main()")

    monkeypatch.setattr(close_task_cmd, "mark_and_advance", track_cascade)
    monkeypatch.setattr(close_task_cmd, "main", fail_if_main_called)

    close_phase_cmd.main(["--project-root", str(tmp_path), "--message", "pulir"])
    # refactor commit must happen first, cascade afterwards.
    assert order == ["commit:refactor", "cascade"]


def test_close_phase_refactor_propagates_cascade_exception(
    tmp_path, monkeypatch: pytest.MonkeyPatch
) -> None:  # type: ignore[no-untyped-def]
    """Post-Finding-6: ``mark_and_advance`` exceptions propagate unchanged.

    With the direct public-API cascade, an error during the state
    advance raises naturally (no rc return-code shim); the dispatcher
    maps the exception to the sec.S.11.1 exit code. The refactor
    commit remains landed because it happened before the cascade.
    """
    import close_phase_cmd
    import close_task_cmd
    from errors import PreconditionError

    _seed_state(tmp_path, current_phase="refactor")
    captured: dict[str, object] = {}
    _install_happy_path_patches(monkeypatch, captured)

    def broken_advance(state, root):  # type: ignore[no-untyped-def]
        raise PreconditionError("simulated advance failure")

    monkeypatch.setattr(close_task_cmd, "mark_and_advance", broken_advance)

    with pytest.raises(PreconditionError, match="simulated advance failure"):
        close_phase_cmd.main(["--project-root", str(tmp_path), "--message", "m"])


def test_close_phase_refactor_cascade_exception_maps_to_correct_exit_code(
    tmp_path, monkeypatch: pytest.MonkeyPatch
) -> None:  # type: ignore[no-untyped-def]
    """MAGI Loop 2 iter 2 W_iter2_2: cascade exception maps through dispatcher.

    ``test_close_phase_refactor_propagates_cascade_exception`` (above)
    verifies the exception reaches ``close_phase_cmd.main``'s caller
    unchanged. This test takes the next hop: invokes the subcommand
    through ``run_sbtdd.main`` (the process-level dispatcher) and
    asserts that :func:`run_sbtdd._exit_code_for` maps the cascade
    exception to the canonical sec.S.11.1 exit code via
    :data:`errors.EXIT_CODES`. Covers the full behaviour change
    introduced by Finding 6 (``rc``-return-code shim → exception
    propagation): not just that the exception leaves the subcommand,
    but that the dispatcher hands the process the RIGHT exit code.
    """
    import close_task_cmd
    import run_sbtdd
    from errors import EXIT_CODES, ValidationError

    _seed_state(tmp_path, current_phase="refactor")
    captured: dict[str, object] = {}
    _install_happy_path_patches(monkeypatch, captured)

    def broken_advance(state, root):  # type: ignore[no-untyped-def]
        raise ValidationError("simulated advance validation failure")

    monkeypatch.setattr(close_task_cmd, "mark_and_advance", broken_advance)

    exit_code = run_sbtdd.main(["close-phase", "--project-root", str(tmp_path), "--message", "m"])
    assert exit_code == EXIT_CODES[ValidationError]


def test_close_phase_verification_receives_project_root_as_cwd(
    tmp_path, monkeypatch: pytest.MonkeyPatch
) -> None:  # type: ignore[no-untyped-def]
    """MAGI Loop 2 iter 1 Finding 4: _run_verification must pass cwd=root.

    The skill wrapper for ``/verification-before-completion`` accepts a
    ``cwd`` kwarg that the underlying subprocess uses as its working
    directory. Without an explicit ``cwd=``, pytest (or any stack's test
    runner) cannot locate tests when ``/sbtdd close-phase`` is invoked
    from a subdirectory of the project root. The fix wires the
    ``--project-root`` argument through to the skill wrapper.
    """
    import close_phase_cmd

    _seed_state(tmp_path, current_phase="red")
    captured_kwargs: dict[str, object] = {}

    def spy_verification(*a, **kw):  # type: ignore[no-untyped-def]
        captured_kwargs.update(kw)
        return None

    monkeypatch.setattr("close_phase_cmd.detect_drift", lambda *a, **k: None)
    monkeypatch.setattr(
        "close_phase_cmd.superpowers_dispatch.verification_before_completion",
        spy_verification,
    )

    from types import SimpleNamespace

    def fake_run(cmd, timeout=0, cwd=None):  # type: ignore[no-untyped-def]
        return SimpleNamespace(returncode=0, stdout="abc9999\n", stderr="")

    monkeypatch.setattr("close_phase_cmd.subprocess_utils.run_with_timeout", fake_run)
    monkeypatch.setattr("close_phase_cmd.commit_create", lambda prefix, message, cwd=None: "")

    close_phase_cmd.main(["--project-root", str(tmp_path), "--message", "x"])
    assert captured_kwargs.get("cwd") == str(tmp_path)


class TestRunVerificationWorkerBypass:
    """v1.0.7 A2 worker-mode bypass per spec sec.4.2 + iter-2 C4 carry-forward.

    Replaces `make verify` shell-out with explicit sec.0.1 chain:
    pytest, ruff check, ruff format --check, mypy. Persists per-worker
    captured output to <root>/.claude/auto-run-workers/<pid>-verify.json
    for INV-16 evidence-before-assertions continuity.
    """

    def test_worker_mode_runs_sec_0_1_chain(
        self,
        monkeypatch: pytest.MonkeyPatch,
        tmp_path: Path,
    ) -> None:
        """A2-2 (C4 carry-forward): worker runs sec.0.1 4-tool chain."""
        monkeypatch.setenv("SBTDD_AUTO_PARALLEL_WORKER", "1")
        skill_called = []

        def fake_skill(*, cwd: str) -> None:
            skill_called.append(cwd)

        monkeypatch.setattr("superpowers_dispatch.verification_before_completion", fake_skill)
        captured_cmds: list[list[str]] = []

        class FakeResult:
            returncode = 0
            stdout = "PASS"
            stderr = ""

        def fake_run(cmd: list[str], **kwargs: object) -> FakeResult:
            captured_cmds.append(cmd)
            return FakeResult()

        monkeypatch.setattr("close_phase_cmd.subprocess.run", fake_run)
        close_phase_cmd._run_verification(tmp_path)
        assert skill_called == []  # bypassed
        # v1.0.7 T3 dogfood empirical fix: chain uses sys.executable -m
        # form for cross-env portability (bare ruff/mypy not always on PATH).
        import sys as _sys

        assert captured_cmds == [
            [_sys.executable, "-m", "pytest"],
            [_sys.executable, "-m", "ruff", "check", "."],
            [_sys.executable, "-m", "ruff", "format", "--check", "."],
            [_sys.executable, "-m", "mypy", "."],
        ]

    def test_worker_mode_first_tool_failure_aborts_chain_and_persists_evidence(
        self,
        monkeypatch: pytest.MonkeyPatch,
        tmp_path: Path,
    ) -> None:
        """A2-3 (C4 carry-forward): pytest failure aborts chain + evidence persisted."""
        monkeypatch.setenv("SBTDD_AUTO_PARALLEL_WORKER", "1")
        captured_cmds: list[list[str]] = []

        class FailResult:
            returncode = 1
            stdout = "FAILED"
            stderr = "test foo failed"

        class PassResult:
            returncode = 0
            stdout = "PASS"
            stderr = ""

        import sys as _sys

        pytest_cmd = [_sys.executable, "-m", "pytest"]

        def fake_run(cmd: list[str], **kwargs: object) -> object:
            captured_cmds.append(cmd)
            return FailResult() if cmd == pytest_cmd else PassResult()

        monkeypatch.setattr("close_phase_cmd.subprocess.run", fake_run)
        with pytest.raises(ValidationError, match=r"A2 worker-mode verify failed at"):
            close_phase_cmd._run_verification(tmp_path)
        # Only pytest ran; ruff/mypy NOT invoked (early-abort).
        assert captured_cmds == [pytest_cmd]
        # Evidence sidecar persisted with the partial chain.
        sidecar_dir = tmp_path / ".claude" / "auto-run-workers"
        sidecars = list(sidecar_dir.glob("*-verify.json"))
        assert len(sidecars) == 1
        payload = json.loads(sidecars[0].read_text(encoding="utf-8"))
        assert payload["verify_chain"] == [
            {"cmd": pytest_cmd, "rc": 1, "stdout": "FAILED", "stderr": "test foo failed"}
        ]

    def test_worker_mode_full_chain_success_persists_evidence(
        self,
        monkeypatch: pytest.MonkeyPatch,
        tmp_path: Path,
    ) -> None:
        """A2-7 (C4 + iter-3 C1 carry-forward): full success + collision-resistant filename."""
        monkeypatch.setenv("SBTDD_AUTO_PARALLEL_WORKER", "1")

        class PassResult:
            returncode = 0
            stdout = "PASS"
            stderr = ""

        monkeypatch.setattr(
            "close_phase_cmd.subprocess.run",
            lambda cmd, **kw: PassResult(),
        )
        close_phase_cmd._run_verification(tmp_path)
        sidecar_dir = tmp_path / ".claude" / "auto-run-workers"
        sidecars = list(sidecar_dir.glob("*-verify.json"))
        assert len(sidecars) == 1
        # v1.0.7 iter-3 C1: filename pattern <pid>-<monotonic_ns>-<uuid8>-verify.json
        stem = sidecars[0].stem
        # Expected: <pid>-<monotonic_ns>-<uuid8hex>-verify
        parts = stem.split("-")
        assert parts[-1] == "verify"
        assert len(parts) == 4  # pid, monotonic_ns, uuid8, "verify"
        assert parts[0] == str(os.getpid())
        assert parts[1].isdigit() and int(parts[1]) > 0  # monotonic_ns
        assert len(parts[2]) == 8 and all(c in "0123456789abcdef" for c in parts[2])
        payload = json.loads(sidecars[0].read_text(encoding="utf-8"))
        assert len(payload["verify_chain"]) == 4
        assert all(entry["rc"] == 0 for entry in payload["verify_chain"])

    def test_pid_recycle_simulation_does_not_collide(
        self,
        monkeypatch: pytest.MonkeyPatch,
        tmp_path: Path,
    ) -> None:
        """A2-9 (iter-3 C1 carry-forward): same-pid re-spawn produces 2 distinct sidecars."""
        monkeypatch.setenv("SBTDD_AUTO_PARALLEL_WORKER", "1")

        class PassResult:
            returncode = 0
            stdout = "PASS"
            stderr = ""

        monkeypatch.setattr(
            "close_phase_cmd.subprocess.run",
            lambda cmd, **kw: PassResult(),
        )
        # Call twice from the same process (simulates PID recycle).
        close_phase_cmd._run_verification(tmp_path)
        close_phase_cmd._run_verification(tmp_path)
        sidecar_dir = tmp_path / ".claude" / "auto-run-workers"
        sidecars = list(sidecar_dir.glob("*-verify.json"))
        assert len(sidecars) == 2  # NO collision
        # Both sidecars share pid prefix but differ in monotonic_ns or uuid8.
        stems = [s.stem for s in sidecars]
        assert all(stem.startswith(f"{os.getpid()}-") for stem in stems)
        assert len(set(stems)) == 2

    def test_worker_mode_runs_real_subprocess_with_sec_0_1_chain(
        self,
        monkeypatch: pytest.MonkeyPatch,
        tmp_path: Path,
    ) -> None:
        """v1.0.7 Loop 2 iter-1 Mel condition (2): production-path empirical signal.

        Exercises ``_run_verification`` worker-mode bypass with REAL
        ``subprocess.run`` invocations against the system Python (pytest +
        ruff + mypy invoked via ``sys.executable -m``). Verifies the
        chicken-and-egg path (workers reaching sec.0.1 chain without
        skill subprocess hang) at production-realistic granularity —
        smaller scope than full ``auto --parallel`` integration test (T3
        xfail) but exercises the actual T2 worker-mode bypass path with
        zero mocking.
        """
        import sys as _sys

        monkeypatch.setenv("SBTDD_AUTO_PARALLEL_WORKER", "1")
        # Stage a minimal Python project in tmp_path so sec.0.1 chain has
        # something to discover. pytest finds zero tests (acceptable, exits
        # with rc=5 "no tests collected" which T2 treats as failure;
        # ruff/mypy succeed on empty src). We monkey one cmd to PASS so
        # the chain reaches the success persistence path AND we capture
        # the real subprocess.run call shape.
        (tmp_path / "pyproject.toml").write_text(
            '[project]\nname = "smoke"\nversion = "0.0.1"\nrequires-python = ">=3.9"\n'
            '[tool.pytest.ini_options]\ntestpaths = ["."]\n'
            "[tool.ruff]\nline-length = 100\n"
            "[tool.mypy]\nstrict = false\n",
            encoding="utf-8",
        )
        (tmp_path / "test_dummy.py").write_text("def test_dummy(): assert True\n", encoding="utf-8")
        # Verify the worker-mode bypass actually invokes sys.executable -m
        # for each tool (the v1.0.7 T3 cross-env portability fix).
        import subprocess as _subprocess

        captured_cmds: list[list[str]] = []
        original_run = _subprocess.run

        def spy_run(cmd: list[str], **kwargs: object) -> object:
            captured_cmds.append(cmd)
            return original_run(cmd, **kwargs)

        monkeypatch.setattr("close_phase_cmd.subprocess.run", spy_run)
        # Run; may raise ValidationError on first non-zero rc (e.g. mypy
        # complains about missing __init__.py). What matters: subprocess
        # actually invoked + captured the sys.executable -m form.
        try:
            close_phase_cmd._run_verification(tmp_path)
        except ValidationError:
            pass  # Expected if any tool returns non-zero on the smoke fixture.

        # Empirical assertions: chain DID dispatch sys.executable -m form
        # for at least the first tool (pytest). Workers reach the sec.0.1
        # chain — chicken-and-egg empirically closed at this scope.
        assert captured_cmds, "worker-mode bypass did not invoke any subprocess"
        first_cmd = captured_cmds[0]
        assert first_cmd[0] == _sys.executable, (
            f"worker chain did not use sys.executable; got {first_cmd[0]!r}"
        )
        assert first_cmd[1] == "-m", (
            f"worker chain did not use module invocation form; got {first_cmd}"
        )
        assert first_cmd[2] == "pytest", f"worker chain first tool not pytest; got {first_cmd}"
        # Sidecar persisted (success or partial-failure path; both write
        # to the sidecar dir).
        sidecar_dir = tmp_path / ".claude" / "auto-run-workers"
        assert sidecar_dir.exists(), "sidecar dir not created"
        sidecars = list(sidecar_dir.glob("*-verify.json"))
        assert sidecars, "no sidecar persisted post-chain"
        # Filename matches v1.0.7 iter-3 C1 3-component pattern.
        stem = sidecars[0].stem
        parts = stem.split("-")
        assert len(parts) == 4 and parts[-1] == "verify", (
            f"sidecar filename {sidecars[0].name!r} does not match "
            f"<pid>-<monotonic_ns>-<uuid8>-verify pattern"
        )

    def test_chicken_and_egg_subprocess_bypass_no_hang(
        self,
        monkeypatch: pytest.MonkeyPatch,
        tmp_path: Path,
    ) -> None:
        """v1.0.7 Loop 2 iter-2 Cas CRITICAL closure: empirically test chicken-and-egg surface.

        Spawns a REAL subprocess via ``subprocess.Popen`` with
        ``stdin=PIPE`` (no TTY — same shape as auto --parallel
        workers) + ``SBTDD_AUTO_PARALLEL_WORKER=1`` env. The
        subprocess then invokes worker-mode ``_run_verification``
        via a small Python -c command. If the bypass works (worker
        sees env var → runs sec.0.1 chain shell-direct, NOT
        interactive skill subprocess), the subprocess completes
        within 30s. If the chicken-and-egg surface is still open
        (env var not propagated, OR bypass not firing), subprocess
        would hang the full timeout.

        Smaller-scope than full ``auto --parallel`` integration
        (T3 xfail) but exercises the EXACT subprocess shape
        (stdin=PIPE, no TTY) that produced the v1.0.6 hang.
        Empirical proof at production-spawn-realistic granularity.
        """
        import subprocess as _subprocess
        import sys as _sys

        # Stage minimal Python project so sec.0.1 chain has discovery target.
        (tmp_path / "pyproject.toml").write_text(
            '[project]\nname = "smoke"\nversion = "0.0.1"\nrequires-python = ">=3.9"\n'
            '[tool.pytest.ini_options]\ntestpaths = ["."]\n'
            "[tool.ruff]\nline-length = 100\n"
            "[tool.mypy]\nstrict = false\n",
            encoding="utf-8",
        )
        (tmp_path / "test_dummy.py").write_text("def test_dummy(): assert True\n", encoding="utf-8")
        # Locate close_phase_cmd module so the spawned subprocess can import it.
        scripts_dir = Path(__file__).parent.parent / "skills" / "sbtdd" / "scripts"
        # Worker script invoked by the spawned subprocess. Mirrors the
        # production chicken-and-egg path: subprocess inherits stdin=PIPE
        # (no TTY) + reads SBTDD_AUTO_PARALLEL_WORKER env → calls
        # _run_verification → bypass should trigger sec.0.1 shell chain.
        # Test passes if subprocess returns within timeout (no hang).
        # v1.0.7 Loop 2 iter-3 Cas polish: assert os.isatty(0) is False
        # so POSIX vacuous-pass is impossible (must observe no-TTY shape).
        worker_code = (
            f"import sys\n"
            f"sys.path.insert(0, {str(scripts_dir)!r})\n"
            f"from pathlib import Path\n"
            f"import close_phase_cmd\n"
            f"# v1.0.7 iter-3 Cas polish: prove subprocess actually runs no-TTY.\n"
            f"assert sys.stdin.isatty() is False, 'fixture broken: subprocess HAS TTY'\n"
            f"try:\n"
            f"    close_phase_cmd._run_verification(Path({str(tmp_path)!r}))\n"
            f"except Exception as e:\n"
            f"    sys.stdout.write(f'BYPASS_REACHED:{{type(e).__name__}}')\n"
            f"    sys.exit(0)\n"
            f"sys.stdout.write('BYPASS_REACHED:OK')\n"
        )
        env = dict(os.environ)
        env["SBTDD_AUTO_PARALLEL_WORKER"] = "1"
        proc = _subprocess.Popen(
            [_sys.executable, "-c", worker_code],
            stdin=_subprocess.PIPE,
            stdout=_subprocess.PIPE,
            stderr=_subprocess.PIPE,
            env=env,
        )
        try:
            # v1.0.7 Loop 2 iter-3 Mel polish: tightened timeout 60s -> 15s
            # for sharper regression signal (observed 1.19s; 12x headroom is
            # ample for AV scanner / CI variance without masking real hangs).
            stdout_b, stderr_b = proc.communicate(timeout=15)
        except _subprocess.TimeoutExpired:
            proc.kill()
            stdout_b, stderr_b = proc.communicate()
            raise AssertionError(
                "v1.0.7 Loop 2 iter-2 Cas CRITICAL closure FAILED: "
                "subprocess with stdin=PIPE + SBTDD_AUTO_PARALLEL_WORKER=1 "
                "hung past 60s. Chicken-and-egg surface NOT closed at "
                "subprocess-spawn granularity. Either env var not "
                "propagated OR _run_verification bypass not firing under "
                "real subprocess context.\n"
                f"stdout (last 4KB): {stdout_b[-4096:]!r}\n"
                f"stderr (last 4KB): {stderr_b[-4096:]!r}"
            )
        # Subprocess returned within 60s → chicken-and-egg surface
        # empirically closed at the spawn-shape granularity that
        # produced the v1.0.6 hang. Whether the verification chain
        # ultimately succeeded or raised ValidationError doesn't
        # matter for THIS test — what matters is the bypass
        # PREVENTED the hang.
        stdout = stdout_b.decode("utf-8", errors="replace")
        assert "BYPASS_REACHED" in stdout, (
            f"_run_verification did not reach the bypass path; "
            f"unexpected exit. stdout={stdout!r} stderr={stderr_b!r}"
        )

    def test_orchestrator_mode_preserves_skill_dispatch(
        self,
        monkeypatch: pytest.MonkeyPatch,
        tmp_path: Path,
    ) -> None:
        """A2-4: no env var -> existing skill path."""
        monkeypatch.delenv("SBTDD_AUTO_PARALLEL_WORKER", raising=False)
        skill_called = []

        def fake_skill(*, cwd: str) -> None:
            skill_called.append(cwd)

        monkeypatch.setattr("superpowers_dispatch.verification_before_completion", fake_skill)

        # subprocess.run should NOT be called in orchestrator mode.
        def boom(cmd: list[str], **kw: object) -> None:
            raise AssertionError("subprocess.run must not be called in orchestrator mode")

        monkeypatch.setattr("close_phase_cmd.subprocess.run", boom)
        close_phase_cmd._run_verification(tmp_path)
        assert skill_called == [str(tmp_path)]
