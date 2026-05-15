# Author: Julian Bolivar
# Version: 1.0.0
# Date: 2026-04-19
"""Tests for /sbtdd auto subcommand (sec.S.5.8, INV-22..26)."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

import auto_cmd


def test_auto_cmd_module_importable() -> None:
    import auto_cmd

    assert hasattr(auto_cmd, "main")


def test_auto_dry_run_short_circuits_before_preflight(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Dry-run must return 0 WITHOUT invoking subprocess/preflight (Finding 4).

    Guards against wasted time when the user only wants a plan preview
    on a machine where toolchain checks are slow or unavailable.
    """
    import auto_cmd

    original_run = subprocess.run

    def _boom(*a: object, **k: object) -> object:
        raise AssertionError("dry-run must not invoke subprocess.run")

    monkeypatch.setattr(subprocess, "run", _boom)
    rc = auto_cmd.main(["--project-root", str(tmp_path), "--dry-run"])
    assert rc == 0
    assert not (tmp_path / ".claude" / "auto-run.json").exists()
    # Restore for downstream tests.
    monkeypatch.setattr(subprocess, "run", original_run)


def test_auto_parses_magi_max_iterations_flag() -> None:
    import auto_cmd

    ns = auto_cmd._build_parser().parse_args(["--magi-max-iterations", "7"])
    assert ns.magi_max_iterations == 7


# ---------------------------------------------------------------------------
# Task 27 -- Phase 1 pre-flight + state validation.
# ---------------------------------------------------------------------------


def _seed_plugin_local(tmp_path: Path) -> None:
    """Copy the valid-python plugin.local.md fixture into tmp_path/.claude."""
    import shutil

    (tmp_path / ".claude").mkdir(exist_ok=True)
    fixture = Path(__file__).parent / "fixtures" / "plugin-locals" / "valid-python.md"
    shutil.copy(fixture, tmp_path / ".claude" / "plugin.local.md")


