# Author: Julian Bolivar
# Version: 1.0.0
# Date: 2026-04-24
"""Tests for H6 -- ``auto_cmd._phase2_task_loop`` spec-reviewer gate.

Feature B (v0.2, INV-31) integration: before ``close_task_cmd.mark_and_advance``
flips the plan checkbox and advances state, auto must consult
``spec_review_dispatch.dispatch_spec_reviewer``. Approval (``SpecReviewResult``
returned) proceeds to the advance. A :class:`SpecReviewError` raise aborts the
loop with an audit entry recording ``error="SpecReviewError"`` so the user sees
why the run stopped without having to grep commits.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any

import pytest

from tests.fixtures.skill_stubs import StubSpecReviewer


# ---------------------------------------------------------------------------
# Environment seeding helpers (parallel to ``tests/test_auto_cmd.py``).
# ---------------------------------------------------------------------------


def _seed_plugin_local(tmp_path: Path) -> None:
    import shutil

    (tmp_path / ".claude").mkdir(exist_ok=True)
    fixture = Path(__file__).parent / "fixtures" / "plugin-locals" / "valid-python.md"
    shutil.copy(fixture, tmp_path / ".claude" / "plugin.local.md")


def _seed_state(
    tmp_path: Path,
    *,
    current_phase: str = "red",
    current_task_id: str | None = "1",
    current_task_title: str | None = "First task",
    plan_approved_at: str | None = "2026-04-20T03:30:00Z",
) -> Path:
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
    state_path.write_text(json.dumps(state), encoding="utf-8")
    return state_path


def _setup_git_repo(tmp_path: Path) -> None:
    subprocess.run(["git", "init", "-q"], cwd=str(tmp_path), check=True, capture_output=True)
    for cfg in (
        ("user.email", "tester@example.com"),
        ("user.name", "Tester"),
        ("commit.gpgsign", "false"),
    ):
        subprocess.run(["git", "config", *cfg], cwd=str(tmp_path), check=True, capture_output=True)
    (tmp_path / "README.md").write_text("initial\n", encoding="utf-8")
    subprocess.run(["git", "add", "README.md"], cwd=str(tmp_path), check=True, capture_output=True)
    subprocess.run(
        ["git", "commit", "-m", "chore: initial"],
        cwd=str(tmp_path),
        check=True,
        capture_output=True,
    )


def _seed_plan(tmp_path: Path, task_count: int) -> Path:
    planning = tmp_path / "planning"
    planning.mkdir(parents=True, exist_ok=True)
    plan = planning / "claude-plan-tdd.md"
    body = "# Plan\n\n"
    for i in range(1, task_count + 1):
        body += f"### Task {i}: Task {i} title\n- [ ] step 1\n\n"
    plan.write_text(body, encoding="utf-8")
    return plan


def _seed_auto_env(
    tmp_path: Path,
    *,
    task_count: int = 1,
    task_id: str = "1",
    current_phase: str = "red",
) -> None:
    _setup_git_repo(tmp_path)
    _seed_plugin_local(tmp_path)
    _seed_plan(tmp_path, task_count)
    _seed_state(
        tmp_path,
        current_phase=current_phase,
        current_task_id=task_id,
        current_task_title=f"Task {task_id} title",
    )


def _install_auto_loop_patches(
    monkeypatch: pytest.MonkeyPatch,
    auto_cmd_mod: Any,
    superpowers_dispatch_mod: Any,
) -> None:
    """Patch the noisy dependencies so tests focus on the reviewer gate."""
    monkeypatch.setattr(
        superpowers_dispatch_mod,
        "test_driven_development",
        lambda **kw: None,
        raising=False,
    )
    monkeypatch.setattr(
        superpowers_dispatch_mod,
        "verification_before_completion",
        lambda **kw: None,
        raising=False,
    )
    monkeypatch.setattr(
        superpowers_dispatch_mod,
        "systematic_debugging",
        lambda **kw: None,
        raising=False,
    )
    monkeypatch.setattr(auto_cmd_mod, "detect_drift", lambda *a, **kw: None, raising=False)


# ---------------------------------------------------------------------------
# Happy path -- reviewer called once per task, auto advances normally.
# ---------------------------------------------------------------------------


def test_auto_phase2_invokes_spec_reviewer_per_task(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Three-task plan, all approvals -> reviewer called 3 times, all tasks close."""
    import auto_cmd
    import spec_review_dispatch
    import superpowers_dispatch
    from config import load_plugin_local
    from state_file import load as load_state

    _seed_auto_env(tmp_path, task_count=3, task_id="1", current_phase="red")
    cfg = load_plugin_local(tmp_path / ".claude" / "plugin.local.md")

    _install_auto_loop_patches(monkeypatch, auto_cmd, superpowers_dispatch)

    stub = StubSpecReviewer(sequence=[True, True, True])
    monkeypatch.setattr(
        spec_review_dispatch,
        "dispatch_spec_reviewer",
        stub.dispatch_spec_reviewer,
    )

    ns = auto_cmd._build_parser().parse_args(["--project-root", str(tmp_path)])
    state = load_state(tmp_path / ".claude" / "session-state.json")
    final = auto_cmd._phase2_task_loop(ns, state, cfg)

    assert final.current_phase == "done"
    assert final.current_task_id is None
    assert len(stub.calls) == 3
    assert [c["task_id"] for c in stub.calls] == ["1", "2", "3"]


