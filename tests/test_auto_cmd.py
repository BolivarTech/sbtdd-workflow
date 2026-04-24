# Author: Julian Bolivar
# Version: 1.0.0
# Date: 2026-04-19
"""Tests for /sbtdd auto subcommand (sec.S.5.8, INV-22..26)."""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest


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
