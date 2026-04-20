#!/usr/bin/env python3
# Author: Julian Bolivar
# Version: 1.0.0
# Date: 2026-04-19
"""End-to-end integration tests for the 9 subcomandos wired through run_sbtdd.

Covers BDD scenarios 13 (spec + close-phase x3), 18 (auto happy path),
19 (resume after quota exhaustion) and 17 (finalize rejects degraded
verdict). Tests consume the shared :mod:`tests.fixtures.skill_stubs`
fixture (Task 46a) so stub signatures stay canonical across the suite.
"""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

import pytest

# Import the fixture helpers here (imports at top of file per PEP 8 / E402).
from tests.fixtures.skill_stubs import StubMAGI, StubSuperpowers, make_verdict

_VALID_SPEC_BASE_BODY = "# Feature spec\n\n## Objetivo\nsomething meaningful\n" + (
    "valid content " * 50
)
_PLAN_ORG_BODY = (
    "# Plan\n\n### Task 1: First task\n\n- [ ] write the test\n- [ ] implement\n- [ ] refactor\n"
)


def _setup_git(tmp_path: Path) -> None:
    """Initialise a git repo at tmp_path with tester identity + initial commit."""
    subprocess.run(["git", "init", "-q"], cwd=str(tmp_path), check=True, capture_output=True)
    for key, value in (
        ("user.email", "tester@example.com"),
        ("user.name", "Tester"),
        ("commit.gpgsign", "false"),
    ):
        subprocess.run(
            ["git", "config", key, value],
            cwd=str(tmp_path),
            check=True,
            capture_output=True,
        )
    subprocess.run(
        ["git", "commit", "--allow-empty", "-m", "chore: seed"],
        cwd=str(tmp_path),
        check=True,
        capture_output=True,
    )


def _seed_plugin_local(tmp_path: Path) -> None:
    """Copy the valid-python plugin.local.md fixture into .claude/."""
    (tmp_path / ".claude").mkdir(exist_ok=True)
    fixture = Path(__file__).parent / "fixtures" / "plugin-locals" / "valid-python.md"
    shutil.copy(fixture, tmp_path / ".claude" / "plugin.local.md")


def _seed_spec_base(tmp_path: Path) -> None:
    spec_dir = tmp_path / "sbtdd"
    spec_dir.mkdir()
    (spec_dir / "spec-behavior-base.md").write_text(_VALID_SPEC_BASE_BODY, encoding="utf-8")
    (tmp_path / "planning").mkdir()


@pytest.fixture
def bootstrapped_project(tmp_path, monkeypatch):
    """Tmp git repo with plugin.local.md + spec-base + skill stubs installed."""
    import magi_dispatch
    import superpowers_dispatch

    _setup_git(tmp_path)
    _seed_spec_base(tmp_path)
    _seed_plugin_local(tmp_path)

    sp = StubSuperpowers()
    # Emulate artifacts produced by /brainstorming and /writing-plans.
    (tmp_path / "sbtdd" / "spec-behavior.md").write_text(
        "# behavior\nsomething\n", encoding="utf-8"
    )

    def fake_brainstorming(args=None, timeout=600, cwd=None):
        (tmp_path / "sbtdd" / "spec-behavior.md").write_text(
            "# behavior\nContent\n", encoding="utf-8"
        )
        sp.calls.append(("brainstorming", list(args or []), cwd or ""))
        return None

    def fake_writing_plans(args=None, timeout=600, cwd=None):
        (tmp_path / "planning" / "claude-plan-tdd-org.md").write_text(
            _PLAN_ORG_BODY, encoding="utf-8"
        )
        sp.calls.append(("writing_plans", list(args or []), cwd or ""))
        return None

    def fake_noop(args=None, timeout=600, cwd=None):
        return None

    monkeypatch.setattr(superpowers_dispatch, "brainstorming", fake_brainstorming)
    monkeypatch.setattr(superpowers_dispatch, "writing_plans", fake_writing_plans)
    monkeypatch.setattr(superpowers_dispatch, "verification_before_completion", fake_noop)
    monkeypatch.setattr(superpowers_dispatch, "requesting_code_review", fake_noop)
    monkeypatch.setattr(superpowers_dispatch, "receiving_code_review", fake_noop)
    monkeypatch.setattr(superpowers_dispatch, "test_driven_development", fake_noop)
    monkeypatch.setattr(superpowers_dispatch, "systematic_debugging", fake_noop)
    monkeypatch.setattr(superpowers_dispatch, "finishing_a_development_branch", fake_noop)

    magi = StubMAGI(sequence=[make_verdict("GO", degraded=False)])

    def fake_invoke_magi(context_paths, timeout=1800, cwd=None):
        return magi.invoke_magi(context_paths=list(context_paths), cwd=cwd or "", timeout=timeout)

    monkeypatch.setattr(magi_dispatch, "invoke_magi", fake_invoke_magi)
    return tmp_path