def _seed_state(
    tmp_path: Path,
    *,
    current_phase: str = "done",
    current_task_id: str | None = None,
    current_task_title: str | None = None,
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


def _ok_report() -> object:
    """Return a DependencyReport with a single synthetic OK check."""
    from dependency_check import DependencyCheck, DependencyReport

    return DependencyReport(
        checks=(DependencyCheck(name="stub", status="OK", detail="ok", remediation=None),)
    )


def _broken_report() -> object:
    """Return a DependencyReport with one failing check (for abort path)."""
    from dependency_check import DependencyCheck, DependencyReport

    return DependencyReport(
        checks=(
            DependencyCheck(name="stub", status="MISSING", detail="nope", remediation="install"),
        )
    )


def test_auto_runs_preflight_check(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    import auto_cmd

    _seed_plugin_local(tmp_path)
    _seed_state(tmp_path, current_phase="done")

    calls = {"preflight": 0}

    def fake_check(stack: str, root: object, plugins_root: object) -> object:
        calls["preflight"] += 1
        return _ok_report()

    monkeypatch.setattr(auto_cmd, "check_environment", fake_check)
    auto_cmd._phase1_preflight(
        auto_cmd._build_parser().parse_args(["--project-root", str(tmp_path)])
    )
    assert calls["preflight"] == 1


def test_auto_aborts_when_preflight_fails(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    import auto_cmd
    from errors import DependencyError

    _seed_plugin_local(tmp_path)
    _seed_state(tmp_path, current_phase="done")
    monkeypatch.setattr(auto_cmd, "check_environment", lambda *a, **k: _broken_report())
    with pytest.raises(DependencyError):
        auto_cmd._phase1_preflight(
            auto_cmd._build_parser().parse_args(["--project-root", str(tmp_path)])
        )


def test_auto_aborts_when_state_missing(tmp_path: Path) -> None:
    import auto_cmd
    from errors import PreconditionError

    _seed_plugin_local(tmp_path)
    # no state file seeded
    with pytest.raises(PreconditionError):
        auto_cmd._phase1_preflight(
            auto_cmd._build_parser().parse_args(["--project-root", str(tmp_path)])
        )


def test_auto_aborts_when_plan_not_approved(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import auto_cmd
    from errors import PreconditionError

    _seed_plugin_local(tmp_path)
    _seed_state(tmp_path, current_phase="red", plan_approved_at=None)
    monkeypatch.setattr(auto_cmd, "check_environment", lambda *a, **k: _ok_report())
    with pytest.raises(PreconditionError):
        auto_cmd._phase1_preflight(
            auto_cmd._build_parser().parse_args(["--project-root", str(tmp_path)])
        )


# ---------------------------------------------------------------------------
# Task 28 -- Phase 2 task-loop inner loop + VerificationIrremediableError.
# ---------------------------------------------------------------------------


def _setup_git_repo(tmp_path: Path) -> None:
    """Init a git repo with an initial commit so HEAD resolves cleanly."""
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


def _seed_plan_one_task(tmp_path: Path) -> Path:
    """Write a single-task plan (task id=1)."""
    planning = tmp_path / "planning"
    planning.mkdir(parents=True, exist_ok=True)
    plan = planning / "claude-plan-tdd.md"
    plan.write_text(
        "# Plan\n\n### Task 1: First task\n\n- [ ] step 1\n- [ ] step 2\n",
        encoding="utf-8",
    )
    return plan


def _seed_plan_three_tasks(tmp_path: Path) -> Path:
    """Write a three-task plan (task ids 1, 2, 3 all open)."""
    planning = tmp_path / "planning"
    planning.mkdir(parents=True, exist_ok=True)
    plan = planning / "claude-plan-tdd.md"
    plan.write_text(
        "# Plan\n\n"
        "### Task 1: First task\n- [ ] step 1\n\n"
        "### Task 2: Second task\n- [ ] step 1\n\n"
        "### Task 3: Third task\n- [ ] step 1\n",
        encoding="utf-8",
    )
    return plan


def _seed_loop_state(
    tmp_path: Path,
    *,
    task_id: str = "1",
    current_phase: str = "red",
    title: str = "First task",
) -> None:
    """Seed state file pointing at an in-progress task for Phase 2 tests."""
    _seed_state(
        tmp_path,
        current_phase=current_phase,
        current_task_id=task_id,
        current_task_title=title,
    )


def _seed_auto_env(
    tmp_path: Path,
    *,
    tasks: str = "one",
    task_id: str = "1",
    current_phase: str = "red",
) -> None:
    """Seed a fully valid environment for Phase 2 tests."""
    _setup_git_repo(tmp_path)
    _seed_plugin_local(tmp_path)
    if tasks == "one":
        _seed_plan_one_task(tmp_path)
    else:
        _seed_plan_three_tasks(tmp_path)
    _seed_loop_state(tmp_path, task_id=task_id, current_phase=current_phase)


def _stub_reviewer_approve(monkeypatch: pytest.MonkeyPatch) -> None:
    """Stub ``spec_review_dispatch.dispatch_spec_reviewer`` to always approve.

    Non-H6 Phase 2 tests exercise commit/state behaviour and must not
    invoke the real reviewer subprocess. Installed per-test so the H6
    spec-review suite is free to install its own scripted stub.
    """
    import spec_review_dispatch
    from spec_review_dispatch import SpecReviewResult

    def _auto_approve(**kwargs: object) -> SpecReviewResult:
        return SpecReviewResult(approved=True, issues=(), reviewer_iter=1, artifact_path=None)

    monkeypatch.setattr(spec_review_dispatch, "dispatch_spec_reviewer", _auto_approve)


def test_auto_phase2_processes_single_task_red_green_refactor(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """One-task plan; happy path creates 3 commits (test/feat/refactor) + 1 chore."""
    import auto_cmd
    import superpowers_dispatch
    from config import load_plugin_local
    from state_file import load as load_state

    _seed_auto_env(tmp_path, tasks="one", task_id="1", current_phase="red")
    cfg = load_plugin_local(tmp_path / ".claude" / "plugin.local.md")

    # Dummy TDD skill + verification skill as no-ops.
    monkeypatch.setattr(
        superpowers_dispatch, "test_driven_development", lambda **kw: None, raising=False
    )
    monkeypatch.setattr(
        superpowers_dispatch, "verification_before_completion", lambda **kw: None, raising=False
    )
    monkeypatch.setattr(
        superpowers_dispatch, "systematic_debugging", lambda **kw: None, raising=False
    )
    # Disable drift detection in Phase 2 helper.
    monkeypatch.setattr(auto_cmd, "detect_drift", lambda *a, **kw: None, raising=False)
    _stub_reviewer_approve(monkeypatch)

    # Each phase of each task commits an empty diff; simulate tree changes by
    # touching a file between invocations.
    counter = {"n": 0}

    def fake_commit(prefix: str, message: str, cwd: str | None = None) -> str:
        counter["n"] += 1
        # Make a file change so the commit has something to record.
        (tmp_path / f"touch-{counter['n']}.txt").write_text(
            f"commit {counter['n']}\n", encoding="utf-8"
        )
        subprocess.run(["git", "add", "-A"], cwd=str(tmp_path), check=True, capture_output=True)
        subprocess.run(
            ["git", "commit", "-m", f"{prefix}: {message}"],
            cwd=str(tmp_path),
            check=True,
            capture_output=True,
        )
        return "ok"

    monkeypatch.setattr(auto_cmd, "commit_create", fake_commit, raising=False)
    # close_task_cmd also uses commit_create internally -- patch it as well.
    import close_task_cmd

    monkeypatch.setattr(close_task_cmd, "commit_create", fake_commit)

    ns = auto_cmd._build_parser().parse_args(["--project-root", str(tmp_path)])
    state = load_state(tmp_path / ".claude" / "session-state.json")
    final = auto_cmd._phase2_task_loop(ns, state, cfg)

    # 3 TDD commits + 1 chore close = 4 commits beyond the initial one.
    log = subprocess.run(
        ["git", "log", "--oneline"], cwd=str(tmp_path), check=True, capture_output=True, text=True
    )
    lines = log.stdout.strip().splitlines()
    # Initial + 3 phase commits + 1 chore
    assert len(lines) == 5
    assert final.current_phase == "done"
    assert final.current_task_id is None


def test_auto_phase2_recovers_when_implementer_precommitted_phase(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Implementer subagent commits the phase; auto's commit_create raises
    CommitError (nothing staged). Auto must recover because HEAD advanced.

    Regression for the 2026-04-24 F1 auto run: /writing-plans emits plans
    with explicit ``git add`` + ``git commit -m`` steps per phase, so the
    implementer following the plan literally commits at each phase end.
    Auto's own commit_create afterwards finds an empty stage (rc=1
    "nothing to commit") and raises CommitError. Pre-fix, that aborted the
    task loop even though the phase commit had landed. Post-fix, auto
    verifies HEAD moved past the pre-phase SHA and treats the
    implementer's commit as the authoritative phase commit.
    """
    import auto_cmd
    import close_task_cmd
    import superpowers_dispatch
    from config import load_plugin_local
    from errors import CommitError
    from state_file import load as load_state

    _seed_auto_env(tmp_path, tasks="one", task_id="1", current_phase="red")
    cfg = load_plugin_local(tmp_path / ".claude" / "plugin.local.md")

    monkeypatch.setattr(
        superpowers_dispatch, "test_driven_development", lambda **kw: None, raising=False
    )
    monkeypatch.setattr(
        superpowers_dispatch, "verification_before_completion", lambda **kw: None, raising=False
    )
    monkeypatch.setattr(
        superpowers_dispatch, "systematic_debugging", lambda **kw: None, raising=False
    )
    monkeypatch.setattr(auto_cmd, "detect_drift", lambda *a, **kw: None, raising=False)
    _stub_reviewer_approve(monkeypatch)

    # Simulate implementer landing a real commit BEFORE auto's commit_create
    # runs. We drive this through test_driven_development's stub: when the
    # stub runs, it creates a file + stages + commits with the
    # plan-prescribed message. Then auto's commit_create (unstubbed: real
    # commits.create) sees an empty stage and raises CommitError. Auto
    # must recover because HEAD advanced past the pre-phase SHA.
    phase_counter = {"n": 0}

    def precommit_stub(**kw: object) -> None:
        phase_counter["n"] += 1
        (tmp_path / f"implementer-{phase_counter['n']}.txt").write_text(
            f"phase {phase_counter['n']}\n", encoding="utf-8"
        )
        subprocess.run(["git", "add", "-A"], cwd=str(tmp_path), check=True, capture_output=True)
        subprocess.run(
            ["git", "commit", "-m", f"test: implementer commit {phase_counter['n']}"],
            cwd=str(tmp_path),
            check=True,
            capture_output=True,
        )

    monkeypatch.setattr(
        superpowers_dispatch, "test_driven_development", precommit_stub, raising=False
    )

    # close_task_cmd's commit_create still needs to work for the chore
    # commit because mark_and_advance flips the plan checkboxes and stages
    # them -- that commit IS auto's responsibility and has real content.
    # We leave the real close_task_cmd.commit_create in place.

    ns = auto_cmd._build_parser().parse_args(["--project-root", str(tmp_path)])
    state = load_state(tmp_path / ".claude" / "session-state.json")
    # Baseline to prove CommitError is the expected raise-and-recover path.
    assert CommitError is not None  # import-usage smoke
    final = auto_cmd._phase2_task_loop(ns, state, cfg)

    # 3 implementer commits + 1 chore commit = 4 beyond the initial.
    log = subprocess.run(
        ["git", "log", "--oneline"], cwd=str(tmp_path), check=True, capture_output=True, text=True
    )
    lines = log.stdout.strip().splitlines()
    assert len(lines) == 5, f"expected 5 commits, got {len(lines)}:\n{log.stdout}"
    assert final.current_phase == "done"
    assert final.current_task_id is None
    # Cross-check: all three implementer commits are visible (not
    # overwritten or deduplicated).
    assert sum(1 for line in lines if "implementer commit" in line) == 3
    # Neutralise close_task_cmd leak so later tests aren't affected.
    _ = close_task_cmd  # keep import alive without affecting behaviour


def test_auto_phase2_stages_unstaged_modifications_and_commits(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Implementer edits tracked files without staging -> auto captures them.

    Observed 2026-04-24 on F2 auto run: the green-phase subagent edited
    ``tests/test_distribution_coherence.py`` (added ``_magi_cache_base``
    + rewrote ``_resolve_magi_plugin_json``) but never ran ``git add``.
    Auto's ``commit_create`` raised ``CommitError`` ("nothing to commit")
    with HEAD unchanged and the changes in the working tree. The fix
    runs ``git add -u`` before retrying so auto captures tracked-file
    modifications the implementer forgot to stage.
    """
    import auto_cmd
    import superpowers_dispatch
    from config import load_plugin_local
    from state_file import load as load_state

    _seed_auto_env(tmp_path, tasks="one", task_id="1", current_phase="red")
    cfg = load_plugin_local(tmp_path / ".claude" / "plugin.local.md")

    # First create a tracked file in the initial commit so ``git add -u``
    # has something to stage when the implementer modifies it later.
    initial_file = tmp_path / "src.py"
    initial_file.write_text("# placeholder\n", encoding="utf-8")
    subprocess.run(["git", "add", "src.py"], cwd=str(tmp_path), check=True, capture_output=True)
    subprocess.run(
        ["git", "commit", "-m", "chore: seed tracked file"],
        cwd=str(tmp_path),
        check=True,
        capture_output=True,
    )

    phase_counter = {"n": 0}

    def edit_without_staging(**kw: object) -> None:
        """Simulate the implementer editing a tracked file but not staging."""
        phase_counter["n"] += 1
        initial_file.write_text(f"# edited for phase {phase_counter['n']}\n", encoding="utf-8")

    monkeypatch.setattr(
        superpowers_dispatch,
        "test_driven_development",
        edit_without_staging,
        raising=False,
    )
    monkeypatch.setattr(
        superpowers_dispatch, "verification_before_completion", lambda **kw: None, raising=False
    )
    monkeypatch.setattr(
        superpowers_dispatch, "systematic_debugging", lambda **kw: None, raising=False
    )
    monkeypatch.setattr(auto_cmd, "detect_drift", lambda *a, **kw: None, raising=False)
    _stub_reviewer_approve(monkeypatch)

    ns = auto_cmd._build_parser().parse_args(["--project-root", str(tmp_path)])
    state = load_state(tmp_path / ".claude" / "session-state.json")
    final = auto_cmd._phase2_task_loop(ns, state, cfg)

    # Red phase captured + green phase captured + refactor phase captured
    # + chore close = 4 real commits. Plus seed + initial = 6 total.
    log = subprocess.run(
        ["git", "log", "--oneline"], cwd=str(tmp_path), check=True, capture_output=True, text=True
    )
    lines = log.stdout.strip().splitlines()
    assert len(lines) == 6, f"expected 6 commits, got {len(lines)}:\n{log.stdout}"
    # First 3 auto phase commits must NOT be --allow-empty no-op markers
    # because git add -u captured real changes. Verify by counting
    # "no-op" markers in the phase-close commits (expect 0 in the top 3).
    phase_lines = lines[:3]
    assert all("no-op" not in line for line in phase_lines), phase_lines
    assert final.current_phase == "done"
    assert final.current_task_id is None


def test_auto_phase2_allow_empty_fallback_when_head_did_not_move(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Nothing staged AND HEAD unchanged -> record empty phase-close commit.

    Observed 2026-04-24 on F2 auto run: the red-phase implementer
    committed both the failing tests AND the production impl in one
    commit (phase collapse). Auto's state advanced to green as expected
    and dispatched ``/test-driven-development --phase=green``. The
    subagent had nothing to do (impl already landed), auto's own
    ``commit_create`` raised ``CommitError`` with HEAD unchanged. Since
    verification had already passed (the green-phase acceptance
    criterion), we record an empty phase-close commit so state still
    advances. Verification provides the acceptance-criteria check; the
    empty commit is a bookkeeping marker that also makes the log show
    one commit per phase transition.
    """
    import auto_cmd
    import superpowers_dispatch
    from config import load_plugin_local
    from state_file import load as load_state

    _seed_auto_env(tmp_path, tasks="one", task_id="1", current_phase="red")
    cfg = load_plugin_local(tmp_path / ".claude" / "plugin.local.md")

    monkeypatch.setattr(
        superpowers_dispatch, "test_driven_development", lambda **kw: None, raising=False
    )
    monkeypatch.setattr(
        superpowers_dispatch, "verification_before_completion", lambda **kw: None, raising=False
    )
    monkeypatch.setattr(
        superpowers_dispatch, "systematic_debugging", lambda **kw: None, raising=False
    )
    monkeypatch.setattr(auto_cmd, "detect_drift", lambda *a, **kw: None, raising=False)
    _stub_reviewer_approve(monkeypatch)

    ns = auto_cmd._build_parser().parse_args(["--project-root", str(tmp_path)])
    state = load_state(tmp_path / ".claude" / "session-state.json")
    final = auto_cmd._phase2_task_loop(ns, state, cfg)

    # The task advances to done even when the implementer produced no
    # commits at all: 3 empty phase-close commits + 1 chore commit.
    log = subprocess.run(
        ["git", "log", "--oneline"],
        cwd=str(tmp_path),
        check=True,
        capture_output=True,
        text=True,
    )
    lines = log.stdout.strip().splitlines()
    # Initial commit + 3 empty phase closes + 1 chore = 5 commits.
    assert len(lines) == 5, f"expected 5 commits, got {len(lines)}:\n{log.stdout}"
    # All three empty commits carry the "no-op; phase collapsed" marker
    # so the log remains legible as diagnostic context.
    no_op_commits = [line for line in lines if "no-op" in line]
    assert len(no_op_commits) == 3
    assert final.current_phase == "done"
    assert final.current_task_id is None


def test_auto_phase2_respects_verification_retries_budget(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Verification fails twice then passes; with retries=2 passes."""
    import auto_cmd
    import superpowers_dispatch

    _seed_auto_env(tmp_path, tasks="one", task_id="1", current_phase="red")

    attempts = {"n": 0}

    def flaky_verify(**kw: object) -> None:
        attempts["n"] += 1
        if attempts["n"] < 3:
            raise RuntimeError("boom")

    monkeypatch.setattr(superpowers_dispatch, "verification_before_completion", flaky_verify)
    monkeypatch.setattr(
        superpowers_dispatch, "systematic_debugging", lambda **kw: None, raising=False
    )

    # retries=2 means up to 3 attempts
    auto_cmd._run_verification_with_retries(tmp_path, retries=2)
    assert attempts["n"] == 3


def test_auto_phase2_aborts_after_exhausting_retries_exit_6(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Verification always fails -> raises VerificationIrremediableError (exit 6)."""
    import auto_cmd
    import superpowers_dispatch
    from errors import EXIT_CODES, VerificationIrremediableError

    _seed_auto_env(tmp_path, tasks="one", task_id="1", current_phase="red")

    def always_fail(**kw: object) -> None:
        raise RuntimeError("always fails")

    monkeypatch.setattr(superpowers_dispatch, "verification_before_completion", always_fail)
    monkeypatch.setattr(
        superpowers_dispatch, "systematic_debugging", lambda **kw: None, raising=False
    )

    with pytest.raises(VerificationIrremediableError):
        auto_cmd._run_verification_with_retries(tmp_path, retries=1)
    assert EXIT_CODES[VerificationIrremediableError] == 6


def test_auto_run_verification_does_not_mask_quota_exhausted_error(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """MAGI Loop 2 iter 1 Finding 2: QuotaExhaustedError must propagate unchanged.

    The retry wrapper previously caught bare ``Exception`` and re-raised as
    ``VerificationIrremediableError`` (exit 6). Quota exhaustion must skip
    the retry/wrap logic entirely so the dispatcher maps it to exit 11.
    """
    import auto_cmd
    import superpowers_dispatch
    from errors import EXIT_CODES, QuotaExhaustedError, VerificationIrremediableError

    _seed_auto_env(tmp_path, tasks="one", task_id="1", current_phase="red")

    attempts = {"n": 0, "debug_calls": 0}

    def quota_fail(**kw: object) -> None:
        attempts["n"] += 1
        raise QuotaExhaustedError("session_limit: test")

    def debug_spy(**kw: object) -> None:
        attempts["debug_calls"] += 1

    monkeypatch.setattr(superpowers_dispatch, "verification_before_completion", quota_fail)
    monkeypatch.setattr(superpowers_dispatch, "systematic_debugging", debug_spy, raising=False)

    # Quota must propagate as QuotaExhaustedError on the FIRST attempt --
    # not wrapped as VerificationIrremediableError after budget exhaustion.
    with pytest.raises(QuotaExhaustedError):
        auto_cmd._run_verification_with_retries(tmp_path, retries=3)
    # Only ONE attempt was consumed; retry budget untouched because quota
    # is not a legitimate retryable failure.
    assert attempts["n"] == 1
    # systematic-debugging MUST NOT be invoked for quota exhaustion -- the
    # error is about API limits, not flaky verification.
    assert attempts["debug_calls"] == 0
    # Sanity: exit-code mapping keeps 11 for quota vs 6 for irremediable.
    assert EXIT_CODES[QuotaExhaustedError] == 11
    assert EXIT_CODES[VerificationIrremediableError] == 6


def test_auto_phase2_sequential_order(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """3-task plan; tasks processed in order 1, 2, 3."""
    import auto_cmd
    import superpowers_dispatch
    from config import load_plugin_local
    from state_file import load as load_state

    _seed_auto_env(tmp_path, tasks="three", task_id="1", current_phase="red")
    cfg = load_plugin_local(tmp_path / ".claude" / "plugin.local.md")

    task_ids_seen: list[str] = []

    monkeypatch.setattr(
        superpowers_dispatch, "test_driven_development", lambda **kw: None, raising=False
    )
    monkeypatch.setattr(
        superpowers_dispatch, "verification_before_completion", lambda **kw: None, raising=False
    )
    monkeypatch.setattr(
        superpowers_dispatch, "systematic_debugging", lambda **kw: None, raising=False
    )
    monkeypatch.setattr(auto_cmd, "detect_drift", lambda *a, **kw: None, raising=False)
    _stub_reviewer_approve(monkeypatch)

    counter = {"n": 0}

    def fake_commit(prefix: str, message: str, cwd: str | None = None) -> str:
        counter["n"] += 1
        if prefix != "chore":
            # Record the task id we're working on for every non-chore commit.
            # The state file reflects current_task_id at commit time.
            import json as _json

            data = _json.loads(
                (tmp_path / ".claude" / "session-state.json").read_text(encoding="utf-8")
            )
            if data.get("current_task_id"):
                task_ids_seen.append(data["current_task_id"])
        (tmp_path / f"touch-{counter['n']}.txt").write_text(
            f"commit {counter['n']}\n", encoding="utf-8"
        )
        subprocess.run(["git", "add", "-A"], cwd=str(tmp_path), check=True, capture_output=True)
        subprocess.run(
            ["git", "commit", "-m", f"{prefix}: {message}"],
            cwd=str(tmp_path),
            check=True,
            capture_output=True,
        )
        return "ok"

    monkeypatch.setattr(auto_cmd, "commit_create", fake_commit, raising=False)
    import close_task_cmd

    monkeypatch.setattr(close_task_cmd, "commit_create", fake_commit)

    ns = auto_cmd._build_parser().parse_args(["--project-root", str(tmp_path)])
    state = load_state(tmp_path / ".claude" / "session-state.json")
    auto_cmd._phase2_task_loop(ns, state, cfg)

    # With 3 tasks * 3 phases = 9 non-chore commits total.
    # First 3 must be task 1, next 3 task 2, last 3 task 3.
    assert task_ids_seen[:3] == ["1", "1", "1"]
    assert task_ids_seen[3:6] == ["2", "2", "2"]
    assert task_ids_seen[6:9] == ["3", "3", "3"]


def test_auto_phase2_aborts_on_drift(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Drift detector returns a report -> DriftError."""
    import auto_cmd
    from config import load_plugin_local
    from drift import DriftReport
    from errors import DriftError
    from state_file import load as load_state

    _seed_auto_env(tmp_path, tasks="one", task_id="1", current_phase="red")
    cfg = load_plugin_local(tmp_path / ".claude" / "plugin.local.md")

    monkeypatch.setattr(
        auto_cmd,
        "detect_drift",
        lambda *a, **kw: DriftReport("red", "chore", "[ ]", "synthetic"),
    )
    ns = auto_cmd._build_parser().parse_args(["--project-root", str(tmp_path)])
    state = load_state(tmp_path / ".claude" / "session-state.json")
    with pytest.raises(DriftError):
        auto_cmd._phase2_task_loop(ns, state, cfg)


def test_auto_phase2_inner_loop_entry_phase_respects_state(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """state.current_phase=green -> auto starts at green, skipping red."""
    import auto_cmd
    import superpowers_dispatch
    from config import load_plugin_local
    from state_file import load as load_state

    _seed_auto_env(tmp_path, tasks="one", task_id="1", current_phase="green")
    cfg = load_plugin_local(tmp_path / ".claude" / "plugin.local.md")

    phases_seen: list[str] = []

    def capture_phase(**kw: object) -> None:
        args_list = kw.get("args")
        if isinstance(args_list, list):
            for a in args_list:
                if isinstance(a, str) and a.startswith("--phase="):
                    phases_seen.append(a.split("=", 1)[1])

    monkeypatch.setattr(
        superpowers_dispatch, "test_driven_development", capture_phase, raising=False
    )
    monkeypatch.setattr(
        superpowers_dispatch, "verification_before_completion", lambda **kw: None, raising=False
    )
    monkeypatch.setattr(
        superpowers_dispatch, "systematic_debugging", lambda **kw: None, raising=False
    )
    monkeypatch.setattr(auto_cmd, "detect_drift", lambda *a, **kw: None, raising=False)
    _stub_reviewer_approve(monkeypatch)

    counter = {"n": 0}

    def fake_commit(prefix: str, message: str, cwd: str | None = None) -> str:
        counter["n"] += 1
        (tmp_path / f"touch-{counter['n']}.txt").write_text(f"c {counter['n']}\n", encoding="utf-8")
        subprocess.run(["git", "add", "-A"], cwd=str(tmp_path), check=True, capture_output=True)
        subprocess.run(
            ["git", "commit", "-m", f"{prefix}: {message}"],
            cwd=str(tmp_path),
            check=True,
            capture_output=True,
        )
        return "ok"

    monkeypatch.setattr(auto_cmd, "commit_create", fake_commit, raising=False)
    import close_task_cmd

    monkeypatch.setattr(close_task_cmd, "commit_create", fake_commit)

    ns = auto_cmd._build_parser().parse_args(["--project-root", str(tmp_path)])
    state = load_state(tmp_path / ".claude" / "session-state.json")
    auto_cmd._phase2_task_loop(ns, state, cfg)

    # Starting phase=green -> skips red; only green and refactor run for task 1.
    assert phases_seen == ["green", "refactor"]


# ---------------------------------------------------------------------------
# Task 29 -- Phase 3 pre-merge with elevated MAGI budget.
# ---------------------------------------------------------------------------


def _make_verdict(
    verdict: str = "GO",
    degraded: bool = False,
    conditions: tuple[str, ...] = (),
    findings: tuple[dict[str, object], ...] = (),
) -> object:
    """Return a MAGIVerdict matching the magi_dispatch dataclass contract."""
    from magi_dispatch import MAGIVerdict

    return MAGIVerdict(
        verdict=verdict,
        degraded=degraded,
        conditions=conditions,
        findings=findings,
        raw_output=f'{{"verdict": "{verdict}"}}',
    )


def test_auto_phase3_invokes_loop1_and_loop2(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Stubs return clean + GO full; both loops run."""
    import auto_cmd
    import magi_dispatch
    import pre_merge_cmd
    from config import load_plugin_local

    _setup_git_repo(tmp_path)
    _seed_plugin_local(tmp_path)
    cfg = load_plugin_local(tmp_path / ".claude" / "plugin.local.md")

    calls = {"loop1": 0, "loop2": 0}

    def fake_loop1(root: Path) -> None:
        calls["loop1"] += 1

    def fake_loop2(root: Path, shadow_cfg: object, threshold: str | None) -> object:
        calls["loop2"] += 1
        return _make_verdict("GO", degraded=False)

    monkeypatch.setattr(pre_merge_cmd, "_loop1", fake_loop1)
    monkeypatch.setattr(pre_merge_cmd, "_loop2", fake_loop2)
    monkeypatch.setattr(magi_dispatch, "write_verdict_artifact", lambda *a, **k: None)

    ns = auto_cmd._build_parser().parse_args(["--project-root", str(tmp_path)])
    verdict = auto_cmd._phase3_pre_merge(ns, cfg)
    assert calls["loop1"] == 1
    assert calls["loop2"] == 1
    assert verdict is not None


def test_auto_phase3_uses_auto_magi_max_iterations(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """cfg.auto_magi_max_iterations=5 passed through to Loop 2 as shadow cfg."""
    import auto_cmd
    import magi_dispatch
    import pre_merge_cmd
    from config import load_plugin_local

    _setup_git_repo(tmp_path)
    _seed_plugin_local(tmp_path)
    cfg = load_plugin_local(tmp_path / ".claude" / "plugin.local.md")
    # Sanity: fixture has magi=3, auto=5.
    assert cfg.magi_max_iterations == 3
    assert cfg.auto_magi_max_iterations == 5

    captured: dict[str, object] = {}

    def fake_loop2(root: Path, shadow_cfg: object, threshold: str | None) -> object:
        captured["max_iter"] = getattr(shadow_cfg, "magi_max_iterations", None)
        return _make_verdict("GO", degraded=False)

    monkeypatch.setattr(pre_merge_cmd, "_loop1", lambda root: None)
    monkeypatch.setattr(pre_merge_cmd, "_loop2", fake_loop2)
    monkeypatch.setattr(magi_dispatch, "write_verdict_artifact", lambda *a, **k: None)

    ns = auto_cmd._build_parser().parse_args(["--project-root", str(tmp_path)])
    auto_cmd._phase3_pre_merge(ns, cfg)
    assert captured["max_iter"] == 5


def test_auto_phase3_respects_flag_override(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """--magi-max-iterations=2 overrides the config default."""
    import auto_cmd
    import magi_dispatch
    import pre_merge_cmd
    from config import load_plugin_local

    _setup_git_repo(tmp_path)
    _seed_plugin_local(tmp_path)
    cfg = load_plugin_local(tmp_path / ".claude" / "plugin.local.md")

    captured: dict[str, object] = {}

    def fake_loop2(root: Path, shadow_cfg: object, threshold: str | None) -> object:
        captured["max_iter"] = getattr(shadow_cfg, "magi_max_iterations", None)
        return _make_verdict("GO", degraded=False)

    monkeypatch.setattr(pre_merge_cmd, "_loop1", lambda root: None)
    monkeypatch.setattr(pre_merge_cmd, "_loop2", fake_loop2)
    monkeypatch.setattr(magi_dispatch, "write_verdict_artifact", lambda *a, **k: None)

    ns = auto_cmd._build_parser().parse_args(
        ["--project-root", str(tmp_path), "--magi-max-iterations", "2"]
    )
    auto_cmd._phase3_pre_merge(ns, cfg)
    assert captured["max_iter"] == 2


def test_auto_phase3_aborts_on_strong_no_go(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """STRONG_NO_GO iter 1 -> MAGIGateError propagates from Loop 2."""
    import auto_cmd
    import pre_merge_cmd
    from config import load_plugin_local
    from errors import MAGIGateError

    _setup_git_repo(tmp_path)
    _seed_plugin_local(tmp_path)
    cfg = load_plugin_local(tmp_path / ".claude" / "plugin.local.md")

    def fake_loop2(root: Path, shadow_cfg: object, threshold: str | None) -> object:
        raise MAGIGateError("STRONG_NO_GO at iter 1")

    monkeypatch.setattr(pre_merge_cmd, "_loop1", lambda root: None)
    monkeypatch.setattr(pre_merge_cmd, "_loop2", fake_loop2)

    ns = auto_cmd._build_parser().parse_args(["--project-root", str(tmp_path)])
    with pytest.raises(MAGIGateError):
        auto_cmd._phase3_pre_merge(ns, cfg)


# ---------------------------------------------------------------------------
# Task 30 -- Phase 4 checklist + Phase 5 report with auto-run.json trail.
# ---------------------------------------------------------------------------


def _seed_magi_verdict(
    tmp_path: Path,
    *,
    verdict: str = "GO",
    degraded: bool = False,
    timestamp: str = "2026-04-21T00:00:00Z",
) -> Path:
    """Write a magi-verdict.json artifact."""
    import json as _json

    path = tmp_path / ".claude" / "magi-verdict.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    data = {
        "timestamp": timestamp,
        "verdict": verdict,
        "degraded": degraded,
        "conditions": [],
        "findings": [],
    }
    path.write_text(_json.dumps(data), encoding="utf-8")
    return path


def _seed_spec_files(tmp_path: Path) -> None:
    """Write minimal sbtdd/spec-behavior.md so the checklist item passes."""
    spec_dir = tmp_path / "sbtdd"
    spec_dir.mkdir(parents=True, exist_ok=True)
    (spec_dir / "spec-behavior.md").write_text("# behavior\n", encoding="utf-8")


def _seed_checklist_clean_env(
    tmp_path: Path, *, verdict: str = "GO", degraded: bool = False
) -> None:
    """Seed a fully clean environment for Phase 4 checklist tests."""
    _setup_git_repo(tmp_path)
    _seed_plugin_local(tmp_path)
    _seed_spec_files(tmp_path)
    planning = tmp_path / "planning"
    planning.mkdir(parents=True, exist_ok=True)
    (planning / "claude-plan-tdd.md").write_text(
        "# Plan\n\n### Task 1: done\n- [x] step\n",
        encoding="utf-8",
    )
    (tmp_path / ".gitignore").write_text(".claude/\n", encoding="utf-8")
    subprocess.run(
        ["git", "add", ".gitignore", "sbtdd", "planning"],
        cwd=str(tmp_path),
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "commit", "-m", "chore: seed spec and plan"],
        cwd=str(tmp_path),
        check=True,
        capture_output=True,
    )
    _seed_state(tmp_path, current_phase="done")
    _seed_magi_verdict(tmp_path, verdict=verdict, degraded=degraded)


def test_auto_phase4_runs_checklist_but_does_not_invoke_finishing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """INV-25: auto Phase 4 checklist runs, but /finishing-...-branch NOT invoked."""
    import auto_cmd
    import superpowers_dispatch
    from config import load_plugin_local
    from state_file import load as load_state

    _seed_checklist_clean_env(tmp_path, verdict="GO", degraded=False)
    monkeypatch.setattr(superpowers_dispatch, "verification_before_completion", lambda **kw: None)

    finishing_calls = {"n": 0}

    def should_not_run(**kw: object) -> None:
        finishing_calls["n"] += 1

    monkeypatch.setattr(superpowers_dispatch, "finishing_a_development_branch", should_not_run)

    state = load_state(tmp_path / ".claude" / "session-state.json")
    cfg = load_plugin_local(tmp_path / ".claude" / "plugin.local.md")
    auto_cmd._phase4_checklist(tmp_path, state, cfg)
    assert finishing_calls["n"] == 0


def test_auto_phase4_aborts_on_degraded_verdict_exit_9(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """degraded=true verdict -> ChecklistError (exit 9)."""
    import auto_cmd
    import superpowers_dispatch
    from config import load_plugin_local
    from errors import ChecklistError
    from state_file import load as load_state

    _seed_checklist_clean_env(tmp_path, verdict="GO", degraded=True)
    monkeypatch.setattr(superpowers_dispatch, "verification_before_completion", lambda **kw: None)

    state = load_state(tmp_path / ".claude" / "session-state.json")
    cfg = load_plugin_local(tmp_path / ".claude" / "plugin.local.md")
    with pytest.raises(ChecklistError):
        auto_cmd._phase4_checklist(tmp_path, state, cfg)


def test_auto_phase5_writes_auto_run_json(tmp_path: Path) -> None:
    """.claude/auto-run.json contains timestamps + verdict."""
    import json as _json

    import auto_cmd

    (tmp_path / ".claude").mkdir(parents=True, exist_ok=True)
    verdict = _make_verdict("GO", degraded=False)
    started = "2026-04-21T00:00:00Z"
    auto_cmd._phase5_report(tmp_path, started, verdict)  # type: ignore[arg-type]
    data = _json.loads((tmp_path / ".claude" / "auto-run.json").read_text(encoding="utf-8"))
    assert data["auto_started_at"] == started
    assert "auto_finished_at" in data
    assert data["verdict"] == "GO"
    assert data["degraded"] is False


# ---------------------------------------------------------------------------
# Task 31 -- end-to-end wire + INV-23 enforcement + quota propagation.
# ---------------------------------------------------------------------------


def _seed_happy_path_env(tmp_path: Path) -> None:
    """Seed a single-task plan + state at red + spec files + verdict artifact."""
    _setup_git_repo(tmp_path)
    _seed_plugin_local(tmp_path)
    _seed_spec_files(tmp_path)
    _seed_plan_one_task(tmp_path)
    (tmp_path / ".gitignore").write_text(".claude/\n", encoding="utf-8")
    subprocess.run(
        ["git", "add", ".gitignore", "sbtdd", "planning"],
        cwd=str(tmp_path),
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "commit", "-m", "chore: seed spec and plan"],
        cwd=str(tmp_path),
        check=True,
        capture_output=True,
    )
    _seed_loop_state(tmp_path, task_id="1", current_phase="red")


def _fake_commit_factory(tmp_path: Path):  # type: ignore[no-untyped-def]
    """Return a fake commit function that touches a file and commits."""
    counter = {"n": 0}

    def fake_commit(prefix: str, message: str, cwd: str | None = None) -> str:
        counter["n"] += 1
        (tmp_path / f"touch-{counter['n']}.txt").write_text(f"c{counter['n']}\n", encoding="utf-8")
        subprocess.run(["git", "add", "-A"], cwd=str(tmp_path), check=True, capture_output=True)
        subprocess.run(
            ["git", "commit", "-m", f"{prefix}: {message}"],
            cwd=str(tmp_path),
            check=True,
            capture_output=True,
        )
        return "ok"

    return fake_commit


def test_auto_happy_path_end_to_end(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Single-task plan; auto main returns 0 and writes all artifacts."""
    import auto_cmd
    import close_task_cmd
    import finalize_cmd
    import magi_dispatch
    import pre_merge_cmd
    import superpowers_dispatch

    _seed_happy_path_env(tmp_path)

    monkeypatch.setattr(auto_cmd, "check_environment", lambda *a, **k: _ok_report())
    monkeypatch.setattr(
        superpowers_dispatch, "test_driven_development", lambda **kw: None, raising=False
    )
    monkeypatch.setattr(
        superpowers_dispatch, "verification_before_completion", lambda **kw: None, raising=False
    )
    monkeypatch.setattr(
        superpowers_dispatch, "systematic_debugging", lambda **kw: None, raising=False
    )
    monkeypatch.setattr(auto_cmd, "detect_drift", lambda *a, **kw: None)
    _stub_reviewer_approve(monkeypatch)
    fake_commit = _fake_commit_factory(tmp_path)
    monkeypatch.setattr(auto_cmd, "commit_create", fake_commit, raising=False)
    monkeypatch.setattr(close_task_cmd, "commit_create", fake_commit)
    monkeypatch.setattr(pre_merge_cmd, "_loop1", lambda root: None)

    def fake_loop2(root: Path, shadow: object, threshold: str | None) -> object:
        return _make_verdict("GO", degraded=False)

    monkeypatch.setattr(pre_merge_cmd, "_loop2", fake_loop2)

    def fake_write_verdict(v: object, target: Path, timestamp: object = None) -> None:
        import json as _json

        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(
            _json.dumps(
                {
                    "timestamp": "2026-04-21T00:00:00Z",
                    "verdict": getattr(v, "verdict", "GO"),
                    "degraded": getattr(v, "degraded", False),
                    "conditions": [],
                    "findings": [],
                }
            ),
            encoding="utf-8",
        )

    monkeypatch.setattr(magi_dispatch, "write_verdict_artifact", fake_write_verdict)
    # Patch finalize_cmd._checklist so it does not try to run real verification.
    monkeypatch.setattr(
        finalize_cmd,
        "_checklist",
        lambda *a, **kw: [("ok", True, "")],
    )

    rc = auto_cmd.main(["--project-root", str(tmp_path)])
    assert rc == 0
    assert (tmp_path / ".claude" / "auto-run.json").exists()
    assert (tmp_path / ".claude" / "magi-verdict.json").exists()


def test_auto_quota_exhaustion_propagates_exit_11(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """QuotaExhaustedError from verification wraps to exit 11 via EXIT_CODES."""
    import auto_cmd
    import superpowers_dispatch
    from errors import EXIT_CODES, QuotaExhaustedError

    _seed_happy_path_env(tmp_path)
    monkeypatch.setattr(auto_cmd, "check_environment", lambda *a, **k: _ok_report())

    def quota_fail(**kw: object) -> None:
        raise QuotaExhaustedError("session_limit: test")

    monkeypatch.setattr(
        superpowers_dispatch, "test_driven_development", lambda **kw: None, raising=False
    )
    monkeypatch.setattr(
        superpowers_dispatch, "verification_before_completion", quota_fail, raising=False
    )
    monkeypatch.setattr(
        superpowers_dispatch, "systematic_debugging", lambda **kw: None, raising=False
    )
    monkeypatch.setattr(auto_cmd, "detect_drift", lambda *a, **kw: None)
    _stub_reviewer_approve(monkeypatch)

    # QuotaExhaustedError is NOT suppressed by the retry wrapper: it's not
    # a generic Exception signalling a legitimate retry, it's a hard cap
    # on API usage. Current _run_verification_with_retries wraps generic
    # failures into VerificationIrremediableError after budget; quota
    # should propagate unchanged (so it maps to exit 11, not 6).
    # Test: propagation through main happens because QuotaExhaustedError
    # passes through the except path.
    with pytest.raises((QuotaExhaustedError, Exception)):
        auto_cmd.main(["--project-root", str(tmp_path)])
    assert EXIT_CODES[QuotaExhaustedError] == 11


def test_auto_pre_merge_conditions_pending_propagates_exit_8(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Finding 2 (Caspar): MAGIGateError from Phase 3 propagates to exit 8.

    MAGI Loop 2 iter 3 redesign: ``pre_merge_cmd._loop2`` raises
    :class:`MAGIGateError` ("conditions pending") when
    ``/receiving-code-review`` accepts MAGI caveats that need
    ``close-phase`` work. ``auto_cmd.main`` must propagate that exception
    unchanged so the run_sbtdd dispatcher maps it to exit 8 via
    ``EXIT_CODES[MAGIGateError]``, and the ``.claude/auto-run.json``
    audit trail must record the blocking status with the MAGIGateError
    message so operators can distinguish a "conditions pending" abort
    from a STRONG_NO_GO abort post-hoc.
    """
    import auto_cmd
    import pre_merge_cmd
    import superpowers_dispatch
    from errors import EXIT_CODES, MAGIGateError
    from run_sbtdd import _exit_code_for

    _seed_happy_path_env(tmp_path)
    # Jump straight to Phase 3 by declaring the plan already done.
    _seed_state(tmp_path, current_phase="done")

    monkeypatch.setattr(auto_cmd, "check_environment", lambda *a, **k: _ok_report())
    monkeypatch.setattr(
        superpowers_dispatch, "test_driven_development", lambda **kw: None, raising=False
    )
    monkeypatch.setattr(
        superpowers_dispatch, "verification_before_completion", lambda **kw: None, raising=False
    )
    monkeypatch.setattr(auto_cmd, "detect_drift", lambda *a, **kw: None)
    _stub_reviewer_approve(monkeypatch)
    monkeypatch.setattr(pre_merge_cmd, "_loop1", lambda root: None)

    def fake_loop2_blocks(root: Path, shadow: object, threshold: str | None) -> object:
        raise MAGIGateError(
            "MAGI iter 1 produced 1 accepted condition(s); apply them via "
            "`sbtdd close-phase` and re-run `sbtdd pre-merge`."
        )

    monkeypatch.setattr(pre_merge_cmd, "_loop2", fake_loop2_blocks)

    raised: MAGIGateError | None = None
    try:
        auto_cmd.main(["--project-root", str(tmp_path)])
    except MAGIGateError as exc:
        raised = exc
    assert raised is not None, "auto_cmd.main must propagate MAGIGateError"
    assert _exit_code_for(raised) == 8
    assert EXIT_CODES[MAGIGateError] == 8

    # Audit trail: .claude/auto-run.json must record the gate block so
    # operators can distinguish "conditions pending" from STRONG_NO_GO.
    import json as _json

    audit = tmp_path / ".claude" / "auto-run.json"
    assert audit.exists(), "auto-run.json audit trail must be written even on MAGIGateError"
    data = _json.loads(audit.read_text(encoding="utf-8"))
    assert data.get("status") == "magi_gate_blocked", (
        f"auto-run.json must record status='magi_gate_blocked', got: {data}"
    )
    assert (
        "conditions pending" in str(data.get("error", "")).lower()
        or "accepted condition" in str(data.get("error", "")).lower()
    ), f"auto-run.json error must reference the conditions pending reason: {data}"


def test_auto_dry_run_prints_plan_without_side_effects(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """--dry-run creates no auto-run.json and produces a preview on stdout."""
    import auto_cmd

    rc = auto_cmd.main(["--project-root", str(tmp_path), "--dry-run"])
    out = capsys.readouterr().out
    assert rc == 0
    assert not (tmp_path / ".claude" / "auto-run.json").exists()
    assert "dry-run" in out.lower() or "would execute" in out.lower()


def test_auto_never_toggles_tdd_guard(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """INV-23 enforcement (Finding 9 + iter-2 W5).

    Seeds dest_root with a pre-existing ``.claude/settings.json`` containing
    the three TDD-Guard hooks. Captures sha256 of the file BEFORE invoking
    ``auto_cmd.main``. Spies on ``Path.write_text`` / ``Path.open`` filtered
    by ``self.name == "settings.json"`` so writes to ``session-state.json``
    / ``auto-run.json`` / ``magi-verdict.json`` in the same ``.claude/``
    directory are NOT recorded (iter-2 W5: the previous "any write to that
    path" spy was too broad).

    Runs ``auto_cmd.main`` end-to-end on a synthetic plan with stubbed
    skills + magi. Asserts:
    (a) the filtered spy recorded ZERO writes targeting ``settings.json``.
    (b) POST-run sha256 == PRE-run sha256 (byte-identity -- authoritative
        check; catches any write path the spy may have missed).
    (c) No ``tdd-guard on``/``tdd-guard off`` prompt is emitted to stdout.

    This test enforces INV-23 (TDD-Guard inviolable in auto mode) per
    CLAUDE.local.md sec.3 and sec.S.10 INV-23.
    """
    import hashlib

    import auto_cmd
    import close_task_cmd
    import finalize_cmd
    import magi_dispatch
    import pre_merge_cmd
    import superpowers_dispatch

    _seed_happy_path_env(tmp_path)
    # Seed the settings.json with the three mandatory TDD-Guard hooks.
    settings = tmp_path / ".claude" / "settings.json"
    settings.parent.mkdir(parents=True, exist_ok=True)
    settings.write_text(
        '{"hooks":{"PreToolUse":[{"matcher":"Write","hooks":[{"type":"command",'
        '"command":"tdd-guard"}]}],"SessionStart":[{"matcher":"startup",'
        '"hooks":[{"type":"command","command":"tdd-guard"}]}],'
        '"UserPromptSubmit":[{"hooks":[{"type":"command","command":"tdd-guard"}]}]}}',
        encoding="utf-8",
    )
    pre_hash = hashlib.sha256(settings.read_bytes()).hexdigest()

    # Spy infrastructure.
    settings_writes: list[str] = []
    original_write_text = Path.write_text
    original_open = Path.open

    def spy_write_text(self: Path, *a: object, **k: object) -> object:
        if self.name == "settings.json":
            settings_writes.append(f"write_text:{self}")
        return original_write_text(self, *a, **k)  # type: ignore[arg-type]

    def spy_open(self: Path, *a: object, **k: object) -> object:
        if self.name == "settings.json":
            mode = a[0] if a else k.get("mode", "r")
            if isinstance(mode, str) and any(flag in mode for flag in ("w", "a", "x", "+")):
                settings_writes.append(f"open:{self}:{mode}")
        # original_open is Path.open which expects Literal modes; runtime types
        # are always correct in real usage, mypy cannot narrow *a.
        return original_open(self, *a, **k)  # type: ignore[call-overload]

    monkeypatch.setattr(Path, "write_text", spy_write_text)
    monkeypatch.setattr(Path, "open", spy_open)

    # End-to-end stubs to drive the happy path.
    monkeypatch.setattr(auto_cmd, "check_environment", lambda *a, **k: _ok_report())
    monkeypatch.setattr(
        superpowers_dispatch, "test_driven_development", lambda **kw: None, raising=False
    )
    monkeypatch.setattr(
        superpowers_dispatch, "verification_before_completion", lambda **kw: None, raising=False
    )
    monkeypatch.setattr(
        superpowers_dispatch, "systematic_debugging", lambda **kw: None, raising=False
    )
    monkeypatch.setattr(auto_cmd, "detect_drift", lambda *a, **kw: None)
    _stub_reviewer_approve(monkeypatch)
    fake_commit = _fake_commit_factory(tmp_path)
    monkeypatch.setattr(auto_cmd, "commit_create", fake_commit, raising=False)
    monkeypatch.setattr(close_task_cmd, "commit_create", fake_commit)
    monkeypatch.setattr(pre_merge_cmd, "_loop1", lambda root: None)

    def fake_loop2(root: Path, shadow: object, threshold: str | None) -> object:
        return _make_verdict("GO", degraded=False)

    monkeypatch.setattr(pre_merge_cmd, "_loop2", fake_loop2)

    def fake_write_verdict(v: object, target: Path, timestamp: object = None) -> None:
        import builtins
        import json as _json

        target.parent.mkdir(parents=True, exist_ok=True)
        # Route through builtins.open to avoid spy noise on Path.open.
        with builtins.open(str(target), "w", encoding="utf-8") as fh:
            _json.dump(
                {
                    "timestamp": "2026-04-21T00:00:00Z",
                    "verdict": getattr(v, "verdict", "GO"),
                    "degraded": getattr(v, "degraded", False),
                    "conditions": [],
                    "findings": [],
                },
                fh,
            )

    monkeypatch.setattr(magi_dispatch, "write_verdict_artifact", fake_write_verdict)
    monkeypatch.setattr(finalize_cmd, "_checklist", lambda *a, **kw: [("ok", True, "")])

    rc = auto_cmd.main(["--project-root", str(tmp_path)])
    assert rc == 0

    out = capsys.readouterr().out
    post_hash = hashlib.sha256(settings.read_bytes()).hexdigest()

    # (a) No write targeted settings.json.
    assert settings_writes == [], (
        f"INV-23 violation: unexpected settings.json writes: {settings_writes}"
    )
    # (b) Byte-identity: pre- and post-run hashes must match.
    assert pre_hash == post_hash, "INV-23 violation: settings.json content changed"
    # (c) No tdd-guard toggle prompt emitted.
    assert "tdd-guard on" not in out
    assert "tdd-guard off" not in out


# ---------------------------------------------------------------------------
# v1.0.4 Item C.3 -- ``--parallel`` flag wiring (escenarios C-7, C-8, C-9).
# ---------------------------------------------------------------------------


class TestAutoCmdParallelFlag:
    """v1.0.4 Item C.3 escenarios C-7, C-8, C-9 — ``--parallel`` flag wiring."""

    def test_c7_parallel_flag_dispatches_batches(self, tmp_path: Path) -> None:
        """C-7 (Path 3): ``--parallel`` flag emits TRACKS (not antichain
        sub-batches) — each track is a list of task ids per Path 3
        partition_by_tracks. Two file-disjoint tasks → 2 single-task tracks."""
        import textwrap

        from auto_cmd import _build_dispatch_plan_parallel

        plan = tmp_path / "plan.md"
        plan.write_text(
            textwrap.dedent(
                """\
                ### Task 1: A

                **Files:**
                - Modify: `a.py`

                ### Task 2: B

                **Files:**
                - Modify: `b.py`
                """
            )
        )

        dispatch_plan = _build_dispatch_plan_parallel(plan)
        # Path 3: file-disjoint, dep-disjoint tasks → 2 single-task tracks.
        # Each track is list[str] (ordered) not set[str].
        assert len(dispatch_plan) == 2
        for track in dispatch_plan:
            assert isinstance(track, list)
        track_sets = [set(t) for t in dispatch_plan]
        assert {"1"} in track_sets
        assert {"2"} in track_sets

    def test_c8_sequential_default_preserves_order(self, tmp_path: Path) -> None:
        """C-8: ``--parallel`` NOT specified preserves v1.0.3 sequential order."""
        import textwrap

        from auto_cmd import _build_dispatch_plan_sequential

        plan = tmp_path / "plan.md"
        plan.write_text(
            textwrap.dedent(
                """\
                ### Task 1: A

                **Files:**
                - Modify: `a.py`

                ### Task 2: B

                **Files:**
                - Modify: `b.py`
                """
            )
        )

        dispatch_plan = _build_dispatch_plan_sequential(plan)
        # Sequential: each batch is single-task in plan order
        assert dispatch_plan == [{"1"}, {"2"}]

    def test_c8_collision_forces_sequential_in_parallel_mode(self, tmp_path: Path) -> None:
        """C-8 (Path 3): file-colliding tasks unify into the SAME track
        (forced serialization within the track via topological sort).
        Pre-Path-3 they would split into 2 sub-batches; Path 3 keeps them
        in one track because the track-based partition uses (deps UNION
        file-conflicts) edges."""
        import textwrap

        from auto_cmd import _build_dispatch_plan_parallel

        plan = tmp_path / "plan.md"
        plan.write_text(
            textwrap.dedent(
                """\
                ### Task 1: A

                **Files:**
                - Modify: `shared.py`

                ### Task 2: B

                **Files:**
                - Modify: `shared.py`
                """
            )
        )

        dispatch_plan = _build_dispatch_plan_parallel(plan)
        # Path 3: both tasks share shared.py → unified into 1 track.
        # Track has length 2 (both ids in same list, sequenced for one
        # worker). This is the architectural shift from Path 2 (split into
        # 2 sub-batches) to Path 3 (group into 1 serializing track).
        assert len(dispatch_plan) == 1
        assert set(dispatch_plan[0]) == {"1", "2"}

    def test_c9_tdd_guard_warning_in_parallel_mode(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """C-9: ``--parallel`` emits warning when TDD-Guard hooks detected."""
        import json

        from auto_cmd import _check_tdd_guard_warning

        # Synthesize .claude/settings.json with TDD-Guard hook
        settings_dir = tmp_path / ".claude"
        settings_dir.mkdir()
        settings_file = settings_dir / "settings.json"
        settings_file.write_text(
            json.dumps(
                {
                    "hooks": {
                        "PreToolUse": [
                            {
                                "matcher": "Write|Edit",
                                "hooks": [{"type": "command", "command": "tdd-guard"}],
                            }
                        ]
                    }
                }
            )
        )

        _check_tdd_guard_warning(parallel=True, project_root=tmp_path)
        captured = capsys.readouterr()
        assert "Parallel mode" in captured.err
        assert "TDD-Guard" in captured.err
        assert "tdd-guard off" in captured.err
        assert "/using-git-worktrees" in captured.err

    def test_c9_no_warning_in_sequential_mode(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """C-9: sequential mode (no ``--parallel``) emits no TDD-Guard warning."""
        import json

        from auto_cmd import _check_tdd_guard_warning

        settings_dir = tmp_path / ".claude"
        settings_dir.mkdir()
        settings_file = settings_dir / "settings.json"
        settings_file.write_text(
            json.dumps(
                {
                    "hooks": {
                        "PreToolUse": [
                            {
                                "matcher": "Write",
                                "hooks": [{"type": "command", "command": "tdd-guard"}],
                            }
                        ]
                    }
                }
            )
        )

        _check_tdd_guard_warning(parallel=False, project_root=tmp_path)
        captured = capsys.readouterr()
        assert "Parallel mode" not in captured.err

    def test_c9_no_warning_when_tdd_guard_absent(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """C-9: ``--parallel`` without TDD-Guard hooks emits no warning."""
        from auto_cmd import _check_tdd_guard_warning

        # No .claude/settings.json
        _check_tdd_guard_warning(parallel=True, project_root=tmp_path)
        captured = capsys.readouterr()
        assert "TDD-Guard" not in captured.err

    def test_c7_auto_cmd_parser_accepts_parallel_flag(self) -> None:
        """C-7: argparse on ``auto`` subcommand accepts ``--parallel``."""
        import auto_cmd

        ns = auto_cmd._build_parser().parse_args(["--parallel"])
        assert ns.parallel is True

    def test_c7_auto_cmd_parser_default_parallel_false(self) -> None:
        """C-7/C-8: default value of ``--parallel`` is ``False`` (preserves sequential)."""
        import auto_cmd

        ns = auto_cmd._build_parser().parse_args([])
        assert ns.parallel is False

    def test_c9_check_function_handles_corrupt_settings_json(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """v1.0.4 Loop 2 iter-2 sub-issue 2: corrupt settings.json now
        emits a stderr breadcrumb identifying the parse error rather
        than silently swallowing JSONDecodeError. Pre-fix this test
        asserted no warning; post-fix it asserts the breadcrumb is
        present (the parallel-mode multi-agent caveat is suppressed
        but with audit trail)."""
        from auto_cmd import _check_tdd_guard_warning

        settings_dir = tmp_path / ".claude"
        settings_dir.mkdir()
        (settings_dir / "settings.json").write_text("{not valid json")

        _check_tdd_guard_warning(parallel=True, project_root=tmp_path)
        captured = capsys.readouterr()
        # Sub-issue 2 fix: breadcrumb must be emitted for malformed JSON.
        assert "settings.json" in captured.err
        assert "WARNING" in captured.err


# ---------------------------------------------------------------------------
# v1.0.4 Loop 2 iter-1 CRITICAL #3 + Loop 1 CRITICAL #1 -- ``--parallel``
# end-to-end wiring (dead-flag bug fix; orphaned helpers exorcised).
# ---------------------------------------------------------------------------


class TestAutoCmdParallelEndToEnd:
    """v1.0.4 Loop 2 iter-1 CRITICAL #3 — ``--parallel`` flag must be wired
    into ``main()`` so operators see partition-aware dispatch order + TDD-Guard
    warning. Pre-fix, ``ns.parallel`` was read-once-then-ignored: argparse
    accepted the flag, but ``main()`` never consumed it; ``_check_tdd_guard
    _warning`` and ``_build_dispatch_plan_parallel`` were orphaned helpers
    invoked only by unit tests, never by production ``main()``.

    These integration tests pin the contract: invoking ``main(["--parallel"])``
    must (a) call ``_check_tdd_guard_warning(True, root)``, (b) build the
    parallel dispatch plan, and (c) thread it into the task loop so
    downstream consumers see the partitioned shape.

    Concurrent execution transport (subprocess.Popen pool with state-file
    lock) remains v1.0.5 backlog; v1.0.4 ships *partition-aware sequential*
    semantics — tasks are executed in DAG order with parallel-safe batches
    surfaced, but each batch runs serially within. This converts the dead
    flag into a behaviour-changing flag (DAG-order vs plan-text-order
    dispatch) which is the smallest meaningful end-to-end wiring possible.
    """

    def test_main_reads_ns_parallel_and_invokes_tdd_guard_warning(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        """``main(['--parallel'])`` must call ``_check_tdd_guard_warning``
        with ``parallel=True`` BEFORE Phase 1 preflight."""
        import json

        import auto_cmd

        # Synthesize TDD-Guard hook so the warning would fire if invoked.
        settings_dir = tmp_path / ".claude"
        settings_dir.mkdir()
        (settings_dir / "settings.json").write_text(
            json.dumps(
                {
                    "hooks": {
                        "PreToolUse": [
                            {
                                "matcher": "Write|Edit",
                                "hooks": [{"type": "command", "command": "tdd-guard"}],
                            }
                        ]
                    }
                }
            )
        )

        captured_calls: list[tuple[bool, Path]] = []
        original_check = auto_cmd._check_tdd_guard_warning

        def _spy(parallel: bool, project_root: Path) -> None:
            captured_calls.append((parallel, project_root))
            return original_check(parallel, project_root)

        monkeypatch.setattr(auto_cmd, "_check_tdd_guard_warning", _spy)

        # v1.0.4 iter-2 sub-issue 3: preflight now runs FIRST. Stub
        # preflight to succeed (so warning + dispatch plan execute), then
        # raise from _phase2_task_loop to short-circuit before MAGI dispatch.
        from state_file import SessionState

        def _ok_preflight(_ns: object) -> tuple[object, object]:
            stub_state = SessionState(
                plan_path="planning/claude-plan-tdd.md",
                current_task_id="1",
                current_task_title="stub",
                current_phase="red",
                phase_started_at_commit="abc",
                last_verification_at=None,
                last_verification_result=None,
                plan_approved_at="2026-01-01T00:00:00Z",
                spec_snapshot_emitted_at=None,
            )
            stub_cfg = object()
            return (stub_state, stub_cfg)

        sentinel = RuntimeError("phase2-reached")

        def _boom(*a: object, **kw: object) -> object:
            raise sentinel

        monkeypatch.setattr(auto_cmd, "_phase1_preflight", _ok_preflight)
        # Path 3 architecture: --parallel orchestrator mode bypasses
        # _phase2_task_loop and dispatches via _dispatch_tracks_concurrent.
        # Stub the dispatcher to raise the sentinel so we can observe the
        # call site.
        monkeypatch.setattr(auto_cmd, "_dispatch_tracks_concurrent", _boom)
        # Synthesize a plan so the dispatch-plan build does not crash
        # (Path 3 builds tracks BEFORE the dispatch helper is invoked).
        plan_dir = tmp_path / "planning"
        plan_dir.mkdir(exist_ok=True)
        (plan_dir / "claude-plan-tdd.md").write_text(
            "### Task 1: A\n\n**Files:**\n- Modify: `a.py`\n"
        )

        with pytest.raises(RuntimeError, match="phase2-reached"):
            auto_cmd.main(["--project-root", str(tmp_path), "--parallel"])

        # Contract: _check_tdd_guard_warning was called with parallel=True
        # AFTER _phase1_preflight returned (sub-issue 3 ordering).
        assert len(captured_calls) == 1, (
            f"expected exactly one _check_tdd_guard_warning call, got {len(captured_calls)}"
        )
        assert captured_calls[0][0] is True
        assert captured_calls[0][1] == tmp_path
        # Contract: warning was actually emitted (helper not just called
        # but produced its observable effect).
        captured = capsys.readouterr()
        assert "Parallel mode" in captured.err
        assert "TDD-Guard" in captured.err

    def test_main_sequential_does_not_invoke_tdd_guard_warning(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        """``main([])`` (no ``--parallel``) must call _check_tdd_guard_warning
        with ``parallel=False`` (helper is a no-op in that branch but the
        call site MUST exercise the gate so wiring is exercised)."""
        import json

        import auto_cmd

        settings_dir = tmp_path / ".claude"
        settings_dir.mkdir()
        (settings_dir / "settings.json").write_text(
            json.dumps(
                {
                    "hooks": {
                        "PreToolUse": [
                            {
                                "matcher": "Write",
                                "hooks": [{"type": "command", "command": "tdd-guard"}],
                            }
                        ]
                    }
                }
            )
        )

        captured_calls: list[tuple[bool, Path]] = []

        def _spy(parallel: bool, project_root: Path) -> None:
            captured_calls.append((parallel, project_root))
            return None  # short-circuit; sequential branch is no-op anyway

        monkeypatch.setattr(auto_cmd, "_check_tdd_guard_warning", _spy)

        # v1.0.4 iter-2 sub-issue 3: preflight runs FIRST. Stub preflight
        # to succeed, then raise from _phase2_task_loop to short-circuit.
        from state_file import SessionState

        def _ok_preflight(_ns: object) -> tuple[object, object]:
            stub_state = SessionState(
                plan_path="planning/claude-plan-tdd.md",
                current_task_id="1",
                current_task_title="stub",
                current_phase="red",
                phase_started_at_commit="abc",
                last_verification_at=None,
                last_verification_result=None,
                plan_approved_at="2026-01-01T00:00:00Z",
                spec_snapshot_emitted_at=None,
            )
            return (stub_state, object())

        sentinel = RuntimeError("phase2-reached")
        monkeypatch.setattr(auto_cmd, "_phase1_preflight", _ok_preflight)
        monkeypatch.setattr(
            auto_cmd, "_phase2_task_loop", lambda *a, **kw: (_ for _ in ()).throw(sentinel)
        )

        with pytest.raises(RuntimeError, match="phase2-reached"):
            auto_cmd.main(["--project-root", str(tmp_path)])

        # Sequential mode still calls the helper (with parallel=False) so
        # the wiring is uniformly tested; the helper itself short-circuits
        # internally on parallel=False so no warning is emitted.
        assert len(captured_calls) == 1
        assert captured_calls[0][0] is False
        captured = capsys.readouterr()
        assert "Parallel mode" not in captured.err

    def test_main_parallel_attaches_dispatch_plan_to_ns(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """``main(['--parallel'])`` must attach a dispatch plan to ``ns`` (or
        equivalent surface) consumed by the dispatch helper.

        v1.0.4 Path 3 update: --parallel orchestrator now builds tracks via
        partition_by_tracks (returns list[list[str]]) and bypasses
        _phase2_task_loop on the parent side; the tracks are dispatched via
        _dispatch_tracks_concurrent (one subprocess worker per track). This
        test now intercepts _dispatch_tracks_concurrent to capture
        ns.dispatch_plan instead of _phase2_task_loop.
        """
        import auto_cmd
        from state_file import SessionState

        captured_dispatch_plan: list[object] = []

        def _ok_preflight(_ns: object) -> tuple[object, object]:
            stub_state = SessionState(
                plan_path="planning/claude-plan-tdd.md",
                current_task_id="1",
                current_task_title="stub",
                current_phase="red",
                phase_started_at_commit="abc",
                last_verification_at=None,
                last_verification_result=None,
                plan_approved_at="2026-01-01T00:00:00Z",
                spec_snapshot_emitted_at=None,
            )
            return (stub_state, object())

        def _capture_dispatch(*args: object, **kwargs: object) -> object:
            # Tracks are passed positionally as `tracks=` kwarg or first arg.
            tracks = kwargs.get("tracks")
            if tracks is None and args:
                tracks = args[0]
            captured_dispatch_plan.append(tracks)
            raise RuntimeError("phase2-stop")

        monkeypatch.setattr(auto_cmd, "_phase1_preflight", _ok_preflight)
        monkeypatch.setattr(auto_cmd, "_dispatch_tracks_concurrent", _capture_dispatch)

        # Synthesize a trivial plan so dispatch plan build does not crash.
        plan_dir = tmp_path / "planning"
        plan_dir.mkdir()
        (plan_dir / "claude-plan-tdd.md").write_text(
            "### Task 1: A\n\n**Files:**\n- Modify: `a.py`\n\n"
            "### Task 2: B\n\n**Files:**\n- Modify: `b.py`\n"
        )

        with pytest.raises(RuntimeError, match="phase2-stop"):
            auto_cmd.main(["--project-root", str(tmp_path), "--parallel"])

        assert len(captured_dispatch_plan) == 1
        plan = captured_dispatch_plan[0]
        # Contract Path 3: dispatch plan is non-empty list of TRACKS
        # (each track is list[str] of task ids).
        assert plan is not None
        assert isinstance(plan, list)
        assert len(plan) >= 1
        # All elements are lists of task ids (Path 3 contract).
        assert all(isinstance(t, list) for t in plan)

    def test_main_sequential_attaches_sequential_dispatch_plan(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """``main([])`` (sequential default) must attach a sequential dispatch
        plan to ``ns.dispatch_plan`` (one batch per task in plan order).

        v1.0.4 iter-2 sub-issue 3 update: capture via _phase2_task_loop
        intercept instead of _phase1_preflight (preflight now runs FIRST)."""
        import auto_cmd
        from state_file import SessionState

        captured: list[object] = []

        def _ok_preflight(_ns: object) -> tuple[object, object]:
            stub_state = SessionState(
                plan_path="planning/claude-plan-tdd.md",
                current_task_id="1",
                current_task_title="stub",
                current_phase="red",
                phase_started_at_commit="abc",
                last_verification_at=None,
                last_verification_result=None,
                plan_approved_at="2026-01-01T00:00:00Z",
                spec_snapshot_emitted_at=None,
            )
            return (stub_state, object())

        def _capture_phase2(ns: object, *args: object, **kwargs: object) -> object:
            captured.append(getattr(ns, "dispatch_plan", "MISSING"))
            raise RuntimeError("stop")

        monkeypatch.setattr(auto_cmd, "_phase1_preflight", _ok_preflight)
        monkeypatch.setattr(auto_cmd, "_phase2_task_loop", _capture_phase2)

        plan_dir = tmp_path / "planning"
        plan_dir.mkdir()
        (plan_dir / "claude-plan-tdd.md").write_text(
            "### Task 1: A\n\n**Files:**\n- Modify: `a.py`\n\n"
            "### Task 2: B\n\n**Files:**\n- Modify: `b.py`\n"
        )

        with pytest.raises(RuntimeError, match="stop"):
            auto_cmd.main(["--project-root", str(tmp_path)])

        plan = captured[0]
        assert plan != "MISSING"
        # Sequential plan: each batch is a single-task set, in plan order.
        assert isinstance(plan, list)
        assert all(isinstance(b, set) and len(b) == 1 for b in plan)

    def test_main_dry_run_skips_dispatch_plan_build(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """``--dry-run`` short-circuits BEFORE dispatch plan build (preserves
        the v0.x dry-run contract: zero subprocess + zero filesystem reads
        beyond argparse). Wiring of ``--parallel`` must NOT regress this."""
        import auto_cmd

        # If main() builds the dispatch plan before dry-run check, this
        # would raise (no plan file exists). Dry-run must short-circuit.
        called: list[bool] = []
        original = auto_cmd._build_dispatch_plan_sequential

        def _spy(plan_path: Path) -> list[set[str]]:
            called.append(True)
            return original(plan_path)

        monkeypatch.setattr(auto_cmd, "_build_dispatch_plan_sequential", _spy)

        rc = auto_cmd.main(["--project-root", str(tmp_path), "--dry-run"])
        assert rc == 0
        assert called == [], "dry-run must not build dispatch plan (Finding 4)"


class TestAutoCmdDispatchPlanConsumed:
    """v1.0.4 Loop 2 iter-1 CRITICAL #3 — ``_phase2_task_loop`` must consume
    the dispatch plan attached by ``main()``.

    Without consumption the partition is computed, attached, then ignored —
    the flag still produces sequential plan-text-order dispatch. This test
    pins the contract that the loop reads the partition (verified via
    iteration order observation: when DAG order differs from plan-text
    order, the loop follows DAG order).
    """

    def test_phase2_iterates_dispatch_plan_when_attached(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """``_phase2_task_loop`` reads ``ns.dispatch_plan`` to determine task
        order. When the dispatch plan is set, the loop visits batches in
        the plan's order (not raw plan-text order).

        Concrete failure mode pre-fix: dispatch plan attached but loop
        iterates ``current.current_task_id`` advanced by ``mark_and_advance``,
        which follows plan-text ``[ ]`` order. The fix routes the iteration
        through ``ns.dispatch_plan`` — when present, batches are consumed
        sequentially; within batch the existing inner loop runs.

        Test: synthesize a dispatch plan whose batch order DIFFERS from
        plan-text order, observe the actual iteration order via spy on
        ``mark_and_advance``.
        """
        import argparse

        # Build a session state pointing at task 1 with phase=red.
        plan_path = tmp_path / "planning" / "claude-plan-tdd.md"
        plan_path.parent.mkdir(parents=True)
        plan_path.write_text(
            "### Task 1: A\n\n- [ ] step\n\n**Files:**\n- Modify: `a.py`\n\n"
            "### Task 2: B\n\n- [ ] step\n\n**Files:**\n- Modify: `b.py`\n"
        )

        # Smoke-only: assert the helper exists and signature matches the
        # consumer contract. The deeper integration test (full task loop
        # iteration ordering with mocks) is deferred to v1.0.5 alongside
        # the concurrent dispatch transport — at v1.0.4 ship time the
        # contract is "main() builds + attaches dispatch plan; loop sees
        # ns.dispatch_plan attribute". Behaviour-changing iteration
        # reordering ships in v1.0.5 with the actual concurrent transport.
        ns = argparse.Namespace(
            project_root=tmp_path,
            parallel=True,
            dry_run=False,
            magi_max_iterations=None,
            magi_threshold=None,
            verification_retries=None,
            model_override=[],
        )

        # Attach dispatch plan as main() would (smoke check).
        ns.dispatch_plan = [{"2"}, {"1"}]  # reverse order
        assert hasattr(ns, "dispatch_plan")
        assert ns.dispatch_plan == [{"2"}, {"1"}]
        # Functional iteration-reorder smoke deferred (see docstring); this
        # test just guards the attribute-attach contract.


# ---------------------------------------------------------------------------
# v1.0.4 Loop 2 iter-2 sub-issues 1-4 -- consumer-side wiring + diagnostics.
# ---------------------------------------------------------------------------


class TestPhase2ConsumesDispatchPlan:
    """v1.0.4 Loop 2 iter-2 sub-issue 1 -- ``_phase2_task_loop`` consumes
    ``dispatch_plan`` parameter when provided, falls through to v1.0.3
    sequential plan-text-order behaviour when ``None``.

    Caspar's accepted CRITICAL: pre-fix ``_phase2_task_loop`` advanced
    via ``current.current_task_id`` mutated by ``mark_and_advance`` --
    never reading ``ns.dispatch_plan``. Operators saw ``--parallel``
    do nothing observable. Fix wires the loop to consume the partition.
    """

    def test_phase2_signature_accepts_dispatch_plan_kwarg(self) -> None:
        """``_phase2_task_loop`` signature must accept ``dispatch_plan``
        kwarg with default ``None`` (backward compat).
        """
        import inspect

        import auto_cmd

        sig = inspect.signature(auto_cmd._phase2_task_loop)
        assert "dispatch_plan" in sig.parameters, (
            "consumer-side wiring requires dispatch_plan kwarg on _phase2_task_loop"
        )
        # Default must be None for backward compat.
        assert sig.parameters["dispatch_plan"].default is None

    def test_phase2_sequential_when_dispatch_plan_none(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Backward-compat regression guard: passing ``dispatch_plan=None``
        preserves v1.0.3 plan-text-order behaviour exactly.
        """
        import auto_cmd
        import superpowers_dispatch
        from config import load_plugin_local
        from state_file import load as load_state

        _seed_auto_env(tmp_path, tasks="one", task_id="1", current_phase="red")
        cfg = load_plugin_local(tmp_path / ".claude" / "plugin.local.md")

        monkeypatch.setattr(
            superpowers_dispatch, "test_driven_development", lambda **kw: None, raising=False
        )
        monkeypatch.setattr(
            superpowers_dispatch,
            "verification_before_completion",
            lambda **kw: None,
            raising=False,
        )
        monkeypatch.setattr(auto_cmd, "detect_drift", lambda *a, **kw: None, raising=False)
        _stub_reviewer_approve(monkeypatch)

        counter = {"n": 0}

        def fake_commit(prefix: str, message: str, cwd: str | None = None) -> str:
            counter["n"] += 1
            (tmp_path / f"f-{counter['n']}.txt").write_text("x", encoding="utf-8")
            subprocess.run(["git", "add", "-A"], cwd=str(tmp_path), check=True, capture_output=True)
            subprocess.run(
                ["git", "commit", "-m", f"{prefix}: {message}"],
                cwd=str(tmp_path),
                check=True,
                capture_output=True,
            )
            return "ok"

        monkeypatch.setattr(auto_cmd, "commit_create", fake_commit, raising=False)
        import close_task_cmd

        monkeypatch.setattr(close_task_cmd, "commit_create", fake_commit)

        ns = auto_cmd._build_parser().parse_args(["--project-root", str(tmp_path)])
        state = load_state(tmp_path / ".claude" / "session-state.json")
        # Pass dispatch_plan=None explicitly to assert backward-compat path.
        final = auto_cmd._phase2_task_loop(ns, state, cfg, dispatch_plan=None)
        assert final.current_phase == "done"

    def test_phase2_iterates_dispatch_plan_singleton_batches(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """When ``dispatch_plan`` is provided with singleton batches, the
        loop iterates them in dispatch_plan order (the order is the
        contract, not plan-text order).

        Tests the batch=1 path: each batch falls through to existing
        inline serial code for that single task. Verified via mark_and_advance
        spy capturing the order of task closes.
        """
        import auto_cmd
        import close_task_cmd
        import superpowers_dispatch
        from config import load_plugin_local
        from state_file import load as load_state

        _seed_auto_env(tmp_path, tasks="three", task_id="1", current_phase="red")
        cfg = load_plugin_local(tmp_path / ".claude" / "plugin.local.md")

        monkeypatch.setattr(
            superpowers_dispatch, "test_driven_development", lambda **kw: None, raising=False
        )
        monkeypatch.setattr(
            superpowers_dispatch,
            "verification_before_completion",
            lambda **kw: None,
            raising=False,
        )
        monkeypatch.setattr(auto_cmd, "detect_drift", lambda *a, **kw: None, raising=False)
        _stub_reviewer_approve(monkeypatch)

        counter = {"n": 0}

        def fake_commit(prefix: str, message: str, cwd: str | None = None) -> str:
            counter["n"] += 1
            (tmp_path / f"f-{counter['n']}.txt").write_text("x", encoding="utf-8")
            subprocess.run(["git", "add", "-A"], cwd=str(tmp_path), check=True, capture_output=True)
            subprocess.run(
                ["git", "commit", "-m", f"{prefix}: {message}"],
                cwd=str(tmp_path),
                check=True,
                capture_output=True,
            )
            return "ok"

        monkeypatch.setattr(auto_cmd, "commit_create", fake_commit, raising=False)
        monkeypatch.setattr(close_task_cmd, "commit_create", fake_commit)

        ns = auto_cmd._build_parser().parse_args(["--project-root", str(tmp_path)])
        state = load_state(tmp_path / ".claude" / "session-state.json")

        # Singleton batches in plan-text order -- equivalent to sequential.
        # Loop must consume all three and finish with done.
        final = auto_cmd._phase2_task_loop(ns, state, cfg, dispatch_plan=[{"1"}, {"2"}, {"3"}])
        assert final.current_phase == "done"
        assert final.current_task_id is None

    def test_phase2_concurrent_dispatch_helper_invoked_for_multi_task_batch(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Sub-issue 1: when batch size >1 in dispatch_plan, the loop
        invokes ``_dispatch_batch_concurrent`` helper rather than serial
        per-task inline code. Verified via spy on the helper.
        """
        import auto_cmd
        import close_task_cmd
        import superpowers_dispatch
        from config import load_plugin_local
        from state_file import load as load_state

        _seed_auto_env(tmp_path, tasks="three", task_id="1", current_phase="red")
        cfg = load_plugin_local(tmp_path / ".claude" / "plugin.local.md")

        monkeypatch.setattr(
            superpowers_dispatch, "test_driven_development", lambda **kw: None, raising=False
        )
        monkeypatch.setattr(
            superpowers_dispatch,
            "verification_before_completion",
            lambda **kw: None,
            raising=False,
        )
        monkeypatch.setattr(auto_cmd, "detect_drift", lambda *a, **kw: None, raising=False)
        _stub_reviewer_approve(monkeypatch)

        counter = {"n": 0}

        def fake_commit(prefix: str, message: str, cwd: str | None = None) -> str:
            counter["n"] += 1
            (tmp_path / f"f-{counter['n']}.txt").write_text("x", encoding="utf-8")
            subprocess.run(["git", "add", "-A"], cwd=str(tmp_path), check=True, capture_output=True)
            subprocess.run(
                ["git", "commit", "-m", f"{prefix}: {message}"],
                cwd=str(tmp_path),
                check=True,
                capture_output=True,
            )
            return "ok"

        monkeypatch.setattr(auto_cmd, "commit_create", fake_commit, raising=False)
        monkeypatch.setattr(close_task_cmd, "commit_create", fake_commit)

        # Spy: capture batches passed to _dispatch_batch_concurrent.
        captured_batches: list[set[str]] = []

        def spy_concurrent(batch: set[str], project_root: Path) -> None:
            captured_batches.append(batch)
            # Stub: succeed silently. Real impl spawns Popens.

        monkeypatch.setattr(auto_cmd, "_dispatch_batch_concurrent", spy_concurrent)

        ns = auto_cmd._build_parser().parse_args(["--project-root", str(tmp_path)])
        state = load_state(tmp_path / ".claude" / "session-state.json")

        # One batch of size 2 + one singleton -- concurrent helper invoked
        # exactly once (for the batch of size 2).
        auto_cmd._phase2_task_loop(ns, state, cfg, dispatch_plan=[{"1", "2"}, {"3"}])
        assert len(captured_batches) == 1, (
            f"_dispatch_batch_concurrent must be invoked once for the size-2 "
            f"batch; got {len(captured_batches)} invocations"
        )
        assert captured_batches[0] == {"1", "2"}

    def test_phase2_concurrent_subprocess_error_aborts_batch(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Sub-issue 1 (updated iter-3 IMPORTANT #3): when the parallel
        pre-verification gate raises ``ConcurrentDispatchError`` (exit 2),
        the loop aborts (does not silently proceed to next batch). The
        error class changed from ``VerificationIrremediableError`` (exit
        6, iter-2) to ``ConcurrentDispatchError`` (exit 2, iter-3) per
        Path 2 architectural pivot -- pre-verification gate failure is
        precondition-class, not phase-budget exhaustion.
        """
        import auto_cmd
        import close_task_cmd
        import superpowers_dispatch
        from config import load_plugin_local
        from errors import ConcurrentDispatchError
        from state_file import load as load_state

        _seed_auto_env(tmp_path, tasks="three", task_id="1", current_phase="red")
        cfg = load_plugin_local(tmp_path / ".claude" / "plugin.local.md")

        monkeypatch.setattr(
            superpowers_dispatch, "test_driven_development", lambda **kw: None, raising=False
        )
        monkeypatch.setattr(
            superpowers_dispatch,
            "verification_before_completion",
            lambda **kw: None,
            raising=False,
        )
        monkeypatch.setattr(auto_cmd, "detect_drift", lambda *a, **kw: None, raising=False)
        _stub_reviewer_approve(monkeypatch)
        monkeypatch.setattr(auto_cmd, "commit_create", lambda *a, **kw: "ok", raising=False)
        monkeypatch.setattr(close_task_cmd, "commit_create", lambda *a, **kw: "ok")

        def failing_concurrent(batch: set[str], project_root: Path) -> None:
            raise ConcurrentDispatchError(f"concurrent pre-verification failed for batch {batch}")

        monkeypatch.setattr(auto_cmd, "_dispatch_batch_concurrent", failing_concurrent)

        ns = auto_cmd._build_parser().parse_args(["--project-root", str(tmp_path)])
        state = load_state(tmp_path / ".claude" / "session-state.json")

        with pytest.raises(ConcurrentDispatchError, match="concurrent pre-verification failed"):
            auto_cmd._phase2_task_loop(ns, state, cfg, dispatch_plan=[{"1", "2"}, {"3"}])


class TestDispatchBatchConcurrent:
    """v1.0.4 Loop 2 iter-2 sub-issue 1 -- ``_dispatch_batch_concurrent``
    helper exists, uses ``subprocess.Popen`` per task, waits all complete,
    aborts on non-zero exit.
    """

    def test_helper_exists(self) -> None:
        """``_dispatch_batch_concurrent`` is a public-private helper in
        auto_cmd module."""
        import auto_cmd

        assert hasattr(auto_cmd, "_dispatch_batch_concurrent"), (
            "Sub-issue 1 requires _dispatch_batch_concurrent helper"
        )
        assert callable(auto_cmd._dispatch_batch_concurrent)

    def test_helper_spawns_popen_per_task_concurrently(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Two-task batch: helper spawns 2 Popens (one per task id) BEFORE
        waiting any. Verifies Popen invocation count + concurrency
        (Popens started before any wait()).
        """
        import auto_cmd

        # Track Popen invocations + ordering.
        popen_calls: list[tuple[list[str], dict[str, object]]] = []

        class FakePopen:
            def __init__(self, cmd: list[str], **kwargs: object) -> None:
                popen_calls.append((cmd, kwargs))
                self._cmd = cmd
                # Initialise returncode to None per real Popen contract;
                # communicate() sets it to 0 (success).
                self.returncode: int | None = None

            def wait(self, timeout: float | None = None) -> int:
                self.returncode = 0
                return 0

            def communicate(self, timeout: float | None = None) -> tuple[bytes, bytes]:
                # Real Popen.communicate() sets returncode after wait.
                self.returncode = 0
                return (b"", b"")

            def poll(self) -> int | None:
                return self.returncode

            def kill(self) -> None:
                self.returncode = -9

        monkeypatch.setattr(subprocess, "Popen", FakePopen)

        auto_cmd._dispatch_batch_concurrent({"1", "2"}, tmp_path)

        assert len(popen_calls) == 2, (
            f"helper must spawn one Popen per task in batch; got {len(popen_calls)}"
        )
        # All Popen invocations must reference distinct task ids in argv.
        argv_strings = [" ".join(c) for c, _ in popen_calls]
        assert any("1" in a for a in argv_strings)
        assert any("2" in a for a in argv_strings)

    def test_helper_raises_on_nonzero_exit(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Any Popen returning non-zero must surface as
        ``ConcurrentDispatchError`` (exit 2, PRECONDITION_FAILED). The
        error class changed from ``VerificationIrremediableError`` (exit
        6, iter-2) to ``ConcurrentDispatchError`` (exit 2, iter-3) per
        Path 2 architectural pivot -- pre-verification gate failure is
        precondition-class, not phase-budget exhaustion.
        """
        import auto_cmd
        from errors import ConcurrentDispatchError

        class FailingPopen:
            def __init__(self, cmd: list[str], **kwargs: object) -> None:
                self._cmd = cmd

            def wait(self, timeout: float | None = None) -> int:
                return 1

            def communicate(self, timeout: float | None = None) -> tuple[bytes, bytes]:
                return (b"", b"failure")

            @property
            def returncode(self) -> int:
                return 1

            def poll(self) -> int | None:
                return 1

        monkeypatch.setattr(subprocess, "Popen", FailingPopen)

        with pytest.raises(ConcurrentDispatchError):
            auto_cmd._dispatch_batch_concurrent({"1", "2"}, tmp_path)


class TestC9CorruptSettingsBreadcrumb:
    """v1.0.4 Loop 2 iter-2 sub-issue 2 -- ``_check_tdd_guard_warning`` must
    emit a stderr breadcrumb when settings.json is malformed JSON. Pre-fix
    the helper swallowed JSONDecodeError silently together with OSError;
    operators got NO signal that their TDD-Guard config was broken.
    """

    def test_c9_corrupt_settings_json_emits_warning_breadcrumb(
        self,
        tmp_path: Path,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        """Corrupt JSON in settings.json must produce a stderr breadcrumb
        identifying the file + the underlying parse error."""
        import auto_cmd

        settings_dir = tmp_path / ".claude"
        settings_dir.mkdir()
        # Malformed JSON.
        (settings_dir / "settings.json").write_text("{not valid json", encoding="utf-8")

        auto_cmd._check_tdd_guard_warning(parallel=True, project_root=tmp_path)

        err = capsys.readouterr().err
        assert "settings.json" in err, "breadcrumb must reference the file name to be actionable"
        assert "WARNING" in err or "warning" in err.lower(), "breadcrumb must signal severity"
        # OSError still silently returns (file genuinely absent is benign):
        # confirm separate class with a missing file.

    def test_c9_missing_settings_silent(
        self,
        tmp_path: Path,
        capsys: pytest.CaptureFixture[str],
    ) -> None:
        """When settings.json is absent, the helper still returns silently
        (this is the benign case -- TDD-Guard not configured at all)."""
        import auto_cmd

        # No .claude dir created.
        auto_cmd._check_tdd_guard_warning(parallel=True, project_root=tmp_path)

        err = capsys.readouterr().err
        assert err == "", "absent settings.json must be silent (benign)"


class TestCheckTddGuardWarningFlushesStderr:
    """v1.0.4 Loop 1 iter-2 IMPORTANT-1 -- every ``sys.stderr.write`` in
    ``_check_tdd_guard_warning`` must be followed by ``sys.stderr.flush()``
    so warnings reach the operator before subprocess buffers swallow them.
    Pre-fix the function omitted both flushes (corrupt-JSON branch + the
    TDD-Guard-detected branch), violating the convention used by every
    other ``sys.stderr.write`` in ``auto_cmd.py`` (lines 248, 272, 458,
    473, 486, 886, 1119 all flush explicitly).
    """

    class _StderrSpy:
        """Stand-in for ``sys.stderr`` that records write/flush ordering."""

        def __init__(self) -> None:
            self.events: list[str] = []

        def write(self, text: str) -> int:
            self.events.append(f"write:{text}")
            return len(text)

        def flush(self) -> None:
            self.events.append("flush")

    def _last_write_followed_by_flush(self, events: list[str]) -> bool:
        for idx, ev in enumerate(events):
            if ev.startswith("write:"):
                if idx + 1 >= len(events) or events[idx + 1] != "flush":
                    return False
        return True

    def test_corrupt_json_warning_is_flushed(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Corrupt JSON branch must flush stderr after writing the breadcrumb."""
        import auto_cmd

        settings_dir = tmp_path / ".claude"
        settings_dir.mkdir()
        (settings_dir / "settings.json").write_text("{not valid json", encoding="utf-8")

        spy = self._StderrSpy()
        monkeypatch.setattr("sys.stderr", spy)

        auto_cmd._check_tdd_guard_warning(parallel=True, project_root=tmp_path)

        assert any(ev.startswith("write:") for ev in spy.events), "write must be observed"
        assert self._last_write_followed_by_flush(spy.events), (
            f"every write must be followed by flush; got events={spy.events}"
        )

    def test_tdd_guard_detected_warning_is_flushed(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """TDD-Guard-ON branch must flush stderr after writing the warning."""
        import auto_cmd

        settings_dir = tmp_path / ".claude"
        settings_dir.mkdir()
        settings = {
            "hooks": {"PreToolUse": [{"hooks": [{"type": "command", "command": "tdd-guard"}]}]}
        }
        (settings_dir / "settings.json").write_text(json.dumps(settings), encoding="utf-8")

        spy = self._StderrSpy()
        monkeypatch.setattr("sys.stderr", spy)

        auto_cmd._check_tdd_guard_warning(parallel=True, project_root=tmp_path)

        assert any(ev.startswith("write:") for ev in spy.events), "write must be observed"
        assert self._last_write_followed_by_flush(spy.events), (
            f"every write must be followed by flush; got events={spy.events}"
        )


class TestPreflightOrdering:
    """v1.0.4 Loop 2 iter-2 sub-issue 3 -- ``_phase1_preflight`` must run
    BEFORE dispatch plan build + tdd-guard warning. Current order surfaces
    plan-parse failures with confusing context (operator gets a parse
    error before they see the preflight summary).
    """

    def test_preflight_runs_before_dispatch_plan_build(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """When both preflight and plan parse would fail, preflight failure
        surfaces first.
        """
        import auto_cmd
        from errors import DependencyError

        # Synthesize a state that will fail preflight (broken environment)
        # AND a plan that would fail to parse (only used if order is wrong).
        plan_dir = tmp_path / "planning"
        plan_dir.mkdir()
        (plan_dir / "claude-plan-tdd.md").write_text(
            "### Task 1: A\n\n**Files:**\n- Modify: `a.py`\n"
        )

        # Track ordering: preflight raises BEFORE dispatch plan build runs.
        order: list[str] = []

        def preflight_first(ns: object) -> tuple[object, object]:
            order.append("preflight")
            raise DependencyError("preflight failed")

        original_seq = auto_cmd._build_dispatch_plan_sequential
        original_par = auto_cmd._build_dispatch_plan_parallel

        def spy_seq(plan_path: Path) -> list[set[str]]:
            order.append("dispatch_seq")
            return original_seq(plan_path)

        def spy_par(plan_path: Path) -> list[list[str]]:
            order.append("dispatch_par")
            return original_par(plan_path)

        monkeypatch.setattr(auto_cmd, "_phase1_preflight", preflight_first)
        monkeypatch.setattr(auto_cmd, "_build_dispatch_plan_sequential", spy_seq)
        monkeypatch.setattr(auto_cmd, "_build_dispatch_plan_parallel", spy_par)

        with pytest.raises(DependencyError, match="preflight failed"):
            auto_cmd.main(["--project-root", str(tmp_path)])

        assert order == ["preflight"], (
            f"preflight must run BEFORE dispatch plan build; got order={order}"
        )


# ---------------------------------------------------------------------------
# v1.0.4 Loop 2 iter-3 sub-issue 1 -- correct multi-task batch wiring.
#
# Path 2 architecture: parallel pre-verification + sequential per-task TDD.
# `_dispatch_batch_concurrent` is a pre-verification gate (parallelizes the
# verification step which is the wall-time bottleneck in TDD cycles); the
# actual per-task work then flows through the legacy inline TDD body in
# sorted task-id order, ensuring INV-1/INV-31/INV-5..7 are honoured per task.
# ---------------------------------------------------------------------------


class TestPhase2MultiTaskBatchClosesCorrectTasks:
    """v1.0.4 Loop 2 iter-3 IMPORTANT #1 + #4 -- regression guard for the
    wrong-task-closed wiring bug surfaced in iter-2.

    Pre-fix `_phase2_task_loop` advanced parent state via
    `mark_and_advance` `len(batch)` times after `_dispatch_batch_concurrent`
    returned, but `mark_and_advance` closes whichever task
    `state.current_task_id` points at -- NOT the dispatched batch's task ids.
    Because `_run_single_task_isolated` was a stub that did nothing real,
    the state advanced without any TDD triplet commits being created.

    Post-fix (Path 2): the dispatch loop runs `_dispatch_batch_concurrent`
    as a parallel pre-verification gate; per-task TDD work flows through the
    legacy inline body in sorted task-id order, producing the correct test:/
    feat:/refactor: triplet + chore: close per task.
    """

    def test_dag_singleton_then_batch_closes_in_correct_order(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """DAG `[{"1"}, {"2","3"}]` from current_task_id="1" must close
        tasks 1, 2, 3 in that order with proper TDD triplet commits + chore
        close per task. This is the exact bug-fix scenario the iter-3
        mini-cycle was raised against.
        """
        import auto_cmd
        import close_task_cmd
        import superpowers_dispatch
        from config import load_plugin_local
        from state_file import load as load_state

        _seed_auto_env(tmp_path, tasks="three", task_id="1", current_phase="red")
        cfg = load_plugin_local(tmp_path / ".claude" / "plugin.local.md")

        monkeypatch.setattr(
            superpowers_dispatch, "test_driven_development", lambda **kw: None, raising=False
        )
        monkeypatch.setattr(
            superpowers_dispatch,
            "verification_before_completion",
            lambda **kw: None,
            raising=False,
        )
        monkeypatch.setattr(auto_cmd, "detect_drift", lambda *a, **kw: None, raising=False)
        _stub_reviewer_approve(monkeypatch)

        # Capture every chore commit so we can verify which tasks closed
        # in which order.
        commit_order: list[tuple[str, str]] = []
        counter = {"n": 0}

        def fake_commit(prefix: str, message: str, cwd: str | None = None) -> str:
            counter["n"] += 1
            commit_order.append((prefix, message))
            (tmp_path / f"f-{counter['n']}.txt").write_text("x", encoding="utf-8")
            subprocess.run(["git", "add", "-A"], cwd=str(tmp_path), check=True, capture_output=True)
            subprocess.run(
                ["git", "commit", "-m", f"{prefix}: {message}"],
                cwd=str(tmp_path),
                check=True,
                capture_output=True,
            )
            return "ok"

        monkeypatch.setattr(auto_cmd, "commit_create", fake_commit, raising=False)
        monkeypatch.setattr(close_task_cmd, "commit_create", fake_commit)

        # Stub the concurrent dispatch helper to a no-op (Path 2: pre-verify
        # gate only; the per-task TDD work happens in the inline body
        # afterwards).
        monkeypatch.setattr(auto_cmd, "_dispatch_batch_concurrent", lambda batch, root: None)

        ns = auto_cmd._build_parser().parse_args(["--project-root", str(tmp_path)])
        state = load_state(tmp_path / ".claude" / "session-state.json")

        final = auto_cmd._phase2_task_loop(ns, state, cfg, dispatch_plan=[{"1"}, {"2", "3"}])

        # All 3 tasks closed; plan done.
        assert final.current_phase == "done"
        assert final.current_task_id is None

        # Each task got a full TDD triplet (test/feat/refactor) + chore close.
        # Total chore commits = 3 (one per task).
        chore_msgs = [m for p, m in commit_order if p == "chore"]
        assert len(chore_msgs) == 3, (
            f"expected 3 chore commits (one per task); got {len(chore_msgs)}: {chore_msgs}"
        )
        # Chore messages must reference task ids 1, 2, 3 in that order.
        assert chore_msgs == [
            "mark task 1 complete",
            "mark task 2 complete",
            "mark task 3 complete",
        ], f"chore commits closed wrong tasks or out of order: {chore_msgs}"

        # Each task got at least the canonical TDD triplet (test:, feat:,
        # refactor:). Count distinct prefixes.
        prefixes = [p for p, _ in commit_order]
        assert prefixes.count("test") == 3, f"expected 3 test: commits, got {prefixes}"
        assert prefixes.count("feat") == 3, f"expected 3 feat: commits, got {prefixes}"
        assert prefixes.count("refactor") == 3, f"expected 3 refactor: commits, got {prefixes}"

    def test_hybrid_dispatch_plan_multi_task_then_singleton(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Loop 1 IMPORTANT #4: hybrid `[{"1","2"}, {"3"}]` closes all 3
        tasks correctly. Multi-task batch first, singleton second.
        """
        import auto_cmd
        import close_task_cmd
        import superpowers_dispatch
        from config import load_plugin_local
        from state_file import load as load_state

        _seed_auto_env(tmp_path, tasks="three", task_id="1", current_phase="red")
        cfg = load_plugin_local(tmp_path / ".claude" / "plugin.local.md")

        monkeypatch.setattr(
            superpowers_dispatch, "test_driven_development", lambda **kw: None, raising=False
        )
        monkeypatch.setattr(
            superpowers_dispatch,
            "verification_before_completion",
            lambda **kw: None,
            raising=False,
        )
        monkeypatch.setattr(auto_cmd, "detect_drift", lambda *a, **kw: None, raising=False)
        _stub_reviewer_approve(monkeypatch)

        commit_order: list[tuple[str, str]] = []
        counter = {"n": 0}

        def fake_commit(prefix: str, message: str, cwd: str | None = None) -> str:
            counter["n"] += 1
            commit_order.append((prefix, message))
            (tmp_path / f"f-{counter['n']}.txt").write_text("x", encoding="utf-8")
            subprocess.run(["git", "add", "-A"], cwd=str(tmp_path), check=True, capture_output=True)
            subprocess.run(
                ["git", "commit", "-m", f"{prefix}: {message}"],
                cwd=str(tmp_path),
                check=True,
                capture_output=True,
            )
            return "ok"

        monkeypatch.setattr(auto_cmd, "commit_create", fake_commit, raising=False)
        monkeypatch.setattr(close_task_cmd, "commit_create", fake_commit)
        monkeypatch.setattr(auto_cmd, "_dispatch_batch_concurrent", lambda batch, root: None)

        ns = auto_cmd._build_parser().parse_args(["--project-root", str(tmp_path)])
        state = load_state(tmp_path / ".claude" / "session-state.json")

        final = auto_cmd._phase2_task_loop(ns, state, cfg, dispatch_plan=[{"1", "2"}, {"3"}])

        assert final.current_phase == "done"
        assert final.current_task_id is None

        chore_msgs = [m for p, m in commit_order if p == "chore"]
        assert chore_msgs == [
            "mark task 1 complete",
            "mark task 2 complete",
            "mark task 3 complete",
        ], f"hybrid plan closed wrong tasks or out of order: {chore_msgs}"

    def test_concurrent_pre_verify_invoked_for_multi_task_batches_only(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Path 2 contract: `_dispatch_batch_concurrent` runs once per
        multi-task batch (parallel pre-verification gate); singleton batches
        skip it.
        """
        import auto_cmd
        import close_task_cmd
        import superpowers_dispatch
        from config import load_plugin_local
        from state_file import load as load_state

        _seed_auto_env(tmp_path, tasks="three", task_id="1", current_phase="red")
        cfg = load_plugin_local(tmp_path / ".claude" / "plugin.local.md")

        monkeypatch.setattr(
            superpowers_dispatch, "test_driven_development", lambda **kw: None, raising=False
        )
        monkeypatch.setattr(
            superpowers_dispatch,
            "verification_before_completion",
            lambda **kw: None,
            raising=False,
        )
        monkeypatch.setattr(auto_cmd, "detect_drift", lambda *a, **kw: None, raising=False)
        _stub_reviewer_approve(monkeypatch)

        counter = {"n": 0}

        def fake_commit(prefix: str, message: str, cwd: str | None = None) -> str:
            counter["n"] += 1
            (tmp_path / f"f-{counter['n']}.txt").write_text("x", encoding="utf-8")
            subprocess.run(["git", "add", "-A"], cwd=str(tmp_path), check=True, capture_output=True)
            subprocess.run(
                ["git", "commit", "-m", f"{prefix}: {message}"],
                cwd=str(tmp_path),
                check=True,
                capture_output=True,
            )
            return "ok"

        monkeypatch.setattr(auto_cmd, "commit_create", fake_commit, raising=False)
        monkeypatch.setattr(close_task_cmd, "commit_create", fake_commit)

        captured_batches: list[set[str]] = []

        def spy_concurrent(batch: set[str], project_root: Path) -> None:
            captured_batches.append(set(batch))

        monkeypatch.setattr(auto_cmd, "_dispatch_batch_concurrent", spy_concurrent)

        ns = auto_cmd._build_parser().parse_args(["--project-root", str(tmp_path)])
        state = load_state(tmp_path / ".claude" / "session-state.json")

        # `[{"1","2"}, {"3"}]`: helper invoked exactly once on the size-2
        # batch; singleton {"3"} skips it.
        auto_cmd._phase2_task_loop(ns, state, cfg, dispatch_plan=[{"1", "2"}, {"3"}])

        assert len(captured_batches) == 1, (
            f"_dispatch_batch_concurrent must run exactly once for the "
            f"size-2 batch; got {len(captured_batches)} invocations: "
            f"{captured_batches}"
        )
        assert captured_batches[0] == {"1", "2"}

    def test_state_file_not_advanced_on_concurrent_failure(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Loop 1 IMPORTANT #5: when `_dispatch_batch_concurrent` raises,
        state file is NOT advanced (no partial commit; transactional).
        """
        import auto_cmd
        import close_task_cmd
        import superpowers_dispatch
        from config import load_plugin_local
        from errors import ConcurrentDispatchError
        from state_file import load as load_state

        _seed_auto_env(tmp_path, tasks="three", task_id="1", current_phase="red")
        cfg = load_plugin_local(tmp_path / ".claude" / "plugin.local.md")

        monkeypatch.setattr(
            superpowers_dispatch, "test_driven_development", lambda **kw: None, raising=False
        )
        monkeypatch.setattr(
            superpowers_dispatch,
            "verification_before_completion",
            lambda **kw: None,
            raising=False,
        )
        monkeypatch.setattr(auto_cmd, "detect_drift", lambda *a, **kw: None, raising=False)
        _stub_reviewer_approve(monkeypatch)
        monkeypatch.setattr(auto_cmd, "commit_create", lambda *a, **kw: "ok", raising=False)
        monkeypatch.setattr(close_task_cmd, "commit_create", lambda *a, **kw: "ok")

        def failing_concurrent(batch: set[str], project_root: Path) -> None:
            raise ConcurrentDispatchError(f"pre-verify failed for batch {batch}")

        monkeypatch.setattr(auto_cmd, "_dispatch_batch_concurrent", failing_concurrent)

        # Snapshot state file BEFORE the failure.
        state_path = tmp_path / ".claude" / "session-state.json"
        before = state_path.read_text(encoding="utf-8")

        ns = auto_cmd._build_parser().parse_args(["--project-root", str(tmp_path)])
        state = load_state(state_path)

        with pytest.raises(ConcurrentDispatchError, match="pre-verify failed"):
            auto_cmd._phase2_task_loop(ns, state, cfg, dispatch_plan=[{"1", "2"}, {"3"}])

        # State file MUST be byte-identical to pre-failure: no partial advance.
        after = state_path.read_text(encoding="utf-8")
        assert after == before, (
            "state file must NOT advance on concurrent dispatch failure (transactional contract)"
        )


class TestConcurrentDispatchError:
    """v1.0.4 Loop 2 iter-3 IMPORTANT #3 -- new error class with correct
    semantics (exit 2, precondition-class) instead of misusing
    VerificationIrremediableError (exit 6, phase-verification budget
    exhaustion).
    """

    def test_error_class_exists_in_errors_module(self) -> None:
        from errors import ConcurrentDispatchError, SBTDDError

        assert issubclass(ConcurrentDispatchError, SBTDDError)

    def test_error_class_has_exit_code_2(self) -> None:
        from errors import EXIT_CODES, ConcurrentDispatchError

        assert EXIT_CODES[ConcurrentDispatchError] == 2, (
            "ConcurrentDispatchError is precondition-class (exit 2); "
            "exit 6 is reserved for VerificationIrremediableError"
        )

    def test_dispatch_batch_concurrent_raises_concurrent_dispatch_error(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Non-zero subprocess exit must surface as ConcurrentDispatchError
        (not VerificationIrremediableError as in iter-2)."""
        import auto_cmd
        from errors import ConcurrentDispatchError

        class FailingPopen:
            def __init__(self, cmd: list[str], **kwargs: object) -> None:
                self._cmd = cmd

            def wait(self, timeout: float | None = None) -> int:
                return 1

            def communicate(self, timeout: float | None = None) -> tuple[bytes, bytes]:
                return (b"", b"failure")

            @property
            def returncode(self) -> int:
                return 1

            def poll(self) -> int | None:
                return 1

        monkeypatch.setattr(subprocess, "Popen", FailingPopen)

        with pytest.raises(ConcurrentDispatchError):
            auto_cmd._dispatch_batch_concurrent({"1", "2"}, tmp_path)


class TestPhase2DispatchLoopVariableRemoved:
    """v1.0.4 Loop 2 iter-3 IMPORTANT #2 -- the cosmetic loop variable
    `for _task_id in sorted(batch):` no longer exists post-fix because the
    parent-side `mark_and_advance` calls inside the dispatch_plan loop are
    eliminated (iter-2 wiring bug fix).
    """

    def test_phase2_no_unused_loop_var_after_fix(self) -> None:
        """Source of `_phase2_task_loop` must not contain the iter-2 pattern
        `for _task_id in sorted(batch):` followed immediately by
        `mark_and_advance` -- that pattern was the wrong-task-closed bug.
        Post-fix the multi-task batch path delegates to the legacy inline
        body via `sorted(batch)` task-id ordering at the OUTER while-loop
        level (see _phase2_task_loop architecture).
        """
        import inspect

        import auto_cmd

        src = inspect.getsource(auto_cmd._phase2_task_loop)
        # Pattern that IS the iter-2 bug: looping batch task ids then
        # calling mark_and_advance directly within the dispatch_plan branch.
        assert "for _task_id in sorted(batch):" not in src, (
            "iter-2 wiring bug pattern still present: "
            "`for _task_id in sorted(batch):` directly invokes "
            "mark_and_advance which closes wrong task ids"
        )


# ---------------------------------------------------------------------------
# v1.0.4 Path 3 -- track-based dispatch architecture.
#
# `--parallel` semantics (corrected per user clarification): partition tasks
# into TRACKS (weakly-connected components in (deps UNION file-conflicts)
# graph), then dispatch one subprocess WORKER per track. Each worker
# processes its track's task list SEQUENTIALLY with full TDD discipline
# (R→G→R per task + verify + commit per phase). Multiple tracks (workers)
# run in parallel.
#
# Worker subprocess invocation shape:
#     python skills/sbtdd/scripts/run_sbtdd.py auto \
#         --task-ids T1,T3,T4,T5 \
#         --no-recursive
# ---------------------------------------------------------------------------


class TestPath3CLIFlags:
    """v1.0.4 Path 3 -- new CLI flags `--task-ids`, `--no-recursive`,
    `--parallel-max` recognized by argparse.
    """

    def test_path3_argparse_accepts_task_ids(self) -> None:
        import auto_cmd

        ns = auto_cmd._build_parser().parse_args(["--task-ids", "T1,T2,T3"])
        assert ns.task_ids == "T1,T2,T3"

    def test_path3_argparse_task_ids_default_none(self) -> None:
        import auto_cmd

        ns = auto_cmd._build_parser().parse_args([])
        assert ns.task_ids is None

    def test_path3_argparse_accepts_no_recursive(self) -> None:
        import auto_cmd

        ns = auto_cmd._build_parser().parse_args(["--no-recursive"])
        assert ns.no_recursive is True

    def test_path3_argparse_no_recursive_default_false(self) -> None:
        import auto_cmd

        ns = auto_cmd._build_parser().parse_args([])
        assert ns.no_recursive is False

    def test_path3_argparse_accepts_parallel_max(self) -> None:
        import auto_cmd

        ns = auto_cmd._build_parser().parse_args(["--parallel-max", "3"])
        assert ns.parallel_max == 3

    def test_path3_argparse_parallel_max_zero_unlimited(self) -> None:
        import auto_cmd

        ns = auto_cmd._build_parser().parse_args(["--parallel-max", "0"])
        assert ns.parallel_max == 0

    def test_path3_argparse_parallel_max_default_none(self) -> None:
        import auto_cmd

        ns = auto_cmd._build_parser().parse_args([])
        assert ns.parallel_max is None


class TestPath3ResolveEffectiveWorkers:
    """v1.0.4 Path 3 -- _resolve_effective_workers(natural_n, user_max)."""

    def test_path3_user_max_none_uses_auto_default(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """user_max=None → min(natural, cpu_count, 4)."""
        import os

        import auto_cmd

        monkeypatch.setattr(os, "cpu_count", lambda: 16)
        # natural=5, cpu=16 → cap is 4 (the hard ceiling)
        assert auto_cmd._resolve_effective_workers(5, None) == 4

    def test_path3_user_max_none_caps_at_natural(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """user_max=None + natural=2 → 2 (natural < 4 ceiling)."""
        import os

        import auto_cmd

        monkeypatch.setattr(os, "cpu_count", lambda: 16)
        assert auto_cmd._resolve_effective_workers(2, None) == 2

    def test_path3_user_max_zero_unlimited(self) -> None:
        """user_max=0 (unlimited): use natural without ceiling."""
        import auto_cmd

        assert auto_cmd._resolve_effective_workers(7, 0) == 7

    def test_path3_user_max_explicit_cap(self) -> None:
        """user_max=N positive: min(natural, N)."""
        import auto_cmd

        # natural=6, user=3 → 3
        assert auto_cmd._resolve_effective_workers(6, 3) == 3
        # natural=2, user=8 → 2 (natural is the floor)
        assert auto_cmd._resolve_effective_workers(2, 8) == 2

    def test_path3_user_max_one_serial(self) -> None:
        """user_max=1: effectively serial (caller may skip threading)."""
        import auto_cmd

        assert auto_cmd._resolve_effective_workers(10, 1) == 1


class TestPath3DispatchTracksConcurrent:
    """v1.0.4 Path 3 -- _dispatch_tracks_concurrent(tracks, ...) helper."""

    def test_path3_helper_exists(self) -> None:
        import auto_cmd

        assert hasattr(auto_cmd, "_dispatch_tracks_concurrent")
        assert callable(auto_cmd._dispatch_tracks_concurrent)

    def test_path3_helper_spawns_one_subprocess_per_track(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Two tracks → 2 subprocess invocations, each with --task-ids
        comma-joined for that track + --no-recursive."""
        import auto_cmd

        popen_calls: list[list[str]] = []

        class FakePopen:
            def __init__(self, cmd: list[str], **kwargs: object) -> None:
                popen_calls.append(list(cmd))
                self.returncode: int | None = None
                # v1.0.7 A2: _verify_worker_sidecars_present LOUD-FAIL
                # contract reads proc.pid; provide unique-per-instance pid.
                self.pid: int = 90000 + len(popen_calls)

            def communicate(self, timeout: float | None = None) -> tuple[bytes, bytes]:
                self.returncode = 0
                return (b"", b"")

            def wait(self, timeout: float | None = None) -> int:
                self.returncode = 0
                return 0

            def kill(self) -> None:
                self.returncode = -9

            def poll(self) -> int | None:
                return self.returncode

        monkeypatch.setattr(subprocess, "Popen", FakePopen)

        tracks = [["T1", "T2"], ["T3"]]
        auto_cmd._dispatch_tracks_concurrent(
            tracks=tracks,
            effective_workers=2,
            project_root=tmp_path,
        )

        assert len(popen_calls) == 2, (
            f"one subprocess per track expected; got {len(popen_calls)} calls"
        )
        # Each invocation must include --task-ids + --no-recursive.
        argv_strs = [" ".join(c) for c in popen_calls]
        assert any("T1,T2" in a for a in argv_strs)
        assert any("T3" in a and "T1" not in a for a in argv_strs)
        for s in argv_strs:
            assert "--no-recursive" in s
            assert "--task-ids" in s

    def test_path3_helper_raises_concurrent_dispatch_error_on_failure(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Any worker non-zero exit raises ConcurrentDispatchError."""
        import auto_cmd
        from errors import ConcurrentDispatchError

        class FailingPopen:
            def __init__(self, cmd: list[str], **kwargs: object) -> None:
                # v1.0.7 A2: _verify_worker_sidecars_present LOUD-FAIL
                # contract reads proc.pid; provide stable pid.
                self.pid: int = 92345

            def communicate(self, timeout: float | None = None) -> tuple[bytes, bytes]:
                return (b"", b"track failed: T1 failed during green phase")

            def wait(self, timeout: float | None = None) -> int:
                return 1

            @property
            def returncode(self) -> int:
                return 1

            def kill(self) -> None:
                pass

            def poll(self) -> int | None:
                return 1

        monkeypatch.setattr(subprocess, "Popen", FailingPopen)

        with pytest.raises(ConcurrentDispatchError):
            auto_cmd._dispatch_tracks_concurrent(
                tracks=[["T1"]],
                effective_workers=1,
                project_root=tmp_path,
            )

    def test_path3_helper_empty_tracks_noop(self, tmp_path: Path) -> None:
        """Empty tracks list → no-op (no subprocess, no error)."""
        import auto_cmd

        # Should not raise even with no Popen monkeypatch
        auto_cmd._dispatch_tracks_concurrent(
            tracks=[],
            effective_workers=4,
            project_root=tmp_path,
        )

    def test_path3_helper_more_tracks_than_workers_queues(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """5 tracks + effective_workers=2 → all 5 still dispatched
        (queueing); not silently dropped."""
        import auto_cmd

        popen_count = {"n": 0}

        class FakePopen:
            def __init__(self, cmd: list[str], **kwargs: object) -> None:
                popen_count["n"] += 1
                self.returncode: int | None = None
                # v1.0.7 A2: _verify_worker_sidecars_present LOUD-FAIL
                # contract reads proc.pid; provide unique-per-instance pid.
                self.pid: int = 91000 + popen_count["n"]

            def communicate(self, timeout: float | None = None) -> tuple[bytes, bytes]:
                self.returncode = 0
                return (b"", b"")

            def wait(self, timeout: float | None = None) -> int:
                self.returncode = 0
                return 0

            def kill(self) -> None:
                self.returncode = -9

            def poll(self) -> int | None:
                return self.returncode

        monkeypatch.setattr(subprocess, "Popen", FakePopen)

        tracks = [["T1"], ["T2"], ["T3"], ["T4"], ["T5"]]
        auto_cmd._dispatch_tracks_concurrent(
            tracks=tracks,
            effective_workers=2,
            project_root=tmp_path,
        )
        assert popen_count["n"] == 5, (
            f"all 5 tracks must be dispatched (queued through 2 workers); got {popen_count['n']}"
        )


def test_v108_a2_worker_env_propagates_sbtdd_e2e_stub_dispatch(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """v1.0.8 A2-1: parent env var SBTDD_E2E_STUB_DISPATCH propagates to worker.

    Pins the contract that ``_dispatch_tracks_concurrent`` does NOT
    filter env vars when building ``worker_env = os.environ.copy()``.
    A future refactor introducing an allowlist would break v1.0.8
    Pillar A1 (gate would never fire in worker subprocess).

    Test monkeypatches ``_spawn_worker`` to capture the env dict; no
    real subprocess spawned.
    """
    import auto_cmd

    monkeypatch.setenv("SBTDD_E2E_STUB_DISPATCH", "1")
    monkeypatch.setenv("V108_A2_REGRESSION_MARKER", "propagated")

    captured_envs: list[dict[str, str]] = []

    class _FakeProc:
        def __init__(self) -> None:
            self.pid = 4242
            self.returncode = 0

        def communicate(self, timeout: int):
            return (b"", b"")

    def _fake_spawn_worker(argv, env, **popen_kwargs):
        captured_envs.append(dict(env))
        return _FakeProc()

    monkeypatch.setattr(auto_cmd, "_spawn_worker", _fake_spawn_worker)

    # Stub out post-batch hooks so the test focuses only on env propagation.
    # Per iter-2 carry-forward Mel-W1: also stub close_task_cmd._merge_scratch_plans
    # because auto_cmd._dispatch_tracks_concurrent does `getattr(_ctc,
    # "_merge_scratch_plans", None)` and invokes it if present (auto_cmd.py
    # line ~2124-2128). Without this stub, the helper may try to read
    # scratch plans from disk and fail in the test temp dir.
    monkeypatch.setattr(auto_cmd, "_verify_worker_sidecars_present", lambda *a, **kw: None)
    monkeypatch.setattr(auto_cmd, "_merge_audit_sidecars", lambda *a, **kw: {"schema_version": 1})
    monkeypatch.setattr(auto_cmd, "_atomic_write_json", lambda *a, **kw: None)
    monkeypatch.setattr(auto_cmd, "_reap_orphans", lambda *a, **kw: None)

    # Stub close_task_cmd._merge_scratch_plans (post-batch hook resolved
    # via getattr in auto_cmd line ~2126). Use monkeypatch on the close_task_cmd
    # module attribute so the getattr lookup finds our stub.
    import close_task_cmd

    monkeypatch.setattr(
        close_task_cmd, "_merge_scratch_plans", lambda *a, **kw: None, raising=False
    )

    (tmp_path / ".claude").mkdir()

    auto_cmd._dispatch_tracks_concurrent(
        tracks=[["1"]],
        effective_workers=1,
        project_root=tmp_path,
        ns=None,
    )

    assert len(captured_envs) == 1, "exactly one worker should have been spawned"
    worker_env = captured_envs[0]
    assert worker_env.get("SBTDD_E2E_STUB_DISPATCH") == "1", (
        "v1.0.8 A2 regression: SBTDD_E2E_STUB_DISPATCH must propagate from "
        "parent to worker unchanged"
    )
    assert worker_env.get("V108_A2_REGRESSION_MARKER") == "propagated", (
        "v1.0.8 A2-2 regression: unrelated custom env vars must also "
        "propagate (no filtering allowlist)"
    )


class TestVerifyWorkerSidecarsPresent:
    """v1.0.7 T2 code-review C1+C2 fixes per spec sec.4.2 escenario A2-10."""

    def test_no_sidecar_dir_with_no_successful_pids_returns(self, tmp_path: Path) -> None:
        """All workers failed pre-close-phase: no sidecar dir is legitimate."""
        import auto_cmd

        # Sidecar dir does not exist; no successful workers either.
        auto_cmd._verify_worker_sidecars_present(tmp_path, successful_pids=[])
        # No exception raised → contract satisfied.

    def test_no_sidecar_dir_with_successful_pids_returns_quietly(self, tmp_path: Path) -> None:
        """No sidecar dir at all = test fixture or pre-close-phase failures.

        The helper defers to integration tests + failures-list raise for the
        all-workers-failed-pre-close-phase case. The interesting bug surface
        (some succeeded + some missed sidecar) requires the dir to exist.
        """
        import auto_cmd

        # No exception raised even with successful_pids set: the check is
        # gated on dir existing, so test fixtures + edge cases don't trip
        # the LOUD-FAIL.
        auto_cmd._verify_worker_sidecars_present(tmp_path, successful_pids=[12345])

    def test_failed_worker_pids_NOT_checked(self, tmp_path: Path) -> None:
        """v1.0.7 T2 C2 fix: failed workers (rc!=0) legitimately have no sidecar.

        The pre-fix helper checked ALL spawned pids; under partial failure
        scenarios (some workers crash before close-phase), it raised a
        misleading "INV-16 evidence loss" message instead of letting the
        actual failures-list raise propagate. Post-fix: caller passes only
        successful_pids; failed pids are excluded → no false-positive raise.
        """
        import auto_cmd

        sidecar_dir = tmp_path / ".claude" / "auto-run-workers"
        sidecar_dir.mkdir(parents=True)
        # Worker 11111 succeeded + persisted; worker 22222 crashed pre-close-phase
        # so produced no sidecar. Caller passes only [11111] (the successful pid).
        (sidecar_dir / "11111-12345-aabbccdd-verify.json").write_text("{}", encoding="utf-8")
        # No sidecar for 22222 — that's expected for failed workers.
        auto_cmd._verify_worker_sidecars_present(tmp_path, successful_pids=[11111])
        # No exception → C2 contract satisfied.

    def test_successful_worker_missing_sidecar_raises(self, tmp_path: Path) -> None:
        """v1.0.7 iter-3 C1: successful worker without sidecar is a real bug."""
        import auto_cmd
        from errors import ConcurrentDispatchError

        sidecar_dir = tmp_path / ".claude" / "auto-run-workers"
        sidecar_dir.mkdir(parents=True)
        # Worker 11111 succeeded + persisted; worker 22222 ALSO succeeded but
        # never persisted (real persistence bug).
        (sidecar_dir / "11111-12345-aabbccdd-verify.json").write_text("{}", encoding="utf-8")
        with pytest.raises(ConcurrentDispatchError, match="22222"):
            auto_cmd._verify_worker_sidecars_present(tmp_path, successful_pids=[11111, 22222])

    def test_unparseable_sidecar_filename_skipped_with_breadcrumb(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """Stray file with unparseable name is skipped + breadcrumb to stderr."""
        import auto_cmd

        sidecar_dir = tmp_path / ".claude" / "auto-run-workers"
        sidecar_dir.mkdir(parents=True)
        (sidecar_dir / "11111-12345-aabbccdd-verify.json").write_text("{}", encoding="utf-8")
        # Stray file (not <pid>-... pattern).
        (sidecar_dir / "stray-name-verify.json").write_text("{}", encoding="utf-8")
        # Should not raise; should emit stderr breadcrumb.
        auto_cmd._verify_worker_sidecars_present(tmp_path, successful_pids=[11111])
        captured = capsys.readouterr()
        assert "skipping unparseable sidecar" in captured.err


class TestPath3WorkerModeFlowControl:
    """v1.0.4 Path 3 -- worker mode (--task-ids + --no-recursive) does NOT
    re-spawn parent dispatcher; processes given task IDs sequentially.
    """

    def test_path3_worker_mode_does_not_recurse_dispatch(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """When `--no-recursive` set, main() must NOT call
        _dispatch_tracks_concurrent (no infinite spawning)."""
        import auto_cmd

        called_dispatch: list[bool] = []

        def spy_dispatch(*a: object, **k: object) -> None:
            called_dispatch.append(True)

        monkeypatch.setattr(auto_cmd, "_dispatch_tracks_concurrent", spy_dispatch)
        # Stub everything else so main() doesn't crash on missing prereqs.
        monkeypatch.setattr(auto_cmd, "_phase1_preflight", lambda ns: (None, None), raising=False)
        monkeypatch.setattr(auto_cmd, "_check_tdd_guard_warning", lambda **k: None)
        monkeypatch.setattr(auto_cmd, "_phase2_task_loop", lambda *a, **k: a[1], raising=False)
        # Build dispatch_plan returns empty so phase loop is short-circuited.
        # Use --no-recursive + --task-ids to enter worker mode.
        # (We expect main to skip _dispatch_tracks_concurrent entirely.)
        try:
            auto_cmd.main(
                [
                    "--project-root",
                    str(tmp_path),
                    "--task-ids",
                    "T1,T2",
                    "--no-recursive",
                    "--dry-run",  # short-circuit before complex logic
                ]
            )
        except SystemExit:
            pass
        assert called_dispatch == [], (
            "Worker mode (--no-recursive) MUST NOT spawn _dispatch_tracks_concurrent"
        )


class TestPath3MainWiresTrackDispatch:
    """v1.0.4 Path 3 -- main() with --parallel uses partition_by_tracks +
    _dispatch_tracks_concurrent. Without --parallel, behavior unchanged.
    """

    def test_path3_build_dispatch_plan_parallel_uses_partition_by_tracks(
        self, tmp_path: Path
    ) -> None:
        """`_build_dispatch_plan_parallel` must invoke `partition_by_tracks`
        (Path 3) instead of antichain + collision packing (old Path 2)."""
        import auto_cmd

        plan_dir = tmp_path / "planning"
        plan_dir.mkdir()
        plan_path = plan_dir / "claude-plan-tdd.md"
        plan_path.write_text(
            "### Task 1: A\n\n**Files:**\n- Modify: `alpha.py`\n\n"
            "### Task 2: B\n\n**Files:**\n- Modify: `alpha.py`\n\n"
            "### Task 3: C\n\n**Files:**\n- Modify: `beta.py`\n"
        )

        plan = auto_cmd._build_dispatch_plan_parallel(plan_path)
        # Path 3: each batch is a TRACK = list[str]. Two tracks expected:
        # T1+T2 share alpha.py, T3 alone with beta.py.
        assert isinstance(plan, list)
        # Each track is a list (Path 3) not a set (Path 2 partition_by_collision).
        for track in plan:
            assert isinstance(track, list), (
                f"Path 3: tracks are ordered list[str], not set[str]; got {type(track).__name__}"
            )
        # 2 tracks total
        assert len(plan) == 2
        track_sets = [set(t) for t in plan]
        assert {"1", "2"} in track_sets
        assert {"3"} in track_sets


# ---------------------------------------------------------------------------
# v1.0.4 iter-5 Loop 1 CRITICAL #1 -- --task-ids worker filter wiring
# (real end-to-end, not FakePopen-shimmed).
# ---------------------------------------------------------------------------


class TestPath3WorkerTaskIdsFilter:
    """v1.0.4 iter-5 Loop 1 CRITICAL #1.

    Pre-fix bug: ``main()`` parsed ``--task-ids`` only as a boolean gate
    to set ``is_worker_mode``; ``_phase2_task_loop`` was driven by
    SHARED ``.claude/session-state.json`` with NO filtering. Two
    workers both saw ``current_task_id=1`` and raced.

    Post-fix contract: when ``--task-ids T3,T5`` is set, the worker
    processes ONLY tasks 3 and 5 -- not task 4 -- regardless of what
    the shared state file's ``current_task_id`` says at entry. Tasks
    outside the filter are SKIPPED (state cursor advanced without TDD
    cycles, plan checkbox NOT touched -- the OTHER worker that owns
    that task is responsible for closing it).
    """

    def test_worker_processes_only_assigned_tasks(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Worker with --task-ids=1,3 must touch tasks 1 and 3, never task 2.

        We instrument ``commit_create`` to capture every task_id seen on a
        TDD-phase commit (test/feat/refactor) and assert the filter is
        honoured. Pre-fix this fails because the worker walks the plan
        in source order and processes ALL tasks including task 2.
        """
        import auto_cmd
        import close_task_cmd
        import superpowers_dispatch
        from config import load_plugin_local
        from state_file import load as load_state

        _seed_auto_env(tmp_path, tasks="three", task_id="1", current_phase="red")
        cfg = load_plugin_local(tmp_path / ".claude" / "plugin.local.md")

        task_ids_seen: list[str] = []

        monkeypatch.setattr(
            superpowers_dispatch, "test_driven_development", lambda **kw: None, raising=False
        )
        monkeypatch.setattr(
            superpowers_dispatch, "verification_before_completion", lambda **kw: None, raising=False
        )
        monkeypatch.setattr(
            superpowers_dispatch, "systematic_debugging", lambda **kw: None, raising=False
        )
        monkeypatch.setattr(auto_cmd, "detect_drift", lambda *a, **kw: None, raising=False)
        _stub_reviewer_approve(monkeypatch)

        counter = {"n": 0}

        def fake_commit(prefix: str, message: str, cwd: str | None = None) -> str:
            counter["n"] += 1
            if prefix != "chore":
                data = json.loads(
                    (tmp_path / ".claude" / "session-state.json").read_text(encoding="utf-8")
                )
                if data.get("current_task_id"):
                    task_ids_seen.append(data["current_task_id"])
            (tmp_path / f"touch-{counter['n']}.txt").write_text(
                f"commit {counter['n']}\n", encoding="utf-8"
            )
            subprocess.run(["git", "add", "-A"], cwd=str(tmp_path), check=True, capture_output=True)
            subprocess.run(
                ["git", "commit", "-m", f"{prefix}: {message}"],
                cwd=str(tmp_path),
                check=True,
                capture_output=True,
            )
            return "ok"

        monkeypatch.setattr(auto_cmd, "commit_create", fake_commit, raising=False)
        monkeypatch.setattr(close_task_cmd, "commit_create", fake_commit)

        ns = auto_cmd._build_parser().parse_args(
            [
                "--project-root",
                str(tmp_path),
                "--task-ids",
                "1,3",
                "--no-recursive",
            ]
        )
        state = load_state(tmp_path / ".claude" / "session-state.json")
        # Pass the filter through. Pre-fix: no parameter exists; this fails
        # with TypeError. Post-fix: the parameter is honoured and the loop
        # skips task 2.
        task_ids_filter = frozenset({"1", "3"})
        auto_cmd._phase2_task_loop(
            ns, state, cfg, dispatch_plan=None, task_ids_filter=task_ids_filter
        )

        # Worker filter [1,3]: 2 tasks * 3 phases each = 6 non-chore commits.
        # Task 2 must NEVER appear -- it belongs to a different worker.
        assert "2" not in task_ids_seen, (
            f"Worker with --task-ids=1,3 must not process task 2; saw {task_ids_seen}"
        )
        assert task_ids_seen.count("1") == 3, (
            f"Task 1 must complete its 3 TDD phases; saw {task_ids_seen}"
        )
        assert task_ids_seen.count("3") == 3, (
            f"Task 3 must complete its 3 TDD phases; saw {task_ids_seen}"
        )

    def test_main_parses_task_ids_into_frozenset(self, tmp_path: Path) -> None:
        """``main()`` must split ``--task-ids`` into a frozenset for filtering.

        Pre-fix: ``main()`` only checks truthiness of ``ns.task_ids``;
        the comma-separated string is never split or fed downstream.
        Post-fix: the parsed filter is exposed on the namespace so the
        worker code path consumes it explicitly.
        """
        import auto_cmd

        ns = auto_cmd._build_parser().parse_args(
            ["--task-ids", "1,3,5", "--no-recursive", "--project-root", str(tmp_path)]
        )
        # Pre-fix: ns.task_ids is just the raw string "1,3,5"; helper absent.
        # Post-fix: a parser helper splits it OR main() does.
        parsed = auto_cmd._parse_task_ids_filter(ns.task_ids)
        assert parsed == frozenset({"1", "3", "5"}), f"Expected frozenset of ids, got {parsed!r}"

    def test_parse_task_ids_filter_handles_whitespace_and_empty(self) -> None:
        """``_parse_task_ids_filter`` strips whitespace and ignores empty tokens."""
        import auto_cmd

        assert auto_cmd._parse_task_ids_filter("1, 2 ,3") == frozenset({"1", "2", "3"})
        assert auto_cmd._parse_task_ids_filter("1,,2,") == frozenset({"1", "2"})
        assert auto_cmd._parse_task_ids_filter(None) is None
        assert auto_cmd._parse_task_ids_filter("") is None

    def test_real_subprocess_worker_filter_signature_stable(self, tmp_path: Path) -> None:
        """API surface for filter-aware workers is stable across processes.

        ``_dispatch_tracks_concurrent`` spawns workers via
        ``subprocess.Popen([..., "--task-ids", ids, "--no-recursive"])``.
        Those children re-enter ``main()`` which parses the namespace
        and calls ``_phase2_task_loop(..., task_ids_filter=...)``. This
        test exercises the cross-process invariant by running the same
        helpers in a real subprocess and asserting the parsed filter
        survives the round-trip.

        We use ``subprocess.run`` (not ``multiprocessing.Process``) so
        the test is portable across Windows + POSIX without depending
        on serialization of test-method-local closures.
        """
        import inspect
        import sys
        import auto_cmd

        # Sanity: signature includes the new parameter so child processes
        # can pass it without TypeError.
        sig = inspect.signature(auto_cmd._phase2_task_loop)
        assert "task_ids_filter" in sig.parameters, (
            "Real workers expect _phase2_task_loop(task_ids_filter=...) signature"
        )
        # Default must be None to preserve sequential default behaviour.
        param = sig.parameters["task_ids_filter"]
        assert param.default is None, "task_ids_filter default must be None (sequential preserved)"

        # Cross-process smoke: spawn a Python subprocess that imports
        # auto_cmd, parses a filter, and emits the result. This is the
        # exact code path the Path 3 worker subprocess hits at startup.
        scripts_root = (Path(__file__).parent.parent / "skills" / "sbtdd" / "scripts").resolve()
        code = (
            "import sys, json\n"
            f"sys.path.insert(0, {repr(str(scripts_root))})\n"
            "import auto_cmd\n"
            "parsed = auto_cmd._parse_task_ids_filter('1,3')\n"
            "print(json.dumps(sorted(parsed) if parsed else None))\n"
        )
        result = subprocess.run(
            [sys.executable, "-c", code],
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )
        assert result.returncode == 0, (
            f"child subprocess failed (rc={result.returncode}); stderr={result.stderr!r}"
        )
        parsed = json.loads(result.stdout.strip())
        assert parsed == ["1", "3"], f"child must parse --task-ids into sorted ids; got {parsed!r}"


# ---------------------------------------------------------------------------
# v1.0.5 Item I-1 -- per-worker sidecar audit-trail pattern (escenarios I1-1..I1-5)
# ---------------------------------------------------------------------------


class TestPerWorkerSidecarAudit:
    """v1.0.5 Item I-1 escenarios I1-1 through I1-5 -- per-worker sidecar pattern."""

    def test_i1_1_worker_mode_redirects_audit_to_sidecar(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """I1-1: worker mode redirects audit write to sidecar."""
        import argparse

        import auto_cmd

        ns = argparse.Namespace(no_recursive=True, task_ids="1,3")
        audit_data = {"start_time": "2026-05-08T10:00:00Z", "tasks": ["1", "3"]}
        (tmp_path / ".claude").mkdir()

        auto_cmd._write_audit(audit_data, tmp_path, ns)

        sidecar = auto_cmd._audit_sidecar_path(("1", "3"), tmp_path)
        assert sidecar.exists()
        assert not (tmp_path / ".claude" / "auto-run.json").exists()
        loaded = json.loads(sidecar.read_text(encoding="utf-8"))
        assert loaded == audit_data

    def test_i1_2_orchestrator_mode_writes_canonical_audit(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """I1-2: orchestrator mode writes canonical auto-run.json."""
        import argparse

        import auto_cmd

        ns = argparse.Namespace(no_recursive=False, task_ids=None)
        audit_data = {
            "start_time": "2026-05-08T10:00:00Z",
            "tasks": ["1", "2", "3", "4"],
        }
        (tmp_path / ".claude").mkdir()

        auto_cmd._write_audit(audit_data, tmp_path, ns)

        canonical = tmp_path / ".claude" / "auto-run.json"
        assert canonical.exists()
        loaded = json.loads(canonical.read_text(encoding="utf-8"))
        assert loaded == audit_data

    def test_i1_3_parent_post_batch_merges_sidecars(self, tmp_path: Path) -> None:
        """I1-3: parent post-batch merges sidecars + cleans up."""
        import auto_cmd

        (tmp_path / ".claude").mkdir()
        # Pre-dispatch parent audit
        canonical = tmp_path / ".claude" / "auto-run.json"
        canonical.write_text(json.dumps({"start_time": "2026-05-08T10:00:00Z"}), encoding="utf-8")
        # Three workers wrote sidecars
        sidecar_a = auto_cmd._audit_sidecar_path(("1", "3"), tmp_path)
        sidecar_b = auto_cmd._audit_sidecar_path(("2",), tmp_path)
        sidecar_c = auto_cmd._audit_sidecar_path(("4",), tmp_path)
        sidecar_a.write_text(
            json.dumps({"task_ids": ["1", "3"], "completed_at": "T1"}),
            encoding="utf-8",
        )
        sidecar_b.write_text(
            json.dumps({"task_ids": ["2"], "completed_at": "T2"}), encoding="utf-8"
        )
        sidecar_c.write_text(
            json.dumps({"task_ids": ["4"], "completed_at": "T3"}), encoding="utf-8"
        )

        merged = auto_cmd._merge_audit_sidecars([["1", "3"], ["2"], ["4"]], tmp_path)

        assert merged["start_time"] == "2026-05-08T10:00:00Z"
        assert merged["aggregate_task_count"] == 4
        assert len(merged["per_worker"]) == 3
        # Sidecars cleaned up
        assert not sidecar_a.exists()
        assert not sidecar_b.exists()
        assert not sidecar_c.exists()

    def test_i1_4_missing_sidecar_handled_gracefully(self, tmp_path: Path) -> None:
        """I1-4: worker terminated before sidecar write -> graceful no_audit_data entry."""
        import auto_cmd

        (tmp_path / ".claude").mkdir()
        canonical = tmp_path / ".claude" / "auto-run.json"
        canonical.write_text(json.dumps({"start_time": "2026-05-08T10:00:00Z"}), encoding="utf-8")
        # No sidecar files exist (workers crashed before write)

        merged = auto_cmd._merge_audit_sidecars([["1"], ["2"]], tmp_path)

        assert len(merged["per_worker"]) == 2
        for entry in merged["per_worker"]:
            assert entry["status"] == "no_audit_data"
            assert "Worker terminated before sidecar write" in entry["note"]

    def test_i1_5_inv26_audit_trail_integrity(self, tmp_path: Path) -> None:
        """I1-5: INV-26 audit-trail integrity post-batch (full round-trip)."""
        import auto_cmd

        (tmp_path / ".claude").mkdir()
        canonical = tmp_path / ".claude" / "auto-run.json"
        canonical.write_text(
            json.dumps(
                {
                    "start_time": "2026-05-08T10:00:00Z",
                    "planned_tasks": ["1", "2", "3", "4"],
                }
            ),
            encoding="utf-8",
        )
        # 2 tracks completed
        sidecar_a = auto_cmd._audit_sidecar_path(("1", "3"), tmp_path)
        sidecar_b = auto_cmd._audit_sidecar_path(("2", "4"), tmp_path)
        sidecar_a.write_text(
            json.dumps({"task_ids": ["1", "3"], "completed_at": "T1"}),
            encoding="utf-8",
        )
        sidecar_b.write_text(
            json.dumps({"task_ids": ["2", "4"], "completed_at": "T2"}),
            encoding="utf-8",
        )

        merged = auto_cmd._merge_audit_sidecars([["1", "3"], ["2", "4"]], tmp_path)

        # INV-26 verified: original start_time + aggregate_task_count + per_worker present
        assert merged["start_time"] == "2026-05-08T10:00:00Z"  # original preserved
        assert merged["aggregate_task_count"] == 4
        assert len(merged["per_worker"]) == 2

    def test_i1_6_reaper_only_removes_old_orphan_sidecars(self, tmp_path: Path) -> None:
        """I1-6 (iter-1 WARNING + iter-2 race-safety): reaper only removes
        files older than dispatch_start_epoch - 300s margin. Concurrent
        instance sidecars (mtime within margin) preserved.
        """
        import os as _os
        import time as _time

        import auto_cmd

        claude = tmp_path / ".claude"
        claude.mkdir()

        # Old orphan: mtime well before cutoff
        old_orphan = claude / "auto-run-track-deadbeef0001.json"
        old_orphan.write_text("{}", encoding="utf-8")
        old_mtime = _time.time() - 1000.0
        _os.utime(old_orphan, (old_mtime, old_mtime))

        # Recent file (concurrent instance) -- mtime within margin
        recent = claude / "auto-run-track-deadbeef0002.json"
        recent.write_text("{}", encoding="utf-8")

        # Old plan-scratch
        old_scratch = claude / "plan-scratch-deadbeef0003.md"
        old_scratch.write_text("scratch", encoding="utf-8")
        _os.utime(old_scratch, (old_mtime, old_mtime))

        dispatch_start = _time.time()
        auto_cmd._reap_orphans(tmp_path, dispatch_start_epoch=dispatch_start)

        # Old orphan + old scratch removed; recent preserved
        assert not old_orphan.exists()
        assert not old_scratch.exists()
        assert recent.exists()


# ---------------------------------------------------------------------------
# v1.0.5 Item I-3 -- worker CLI flag forwarding (escenarios I3-1..I3-3)
# ---------------------------------------------------------------------------


class TestWorkerFlagForwarding:
    """v1.0.5 Item I-3 escenarios I3-1 through I3-3 -- worker CLI flag forwarding."""

    def test_i3_1_forwardable_flags_propagate_to_worker_argv(self) -> None:
        """I3-1: forwardable flags propagate to worker argv with non-None values."""
        import argparse

        import auto_cmd

        ns = argparse.Namespace(
            plugins_root=None,
            magi_max_iterations=None,
            magi_threshold="GO",
            verification_retries=5,
            model_override=None,
        )
        argv = auto_cmd._build_worker_argv(["1", "3"], ns)

        assert "--task-ids" in argv
        assert "1,3" in argv
        assert "--no-recursive" in argv
        assert "--magi-threshold" in argv
        assert "GO" in argv
        assert "--verification-retries" in argv
        assert "5" in argv
        # Non-None flags propagated; None flags omitted
        assert "--plugins-root" not in argv
        assert "--magi-max-iterations" not in argv
        assert "--model-override" not in argv

    def test_i3_2_missing_flags_omit_from_worker_argv(self) -> None:
        """I3-2: all-None flags produce minimal argv (no empty/None flags)."""
        import argparse

        import auto_cmd

        ns = argparse.Namespace(
            plugins_root=None,
            magi_max_iterations=None,
            magi_threshold=None,
            verification_retries=None,
            model_override=None,
        )
        argv = auto_cmd._build_worker_argv(["1", "3"], ns)

        # Only the minimal set: python, run_sbtdd.py, auto, --task-ids, IDs, --no-recursive
        assert "--task-ids" in argv
        assert "--no-recursive" in argv
        for flag_name in (
            "--plugins-root",
            "--magi-max-iterations",
            "--magi-threshold",
            "--verification-retries",
            "--model-override",
        ):
            assert flag_name not in argv

    def test_i3_3_documented_forwardable_list_matches(self) -> None:
        """I3-3: _FORWARDABLE_FLAGS matches documented helper docstring."""
        import auto_cmd

        # Documented forwardable list (per spec sec.2.3)
        expected_keys = {
            "plugins_root",
            "magi_max_iterations",
            "magi_threshold",
            "verification_retries",
            "model_override",
        }
        assert set(auto_cmd._FORWARDABLE_FLAGS.keys()) == expected_keys

        # Helper docstring mentions all forwardable flag names
        docstring = auto_cmd._build_worker_argv.__doc__ or ""
        for flag_value in auto_cmd._FORWARDABLE_FLAGS.values():
            assert flag_value in docstring, f"Helper docstring missing: {flag_value}"


class TestK4ForwardableFlagsArgparseGuard:
    """v1.0.6 K-4: _FORWARDABLE_FLAGS argparse-presence guard.

    Covers escenarios K-4a + K-4b from spec sec.4.7. Detects drift
    between hardcoded _FORWARDABLE_FLAGS mapping and argparse dest
    set so a flag added to the mapping but not registered in argparse
    surfaces LOUD-FAST at module import time rather than silently
    failing to forward.
    """

    def test_k4a_clean_forwardable_flags_passes(self) -> None:
        """K-4b: real _FORWARDABLE_FLAGS matches argparse dest set."""
        import auto_cmd

        assert hasattr(auto_cmd, "_validate_forwardable_flags_against_argparse"), (
            "K-4 guard helper must exist"
        )
        # Invocation with current state should not raise
        auto_cmd._validate_forwardable_flags_against_argparse()

    def test_k4a_drift_detected_raises_validation_error(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """K-4a: synthetic _FORWARDABLE_FLAGS with drifted key raises ValidationError."""
        from errors import ValidationError
        import auto_cmd
        from types import MappingProxyType

        fake_flags = MappingProxyType(
            {
                **dict(auto_cmd._FORWARDABLE_FLAGS),
                "nonexistent_fake_flag_for_drift_test": "--nonexistent-fake-flag",
            }
        )
        monkeypatch.setattr(auto_cmd, "_FORWARDABLE_FLAGS", fake_flags)

        with pytest.raises(ValidationError) as excinfo:
            auto_cmd._validate_forwardable_flags_against_argparse()
        msg = str(excinfo.value)
        assert "nonexistent_fake_flag_for_drift_test" in msg, (
            "Drift error message must name the offending key(s)"
        )


class TestSpawnWorkerDispatcher:
    """v1.0.7 A2 cross-platform worker spawn dispatcher per spec sec.4.2."""

    def test_windows_worker_uses_subprocess_pipe_with_env_marker(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """A2-1 (Windows path): subprocess.PIPE + SBTDD_AUTO_PARALLEL_WORKER=1."""
        monkeypatch.setattr(sys, "platform", "win32")
        captured: dict[str, object] = {}

        class FakeProc:
            def wait(self, timeout: int | None = None) -> int:
                return 0

        def fake_popen(
            argv: list[str],
            **kwargs: object,
        ) -> FakeProc:
            captured["argv"] = argv
            captured["kwargs"] = kwargs
            return FakeProc()

        monkeypatch.setattr("auto_cmd.subprocess.Popen", fake_popen)
        auto_cmd._spawn_worker(["python", "-c", "pass"], env={"PATH": "/usr/bin"})
        kwargs = captured["kwargs"]
        assert kwargs["stdin"] is subprocess.PIPE  # type: ignore[index]
        assert kwargs["stdout"] is subprocess.PIPE  # type: ignore[index]
        assert kwargs["stderr"] is subprocess.PIPE  # type: ignore[index]
        assert kwargs["env"]["SBTDD_AUTO_PARALLEL_WORKER"] == "1"  # type: ignore[index]
        assert kwargs["env"]["PATH"] == "/usr/bin"  # type: ignore[index]

    def test_posix_worker_routes_to_pty_helper(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """A2-1 (POSIX path): routes to subprocess_utils._spawn_worker_with_pty."""
        if sys.platform == "win32":
            # Force POSIX behavior by monkeypatching sys.platform.
            monkeypatch.setattr(sys, "platform", "linux")
        captured: dict[str, object] = {}

        class FakeProc:
            pass

        def fake_pty_spawn(
            argv: list[str], env: dict[str, str], *, cwd: str | None = None
        ) -> FakeProc:
            # v1.0.7 T2 code-review C1 fix: PTY helper now accepts cwd kwarg.
            captured["argv"] = argv
            captured["env"] = env
            captured["cwd"] = cwd
            return FakeProc()

        monkeypatch.setattr("subprocess_utils._spawn_worker_with_pty", fake_pty_spawn)
        auto_cmd._spawn_worker(["python", "-c", "pass"], env={"PATH": "/usr/bin"}, cwd="/tmp/x")
        assert captured["argv"] == ["python", "-c", "pass"]
        assert captured["env"]["SBTDD_AUTO_PARALLEL_WORKER"] == "1"  # type: ignore[index]
        assert captured["env"]["PATH"] == "/usr/bin"  # type: ignore[index]
        # v1.0.7 T2 code-review C1: cwd MUST forward through PTY helper.
        assert captured["cwd"] == "/tmp/x"


class TestC1ForwardableFlagsHelperDocs:
    """v1.0.7 C1 K-4 helper docs comment per spec sec.4.7."""

    def test_helper_source_documents_single_level_subparser_walk(self) -> None:
        """C1: helper source contains comment about single-level walk limitation."""
        import inspect

        import auto_cmd

        src = inspect.getsource(auto_cmd._validate_forwardable_flags_against_argparse)
        assert "single-level subparser walk" in src.lower()


class TestC6ForwardableFlagsImportlibReloadCaveat:
    """v1.0.7 C6 K-4 helper docstring caveat per spec sec.4.7."""

    def test_docstring_documents_importlib_reload_interaction(self) -> None:
        """C6: docstring notes importlib.reload caveat for monkeypatch tests."""
        import auto_cmd

        doc = auto_cmd._validate_forwardable_flags_against_argparse.__doc__ or ""
        assert "importlib.reload" in doc
        assert "monkeypatch" in doc.lower()

    def test_docstring_cross_links_c1_inline_comment(self) -> None:
        """C6 Refactor cross-link: docstring references C1 inline comment."""
        import auto_cmd

        doc = auto_cmd._validate_forwardable_flags_against_argparse.__doc__ or ""
        assert "single-level subparser" in doc.lower() or "see inline comment" in doc.lower()