def test_auto_phase2_reviewer_receives_plan_and_repo_paths(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Reviewer dispatch kwargs resolve ``plan_path`` and ``repo_root`` from state."""
    import auto_cmd
    import spec_review_dispatch
    import superpowers_dispatch
    from config import load_plugin_local
    from spec_review_dispatch import SpecReviewResult
    from state_file import load as load_state

    _seed_auto_env(tmp_path, task_count=1, task_id="1", current_phase="red")
    cfg = load_plugin_local(tmp_path / ".claude" / "plugin.local.md")

    _install_auto_loop_patches(monkeypatch, auto_cmd, superpowers_dispatch)

    observed: dict[str, Any] = {}

    def fake_dispatch(
        *,
        task_id: str,
        plan_path: Path,
        repo_root: Path,
        max_iterations: int = 3,
        timeout: int = 900,
        model: str | None = None,
        skill_field_name: str = "spec_reviewer_model",
        stream_prefix: str | None = None,
    ) -> SpecReviewResult:
        # iter 2 finding #1 + #7: accept stream_prefix kwarg threaded by
        # _run_spec_review_gate (production wiring of streaming).
        observed["task_id"] = task_id
        observed["plan_path"] = plan_path
        observed["repo_root"] = repo_root
        observed["stream_prefix"] = stream_prefix
        return SpecReviewResult(approved=True, issues=(), reviewer_iter=1, artifact_path=None)

    monkeypatch.setattr(spec_review_dispatch, "dispatch_spec_reviewer", fake_dispatch)

    ns = auto_cmd._build_parser().parse_args(["--project-root", str(tmp_path)])
    state = load_state(tmp_path / ".claude" / "session-state.json")
    auto_cmd._phase2_task_loop(ns, state, cfg)

    assert observed["task_id"] == "1"
    assert Path(observed["plan_path"]) == tmp_path / "planning" / "claude-plan-tdd.md"
    assert Path(observed["repo_root"]) == tmp_path


def test_auto_phase2_reviewer_runs_before_mark_and_advance(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Reviewer must fire BEFORE ``close_task_cmd.mark_and_advance`` flips state."""
    import auto_cmd
    import close_task_cmd
    import spec_review_dispatch
    import superpowers_dispatch
    from config import load_plugin_local
    from spec_review_dispatch import SpecReviewResult
    from state_file import load as load_state

    _seed_auto_env(tmp_path, task_count=1, task_id="1", current_phase="red")
    cfg = load_plugin_local(tmp_path / ".claude" / "plugin.local.md")

    _install_auto_loop_patches(monkeypatch, auto_cmd, superpowers_dispatch)

    events: list[str] = []

    def fake_dispatch(**kwargs: Any) -> SpecReviewResult:
        events.append("review")
        return SpecReviewResult(approved=True, issues=(), reviewer_iter=1, artifact_path=None)

    original_mark_and_advance = close_task_cmd.mark_and_advance

    def spy_mark_and_advance(state: Any, root: Path) -> Any:
        events.append("mark_and_advance")
        return original_mark_and_advance(state, root)

    monkeypatch.setattr(spec_review_dispatch, "dispatch_spec_reviewer", fake_dispatch)
    monkeypatch.setattr(close_task_cmd, "mark_and_advance", spy_mark_and_advance)

    ns = auto_cmd._build_parser().parse_args(["--project-root", str(tmp_path)])
    state = load_state(tmp_path / ".claude" / "session-state.json")
    auto_cmd._phase2_task_loop(ns, state, cfg)

    assert events == ["review", "mark_and_advance"], (
        f"reviewer gate must precede advance, observed: {events}"
    )


# ---------------------------------------------------------------------------
# Failure path -- SpecReviewError aborts the loop with audit trail.
# ---------------------------------------------------------------------------


@pytest.mark.slow
def test_auto_phase2_spec_review_error_writes_audit_and_propagates(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """SpecReviewError from dispatcher -> audit records error + raise propagates.

    Marked ``@pytest.mark.slow`` (wall-clock ~30s on baseline hardware): the
    test exercises the full ``_phase2_task_loop`` failure path including
    SpecReviewError audit + propagation. CI may opt out via
    ``pytest -m 'not slow'``; default ``make verify`` runs all.
    """
    import auto_cmd
    import close_task_cmd
    import spec_review_dispatch
    import superpowers_dispatch
    from config import load_plugin_local
    from errors import SpecReviewError
    from state_file import load as load_state

    _seed_auto_env(tmp_path, task_count=1, task_id="1", current_phase="red")
    cfg = load_plugin_local(tmp_path / ".claude" / "plugin.local.md")

    _install_auto_loop_patches(monkeypatch, auto_cmd, superpowers_dispatch)

    def failing_dispatch(**kwargs: Any) -> Any:
        raise SpecReviewError(
            "spec-reviewer safety valve exhausted for task 1",
            task_id="1",
            iteration=3,
            issues=("stub finding",),
        )

    monkeypatch.setattr(spec_review_dispatch, "dispatch_spec_reviewer", failing_dispatch)

    # mark_and_advance must NOT run when reviewer raises.
    advance_calls = {"n": 0}

    def never_advance(state: Any, root: Path) -> Any:
        advance_calls["n"] += 1
        raise AssertionError("mark_and_advance must not run on SpecReviewError")

    monkeypatch.setattr(close_task_cmd, "mark_and_advance", never_advance)

    ns = auto_cmd._build_parser().parse_args(["--project-root", str(tmp_path)])
    state = load_state(tmp_path / ".claude" / "session-state.json")

    with pytest.raises(SpecReviewError):
        auto_cmd._phase2_task_loop(ns, state, cfg)

    assert advance_calls["n"] == 0
    audit_path = tmp_path / ".claude" / "auto-run.json"
    assert audit_path.exists(), "audit artifact must be written on SpecReviewError"
    audit = json.loads(audit_path.read_text(encoding="utf-8"))
    assert audit["error"] == "SpecReviewError"
    assert audit["status"] != "success"
    assert audit["tasks_completed"] == 0


@pytest.mark.slow
def test_auto_phase2_spec_review_error_mid_plan_records_completed_tasks(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Two tasks approved, third raises -> audit shows tasks_completed=2.

    Marked ``@pytest.mark.slow`` (wall-clock ~18s on baseline hardware): the
    test exercises the full ``_phase2_task_loop`` mid-plan failure path
    including reviewer success on N-1 tasks then SpecReviewError on task N.
    CI may opt out via ``pytest -m 'not slow'``; default ``make verify``
    runs all.
    """
    import auto_cmd
    import spec_review_dispatch
    import superpowers_dispatch
    from config import load_plugin_local
    from errors import SpecReviewError
    from spec_review_dispatch import SpecReviewResult
    from state_file import load as load_state

    _seed_auto_env(tmp_path, task_count=3, task_id="1", current_phase="red")
    cfg = load_plugin_local(tmp_path / ".claude" / "plugin.local.md")

    _install_auto_loop_patches(monkeypatch, auto_cmd, superpowers_dispatch)

    call_count = {"n": 0}

    def dispatch_two_pass_one_fail(**kwargs: Any) -> SpecReviewResult:
        call_count["n"] += 1
        if call_count["n"] <= 2:
            return SpecReviewResult(approved=True, issues=(), reviewer_iter=1, artifact_path=None)
        raise SpecReviewError(
            "spec-reviewer safety valve exhausted for task 3",
            task_id="3",
            iteration=3,
            issues=("stub finding",),
        )

    monkeypatch.setattr(spec_review_dispatch, "dispatch_spec_reviewer", dispatch_two_pass_one_fail)

    ns = auto_cmd._build_parser().parse_args(["--project-root", str(tmp_path)])
    state = load_state(tmp_path / ".claude" / "session-state.json")

    with pytest.raises(SpecReviewError):
        auto_cmd._phase2_task_loop(ns, state, cfg)

    audit = json.loads((tmp_path / ".claude" / "auto-run.json").read_text(encoding="utf-8"))
    assert audit["error"] == "SpecReviewError"
    assert audit["tasks_completed"] == 2


# ---------------------------------------------------------------------------
# Cost guardrail -- cumulative spec-review wall-time budget.
# ---------------------------------------------------------------------------


def test_auto_phase2_skips_reviewer_after_budget_exceeded(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Once the cumulative reviewer wall-time exceeds the configured budget,
    subsequent tasks must skip the dispatcher and continue normally.

    Setup: 3-task plan, budget tightened to 1 second via the parsed config.
    The first reviewer call sleeps long enough to exceed the budget; the
    next two tasks must NOT call the dispatcher and the breadcrumb must
    appear on stderr exactly once.
    """
    import time

    import auto_cmd
    import spec_review_dispatch
    import superpowers_dispatch
    from config import PluginConfig, load_plugin_local
    from spec_review_dispatch import SpecReviewResult
    from state_file import load as load_state

    _seed_auto_env(tmp_path, task_count=3, task_id="1", current_phase="red")
    base_cfg = load_plugin_local(tmp_path / ".claude" / "plugin.local.md")
    cfg = PluginConfig(
        **{**base_cfg.__dict__, "auto_max_spec_review_seconds": 1},
    )

    _install_auto_loop_patches(monkeypatch, auto_cmd, superpowers_dispatch)

    call_count = {"n": 0}

    def slow_then_fast(**kwargs: Any) -> SpecReviewResult:
        call_count["n"] += 1
        if call_count["n"] == 1:
            # First task spends > budget. Use a tiny sleep so the test
            # stays fast but monotonic delta crosses the 1s budget.
            time.sleep(1.05)
        return SpecReviewResult(approved=True, issues=(), reviewer_iter=1, artifact_path=None)

    monkeypatch.setattr(spec_review_dispatch, "dispatch_spec_reviewer", slow_then_fast)

    ns = auto_cmd._build_parser().parse_args(["--project-root", str(tmp_path)])
    state = load_state(tmp_path / ".claude" / "session-state.json")
    final = auto_cmd._phase2_task_loop(ns, state, cfg)

    assert final.current_phase == "done"
    assert final.current_task_id is None
    assert call_count["n"] == 1, (
        f"reviewer must run only for task 1 (call_count={call_count['n']});"
        " tasks 2 and 3 should skip after budget exhaustion"
    )
    err = capsys.readouterr().err
    assert "spec-review budget" in err and "exceeded" in err and "--skip-spec-review" in err, (
        f"expected breadcrumb on stderr, got: {err!r}"
    )
    # Breadcrumb emitted exactly once even though two tasks were skipped.
    assert err.count("spec-review budget") == 1


def test_auto_phase2_budget_not_exceeded_runs_reviewer_for_all(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """When the cumulative reviewer time stays under budget, no skip path
    triggers and no breadcrumb appears on stderr.
    """
    import auto_cmd
    import spec_review_dispatch
    import superpowers_dispatch
    from config import load_plugin_local
    from spec_review_dispatch import SpecReviewResult
    from state_file import load as load_state

    _seed_auto_env(tmp_path, task_count=2, task_id="1", current_phase="red")
    cfg = load_plugin_local(tmp_path / ".claude" / "plugin.local.md")  # default 3600s budget

    _install_auto_loop_patches(monkeypatch, auto_cmd, superpowers_dispatch)

    calls = {"n": 0}

    def fast_dispatch(**kwargs: Any) -> SpecReviewResult:
        calls["n"] += 1
        return SpecReviewResult(approved=True, issues=(), reviewer_iter=1, artifact_path=None)

    monkeypatch.setattr(spec_review_dispatch, "dispatch_spec_reviewer", fast_dispatch)

    ns = auto_cmd._build_parser().parse_args(["--project-root", str(tmp_path)])
    state = load_state(tmp_path / ".claude" / "session-state.json")
    auto_cmd._phase2_task_loop(ns, state, cfg)

    assert calls["n"] == 2
    err = capsys.readouterr().err
    assert "spec-review budget" not in err