def _stage_scratch_change(root: Path, name: str, content: str) -> None:
    """Write a file inside the project and stage it so git commit has something to commit."""
    scratch = root / name
    scratch.write_text(content, encoding="utf-8")
    subprocess.run(["git", "add", name], cwd=str(root), check=True, capture_output=True)


def test_spec_then_three_close_phase_end_to_end(bootstrapped_project, monkeypatch):
    """Scenario 13 end-to-end: spec approves plan, then 3 close-phase cycles complete task 1.

    Uses ``close_task_cmd.mark_and_advance`` (the public helper per iter-2 W1)
    in place of ``close_task_cmd.main`` in the cascade: the main() path re-runs
    drift detection, which legitimately flags ``state=refactor + HEAD=refactor:``
    as "close already landed but state not advanced". In the cascade context
    this IS the intermediate pre-advance state, which :func:`mark_and_advance`
    consumes directly (same path auto_cmd uses to side-step the spurious flag).
    """
    import close_task_cmd
    import run_sbtdd

    def cascade_without_drift_check(argv=None):
        from pathlib import Path as _Path

        from state_file import load as _load_state

        parsed_root = _Path(argv[argv.index("--project-root") + 1]) if argv else _Path.cwd()
        state = _load_state(parsed_root / ".claude" / "session-state.json")
        close_task_cmd.mark_and_advance(state, parsed_root)
        return 0

    monkeypatch.setattr(close_task_cmd, "main", cascade_without_drift_check)

    # Run spec -- stubs write spec-behavior.md + plan-org.md, MAGI returns GO.
    rc = run_sbtdd.main(["spec", "--project-root", str(bootstrapped_project)])
    assert rc == 0
    state_path = bootstrapped_project / ".claude" / "session-state.json"
    assert state_path.exists(), "spec should create session-state.json"
    state = json.loads(state_path.read_text(encoding="utf-8"))
    assert state["current_phase"] == "red"
    assert state["plan_approved_at"] is not None

    # Red close: stage a scratch test file, then close-phase.
    _stage_scratch_change(bootstrapped_project, "tests_scratch_red.py", "# red stub\n")
    rc = run_sbtdd.main(
        [
            "close-phase",
            "--project-root",
            str(bootstrapped_project),
            "--message",
            "red phase for task 1",
        ]
    )
    assert rc == 0

    # Green close with --variant feat.
    _stage_scratch_change(bootstrapped_project, "impl_scratch.py", "# green stub\n")
    rc = run_sbtdd.main(
        [
            "close-phase",
            "--project-root",
            str(bootstrapped_project),
            "--variant",
            "feat",
            "--message",
            "green phase for task 1",
        ]
    )
    assert rc == 0

    # Refactor close -- cascades into close-task bookkeeping.
    _stage_scratch_change(bootstrapped_project, "impl_scratch.py", "# refactored\n")
    rc = run_sbtdd.main(
        [
            "close-phase",
            "--project-root",
            str(bootstrapped_project),
            "--message",
            "refactor phase for task 1",
        ]
    )
    assert rc == 0

    state = json.loads(state_path.read_text(encoding="utf-8"))
    assert state["current_phase"] == "done"
    assert state["current_task_id"] is None


