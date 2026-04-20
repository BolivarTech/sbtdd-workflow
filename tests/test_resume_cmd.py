# Author: Julian Bolivar
# Version: 1.0.0
# Date: 2026-04-19
"""Tests for /sbtdd resume subcommand (sec.S.5.10, INV-30)."""

from __future__ import annotations

import argparse
from pathlib import Path

import pytest


def test_resume_cmd_module_importable() -> None:
    import resume_cmd

    assert hasattr(resume_cmd, "main")


def test_resume_prints_no_session_and_exits_0_when_state_absent(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    import resume_cmd

    # Create plugin.local.md so plugin_local precondition passes.
    (tmp_path / ".claude").mkdir()
    (tmp_path / ".claude" / "plugin.local.md").write_text(
        "---\nstack: python\n---\n", encoding="utf-8"
    )
    rc = resume_cmd.main(["--project-root", str(tmp_path)])
    out = capsys.readouterr().out
    assert rc == 0
    assert "no active" in out.lower() or "manual" in out.lower()


def test_resume_aborts_when_plugin_local_md_missing(tmp_path: Path) -> None:
    import resume_cmd
    from errors import PreconditionError

    with pytest.raises(PreconditionError):
        resume_cmd.main(["--project-root", str(tmp_path)])


# ---------------------------------------------------------------------------
# Task 33 -- Phase 1 diagnostic read (state, git, tree, artifacts).
# ---------------------------------------------------------------------------


def _setup_git_repo(tmp_path: Path) -> None:
    """Init a git repo with an initial commit so HEAD resolves."""
    import subprocess as _sp

    _sp.run(["git", "init", "-q"], cwd=str(tmp_path), check=True, capture_output=True)
    _sp.run(
        ["git", "config", "user.email", "tester@example.com"],
        cwd=str(tmp_path),
        check=True,
        capture_output=True,
    )
    _sp.run(
        ["git", "config", "user.name", "Tester"],
        cwd=str(tmp_path),
        check=True,
        capture_output=True,
    )
    _sp.run(
        ["git", "config", "commit.gpgsign", "false"],
        cwd=str(tmp_path),
        check=True,
        capture_output=True,
    )
    (tmp_path / "README.md").write_text("initial\n", encoding="utf-8")
    _sp.run(["git", "add", "README.md"], cwd=str(tmp_path), check=True, capture_output=True)
    _sp.run(
        ["git", "commit", "-m", "chore: initial"],
        cwd=str(tmp_path),
        check=True,
        capture_output=True,
    )


def _seed_plugin_local(tmp_path: Path) -> None:
    """Write a minimal plugin.local.md so the plugin_local gate passes."""
    import shutil

    (tmp_path / ".claude").mkdir(exist_ok=True)
    fixture = Path(__file__).parent / "fixtures" / "plugin-locals" / "valid-python.md"
    shutil.copy(fixture, tmp_path / ".claude" / "plugin.local.md")


def _seed_state(
    tmp_path: Path,
    *,
    current_phase: str = "green",
    current_task_id: str | None = "3",
    current_task_title: str | None = "example task",
    plan_approved_at: str | None = "2026-04-20T03:30:00Z",
) -> Path:
    """Write a minimal valid state file into tmp_path/.claude."""
    import json as _json

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
    state_path.write_text(_json.dumps(state), encoding="utf-8")
    return state_path


def test_resume_prints_state_file_fields(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """Diagnostic output contains the 7 critical state fields."""
    import resume_cmd

    _setup_git_repo(tmp_path)
    _seed_plugin_local(tmp_path)
    _seed_state(tmp_path, current_task_id="3", current_phase="green")

    resume_cmd._report_diagnostic(tmp_path)
    out = capsys.readouterr().out
    assert "current_task_id:" in out
    assert "current_task_title:" in out
    assert "current_phase:" in out
    assert "plan_approved_at:" in out
    assert "phase_started_at_commit:" in out
    assert "last_verification_at:" in out
    assert "last_verification_result:" in out
    assert "green" in out
    assert "3" in out


def test_resume_prints_head_commit_info(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """Output contains HEAD short SHA + subject."""
    import resume_cmd

    _setup_git_repo(tmp_path)
    _seed_plugin_local(tmp_path)
    _seed_state(tmp_path)
    resume_cmd._report_diagnostic(tmp_path)
    out = capsys.readouterr().out
    assert "Git HEAD:" in out
    assert "chore: initial" in out


def test_resume_prints_working_tree_status(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """DIRTY when uncommitted; clean when tree is clean."""
    import resume_cmd

    _setup_git_repo(tmp_path)
    _seed_plugin_local(tmp_path)
    _seed_state(tmp_path)
    # Introduce an untracked file.
    (tmp_path / "stray.txt").write_text("dirty", encoding="utf-8")
    resume_cmd._report_diagnostic(tmp_path)
    out = capsys.readouterr().out
    assert "Working tree:" in out
    assert "DIRTY" in out


def test_resume_detects_runtime_artifacts(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """Presence of magi-verdict.json and auto-run.json appears in report."""
    import json as _json

    import resume_cmd

    _setup_git_repo(tmp_path)
    _seed_plugin_local(tmp_path)
    _seed_state(tmp_path)
    (tmp_path / ".claude" / "magi-verdict.json").write_text(
        _json.dumps({"verdict": "GO", "degraded": False}), encoding="utf-8"
    )
    (tmp_path / ".claude" / "auto-run.json").write_text(
        _json.dumps({"auto_started_at": "x"}), encoding="utf-8"
    )
    resume_cmd._report_diagnostic(tmp_path)
    out = capsys.readouterr().out
    assert "magi-verdict.json" in out
    assert "present" in out
    assert "auto-run.json" in out


# ---------------------------------------------------------------------------
# Task 34 -- Phase 1 dependency + drift re-check.
# ---------------------------------------------------------------------------


def _ok_report() -> object:
    from dependency_check import DependencyCheck, DependencyReport

    return DependencyReport(
        checks=(DependencyCheck(name="stub", status="OK", detail="ok", remediation=None),)
    )


def _broken_report() -> object:
    from dependency_check import DependencyCheck, DependencyReport

    return DependencyReport(
        checks=(
            DependencyCheck(name="stub", status="MISSING", detail="nope", remediation="install"),
        )
    )


def test_resume_reruns_dependency_check(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """resume invokes check_environment during re-check phase."""
    import resume_cmd

    _setup_git_repo(tmp_path)
    _seed_plugin_local(tmp_path)
    _seed_state(tmp_path)

    calls = {"n": 0}

    def fake_check(stack: str, root: object, plugins_root: object) -> object:
        calls["n"] += 1
        return _ok_report()

    monkeypatch.setattr(resume_cmd, "check_environment", fake_check)
    monkeypatch.setattr(resume_cmd, "detect_drift", lambda *a, **kw: None)
    resume_cmd._recheck_environment(tmp_path)
    assert calls["n"] == 1


def test_resume_aborts_on_failed_preflight(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Failed pre-flight -> DependencyError."""
    import resume_cmd
    from errors import DependencyError

    _setup_git_repo(tmp_path)
    _seed_plugin_local(tmp_path)
    _seed_state(tmp_path)
    monkeypatch.setattr(resume_cmd, "check_environment", lambda *a, **k: _broken_report())
    with pytest.raises(DependencyError):
        resume_cmd._recheck_environment(tmp_path)


def test_resume_aborts_on_drift(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Drift detection at resume entry -> DriftError."""
    import resume_cmd
    from drift import DriftReport
    from errors import DriftError

    _setup_git_repo(tmp_path)
    _seed_plugin_local(tmp_path)
    _seed_state(tmp_path)
    monkeypatch.setattr(resume_cmd, "check_environment", lambda *a, **k: _ok_report())
    monkeypatch.setattr(
        resume_cmd,
        "detect_drift",
        lambda *a, **kw: DriftReport("green", "refactor", "[ ]", "synthetic"),
    )
    with pytest.raises(DriftError):
        resume_cmd._recheck_environment(tmp_path)


# ---------------------------------------------------------------------------
# Task 35 -- Phase 3 delegation decision tree.
# ---------------------------------------------------------------------------


class _FakeState:
    """Minimal SessionState-shaped stub for decision-tree testing."""

    def __init__(self, current_phase: str, current_task_id: str | None = None) -> None:
        self.current_phase = current_phase
        self.current_task_id = current_task_id


def test_resume_delegates_to_auto_when_phase_red_and_auto_run_present() -> None:
    """state=red + auto-run.json present + tree clean -> auto_cmd."""
    import resume_cmd

    state = _FakeState("red", current_task_id="1")
    module, extra = resume_cmd._decide_delegation(
        state, tree_dirty=False, runtime={"auto-run.json": True, "magi-verdict.json": False}
    )
    assert module == "auto_cmd"
    assert extra == []


def test_resume_delegates_to_pre_merge_when_done_no_verdict() -> None:
    """state=done, no magi-verdict.json, tree clean -> pre_merge_cmd."""
    import resume_cmd

    state = _FakeState("done", current_task_id=None)
    module, _ = resume_cmd._decide_delegation(
        state, tree_dirty=False, runtime={"auto-run.json": False, "magi-verdict.json": False}
    )
    assert module == "pre_merge_cmd"


def test_resume_delegates_to_finalize_when_done_and_verdict_present() -> None:
    """state=done, verdict present, tree clean -> finalize_cmd."""
    import resume_cmd

    state = _FakeState("done", current_task_id=None)
    module, _ = resume_cmd._decide_delegation(
        state, tree_dirty=False, runtime={"auto-run.json": False, "magi-verdict.json": True}
    )
    assert module == "finalize_cmd"


def test_resume_prefers_auto_when_interrupted_mid_auto_at_done_phase() -> None:
    """MAGI Loop 2 iter 1 Finding 9: state=done + auto-run.json + no verdict -> auto.

    An auto run that completed the task loop (phase advanced to done) but
    died before Loop 2 wrote magi-verdict.json should resume as ``auto``
    (which re-enters its own phases with its elevated MAGI budget), NOT
    as fresh ``pre_merge`` (which uses the interactive budget and does
    not update auto-run.json). The signal that auto was active is the
    presence of ``.claude/auto-run.json``; absence of the verdict means
    Loop 2 did not complete.
    """
    import resume_cmd

    state = _FakeState("done", current_task_id=None)
    module, _ = resume_cmd._decide_delegation(
        state,
        tree_dirty=False,
        runtime={"auto-run.json": True, "magi-verdict.json": False},
    )
    assert module == "auto_cmd"


def test_resume_dry_run_prints_plan_without_delegating(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """--dry-run prints 'would delegate to ...' without invoking the target."""
    import resume_cmd

    _setup_git_repo(tmp_path)
    _seed_plugin_local(tmp_path)
    # state=done + verdict present -> decision tree picks finalize
    _seed_state(tmp_path, current_phase="done", current_task_id=None)
    import json as _json

    (tmp_path / ".claude" / "magi-verdict.json").write_text(
        _json.dumps({"verdict": "GO", "degraded": False}), encoding="utf-8"
    )
    monkeypatch.setattr(resume_cmd, "check_environment", lambda *a, **k: _ok_report())
    monkeypatch.setattr(resume_cmd, "detect_drift", lambda *a, **k: None)

    # Spy to detect whether the delegate was actually invoked.
    invoked = {"finalize": 0}

    def fake_delegate(module_name: str, root: Path, extra: list[str]) -> int:
        invoked["finalize"] += 1
        return 0

    monkeypatch.setattr(resume_cmd, "_delegate", fake_delegate)

    rc = resume_cmd.main(["--project-root", str(tmp_path), "--dry-run"])
    out = capsys.readouterr().out
    assert rc == 0
    assert "would delegate" in out.lower() or "dry" in out.lower()
    assert invoked["finalize"] == 0


# ---------------------------------------------------------------------------
# Task 36 -- Phase 4 uncommitted-work resolution with CONTINUE default.
# ---------------------------------------------------------------------------


def _make_ns(**overrides: object) -> "argparse.Namespace":
    """Return a simple namespace mimicking argparse output for Phase 4 tests."""
    ns = argparse.Namespace(
        project_root=Path.cwd(),
        auto=False,
        discard_uncommitted=False,
        dry_run=False,
    )
    for k, v in overrides.items():
        setattr(ns, k, v)
    return ns


def test_resume_auto_continues_when_dirty(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """--auto + tree dirty: does NOT run git reset; prints CONTINUE."""
    import resume_cmd

    _setup_git_repo(tmp_path)
    (tmp_path / "stray.txt").write_text("dirty", encoding="utf-8")

    subprocess_calls: list[list[str]] = []

    def spy_run(cmd: list[str], **kw: object) -> object:
        subprocess_calls.append(cmd)
        import subprocess as _sp

        return _sp.CompletedProcess(cmd, 0, stdout="", stderr="")

    monkeypatch.setattr("resume_cmd.subprocess_utils.run_with_timeout", spy_run)

    ns = _make_ns(project_root=tmp_path, auto=True)
    action = resume_cmd._resolve_uncommitted(ns, tmp_path)
    out = capsys.readouterr().out
    assert action == "CONTINUE"
    # No destructive git calls should have been issued.
    assert not any("checkout" in " ".join(c) for c in subprocess_calls)
    assert not any("clean" in " ".join(c) for c in subprocess_calls)
    assert "CONTINUE" in out


def test_resume_discard_uncommitted_runs_git_checkout_and_clean(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """--discard-uncommitted: subprocess calls include checkout + clean."""
    import resume_cmd

    _setup_git_repo(tmp_path)
    (tmp_path / "stray.txt").write_text("dirty", encoding="utf-8")

    subprocess_calls: list[list[str]] = []

    def spy_run(cmd: list[str], **kw: object) -> object:
        subprocess_calls.append(cmd)
        import subprocess as _sp

        return _sp.CompletedProcess(cmd, 0, stdout="", stderr="")

    monkeypatch.setattr("resume_cmd.subprocess_utils.run_with_timeout", spy_run)

    ns = _make_ns(project_root=tmp_path, discard_uncommitted=True)
    action = resume_cmd._resolve_uncommitted(ns, tmp_path)
    assert action == "RESET"
    flat = [" ".join(c) for c in subprocess_calls]
    assert any("checkout HEAD -- ." in c for c in flat)
    assert any("clean -fd" in c for c in flat)


def test_resume_discard_preserves_gitignored_files(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Files in .gitignore are preserved after --discard-uncommitted.

    git clean -fd respects .gitignore by default (no -x). This test
    verifies the helper calls clean without -x so ignored files stay.
    """
    import resume_cmd

    _setup_git_repo(tmp_path)
    (tmp_path / ".gitignore").write_text(".venv/\n", encoding="utf-8")
    (tmp_path / ".venv").mkdir()
    (tmp_path / ".venv" / "sentinel").write_text("preserved", encoding="utf-8")

    subprocess_calls: list[list[str]] = []

    def spy_run(cmd: list[str], **kw: object) -> object:
        subprocess_calls.append(cmd)
        import subprocess as _sp

        return _sp.CompletedProcess(cmd, 0, stdout="", stderr="")

    monkeypatch.setattr("resume_cmd.subprocess_utils.run_with_timeout", spy_run)

    ns = _make_ns(project_root=tmp_path, discard_uncommitted=True)
    resume_cmd._resolve_uncommitted(ns, tmp_path)
    # The clean command must NOT carry -x (which would remove ignored files).
    for c in subprocess_calls:
        if c[0] == "git" and len(c) >= 2 and c[1] == "clean":
            assert "-x" not in c


def test_resume_interactive_R_choice_triggers_reset(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Interactive 'R' response triggers checkout + clean."""
    import resume_cmd

    _setup_git_repo(tmp_path)
    (tmp_path / "stray.txt").write_text("dirty", encoding="utf-8")

    subprocess_calls: list[list[str]] = []

    def spy_run(cmd: list[str], **kw: object) -> object:
        subprocess_calls.append(cmd)
        import subprocess as _sp

        return _sp.CompletedProcess(cmd, 0, stdout="", stderr="")

    monkeypatch.setattr("resume_cmd.subprocess_utils.run_with_timeout", spy_run)
    monkeypatch.setattr("builtins.input", lambda prompt="": "R")

    ns = _make_ns(project_root=tmp_path)
    action = resume_cmd._resolve_uncommitted(ns, tmp_path)
    assert action == "RESET"
    flat = [" ".join(c) for c in subprocess_calls]
    assert any("checkout HEAD -- ." in c for c in flat)


def test_resume_abort_choice_A_exits_130(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Interactive 'A' response returns ABORT -> main maps to rc=130."""
    import json as _json

    import resume_cmd

    _setup_git_repo(tmp_path)
    _seed_plugin_local(tmp_path)
    # Dirty tree on a TDD phase -> triggers uncommitted-resolution.
    (tmp_path / "stray.txt").write_text("dirty", encoding="utf-8")
    _seed_state(tmp_path, current_phase="green", current_task_id="1")
    # Add plan so drift check does not complain about missing file.
    planning = tmp_path / "planning"
    planning.mkdir(exist_ok=True)
    (planning / "claude-plan-tdd.md").write_text("### Task 1: x\n- [ ] step\n", encoding="utf-8")

    monkeypatch.setattr(resume_cmd, "check_environment", lambda *a, **k: _ok_report())
    monkeypatch.setattr(resume_cmd, "detect_drift", lambda *a, **k: None)
    monkeypatch.setattr("builtins.input", lambda prompt="": "A")
    # magi-verdict absent, auto-run absent irrelevant for this branch.
    _json.dumps({})  # silence unused import

    rc = resume_cmd.main(["--project-root", str(tmp_path)])
    assert rc == 130
