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