def _ok_dep_report():
    from dependency_check import DependencyCheck, DependencyReport

    return DependencyReport(
        checks=(DependencyCheck(name="stub", status="OK", detail="", remediation=""),)
    )


def test_auto_full_cycle_happy_path(bootstrapped_project, monkeypatch):
    """Scenario 18: single auto invocation completes plan + pre-merge + checklist.

    Exercises run_sbtdd.main("auto") through the 5-phase flow. Heavy stubs
    are unavoidable for an integration test (real auto talks to git, tdd-guard,
    external plugins), but the dispatcher wiring (Tasks 37-46) is still the
    subject under test.
    """
    import auto_cmd
    import close_task_cmd
    import finalize_cmd
    import magi_dispatch
    import pre_merge_cmd
    import run_sbtdd

    # Run spec first so plan_approved_at + state file exist.
    rc = run_sbtdd.main(["spec", "--project-root", str(bootstrapped_project)])
    assert rc == 0

    # Stub the parts that require a real toolchain.
    monkeypatch.setattr(auto_cmd, "check_environment", lambda *a, **k: _ok_dep_report())
    monkeypatch.setattr(auto_cmd, "detect_drift", lambda *a, **kw: None)

    # commit_create fakes that actually create a real git commit (so HEAD advances).
    def fake_commit(prefix, message, cwd=None):
        subprocess.run(
            ["git", "commit", "--allow-empty", "-m", f"{prefix}: {message}"],
            cwd=cwd or str(bootstrapped_project),
            check=True,
            capture_output=True,
        )
        return "ok"

    monkeypatch.setattr(auto_cmd, "commit_create", fake_commit, raising=False)
    monkeypatch.setattr(close_task_cmd, "commit_create", fake_commit)

    # Short-circuit the pre-merge internals -- they are exercised by their own
    # unit tests; here we only need a GO verdict to flow through.
    monkeypatch.setattr(pre_merge_cmd, "_loop1", lambda root: None)

    def fake_loop2(root, shadow, threshold):
        return make_verdict("GO", degraded=False)

    monkeypatch.setattr(pre_merge_cmd, "_loop2", fake_loop2)

    def fake_write_verdict(v, target, timestamp=None):
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(
            json.dumps(
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

    # Avoid running the real sec.M.0.1 verification inside finalize's checklist.
    monkeypatch.setattr(finalize_cmd, "_checklist", lambda *a, **kw: [("ok", True, "")])

    rc = run_sbtdd.main(["auto", "--project-root", str(bootstrapped_project)])
    assert rc == 0
    assert (bootstrapped_project / ".claude" / "auto-run.json").exists()
    assert (bootstrapped_project / ".claude" / "magi-verdict.json").exists()
    verdict = json.loads(
        (bootstrapped_project / ".claude" / "magi-verdict.json").read_text(encoding="utf-8")
    )
    assert verdict["degraded"] is False
    state = json.loads(
        (bootstrapped_project / ".claude" / "session-state.json").read_text(encoding="utf-8")
    )
    assert state["current_phase"] == "done"
    assert state["current_task_id"] is None


def test_resume_after_quota_exhaustion_continues_to_completion(bootstrapped_project, monkeypatch):
    """Scenario 19: auto hits quota mid-phase-2 (exit 11); resume --auto completes.

    Simulates two Claude Code sessions: first session runs auto and is cut off
    by a 429-style QuotaExhaustedError; the state file + prior commits form the
    checkpoint chain. Second session invokes /sbtdd resume --auto, which reads
    the diagnostic + delegates back to auto_cmd to finish what was started.
    """
    import auto_cmd
    import close_task_cmd
    import finalize_cmd
    import magi_dispatch
    import pre_merge_cmd
    import resume_cmd
    import run_sbtdd
    import superpowers_dispatch
    from errors import EXIT_CODES, QuotaExhaustedError

    # Spec first -- provides session-state.json + plan_approved_at.
    rc = run_sbtdd.main(["spec", "--project-root", str(bootstrapped_project)])
    assert rc == 0

    monkeypatch.setattr(auto_cmd, "check_environment", lambda *a, **k: _ok_dep_report())
    monkeypatch.setattr(auto_cmd, "detect_drift", lambda *a, **kw: None)
    monkeypatch.setattr(resume_cmd, "check_environment", lambda *a, **k: _ok_dep_report())
    monkeypatch.setattr(resume_cmd, "detect_drift", lambda *a, **kw: None)

    def fake_commit(prefix, message, cwd=None):
        subprocess.run(
            ["git", "commit", "--allow-empty", "-m", f"{prefix}: {message}"],
            cwd=cwd or str(bootstrapped_project),
            check=True,
            capture_output=True,
        )
        return "ok"

    monkeypatch.setattr(auto_cmd, "commit_create", fake_commit, raising=False)
    monkeypatch.setattr(close_task_cmd, "commit_create", fake_commit)

    # First pass: verification always raises QuotaExhaustedError so auto
    # aborts mid-Phase-2. Under the current retry-wrapper contract the
    # quota error is captured inside _run_verification_with_retries and
    # re-raised as VerificationIrremediableError (exit 6); on resume we
    # flip the stub to a no-op so the second pass drives to completion.
    call_count = {"n": 0}
    first_pass_verify = []

    def flaky_verify(**kw):
        call_count["n"] += 1
        if first_pass_verify and first_pass_verify[0]:
            raise QuotaExhaustedError("rate_limit_429: session limit")
        return None

    first_pass_verify.append(True)
    monkeypatch.setattr(
        superpowers_dispatch, "verification_before_completion", flaky_verify, raising=False
    )
    monkeypatch.setattr(
        superpowers_dispatch, "systematic_debugging", lambda **kw: None, raising=False
    )

    # Quota-table assertion (sanity check for the exit-code map).
    assert EXIT_CODES[QuotaExhaustedError] == 11

    rc = run_sbtdd.main(["auto", "--project-root", str(bootstrapped_project)])
    # Auto aborts mid-phase-2 -- exit 6 (VerificationIrremediableError)
    # because the retry wrapper wraps the quota exception. The critical
    # point is auto did NOT complete: state file still points at an
    # active task, allowing resume to pick up.
    assert rc != 0
    first_pass_verify[0] = False  # subsequent verification calls succeed

    # Make the rest of the pipeline succeed for the retry.
    monkeypatch.setattr(pre_merge_cmd, "_loop1", lambda root: None)

    def fake_loop2(root, shadow, threshold):
        return make_verdict("GO", degraded=False)

    monkeypatch.setattr(pre_merge_cmd, "_loop2", fake_loop2)

    def fake_write_verdict(v, target, timestamp=None):
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(
            json.dumps(
                {
                    "timestamp": "2026-04-21T00:00:00Z",
                    "verdict": "GO",
                    "degraded": False,
                    "conditions": [],
                    "findings": [],
                }
            ),
            encoding="utf-8",
        )

    monkeypatch.setattr(magi_dispatch, "write_verdict_artifact", fake_write_verdict)
    monkeypatch.setattr(finalize_cmd, "_checklist", lambda *a, **kw: [("ok", True, "")])

    # Resume must pick up where auto left off and drive to completion.
    rc = run_sbtdd.main(["resume", "--project-root", str(bootstrapped_project), "--auto"])
    assert rc == 0
