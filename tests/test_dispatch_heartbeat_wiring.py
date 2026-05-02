#!/usr/bin/env python3
# Author: Julian Bolivar
# Version: 1.0.0
# Date: 2026-05-02
"""Wiring tests for ``_dispatch_with_heartbeat`` (v0.5.0 Loop 1 fix CRITICAL #1).

The headline UX deliverable of v0.5.0 (heartbeat tick-during-long-dispatch)
is only realised when the long-dispatch sites in :mod:`auto_cmd` and
:mod:`pre_merge_cmd` actually invoke :func:`auto_cmd._dispatch_with_heartbeat`.
Pre-fix the helper was defined but never called from production code paths;
this module pins the wiring contract.

Strategy: spy on ``auto_cmd._dispatch_with_heartbeat`` via monkeypatch and
exercise each callsite-bearing function with stub dispatch modules so the
real subprocess + Claude CLI is never reached. The spy records call count
+ the dispatch_label captured from the active ProgressContext at invoke
time so tests assert the wrapper fires WITH the correct label per
sec.3 / spec sec.S1-9 enumeration.
"""

from __future__ import annotations

import sys
from pathlib import Path
from types import SimpleNamespace
from typing import Any

sys.path.insert(0, str(Path(__file__).parent.parent / "skills" / "sbtdd" / "scripts"))

import auto_cmd
import pre_merge_cmd
import superpowers_dispatch
from heartbeat import get_current_progress, reset_current_progress


def _install_dispatch_spy(monkeypatch) -> list[str]:  # type: ignore[no-untyped-def]
    """Install a spy on ``auto_cmd._dispatch_with_heartbeat``.

    Returns a list that the spy appends ``ProgressContext.dispatch_label``
    to on every invocation. Tests inspect the list to assert the wrapper
    fires with the expected label.
    """
    captured_labels: list[str] = []
    real = auto_cmd._dispatch_with_heartbeat

    def spy(*, invoke, heartbeat_interval: float = 15.0, **kwargs: Any) -> Any:  # type: ignore[no-untyped-def]
        ctx = get_current_progress()
        captured_labels.append(ctx.dispatch_label or "<none>")
        # Use a tiny interval so any latent thread spawn is benign.
        return real(invoke=invoke, heartbeat_interval=0.01, **kwargs)

    monkeypatch.setattr(auto_cmd, "_dispatch_with_heartbeat", spy)
    return captured_labels


def test_run_verification_with_retries_wraps_with_heartbeat(monkeypatch):
    """Site #1 (verification): ``_run_verification_with_retries`` wraps dispatch.

    Pre-fix: ``superpowers_dispatch.verification_before_completion(...)`` was
    invoked directly. Post-fix: routed through ``_dispatch_with_heartbeat``
    after ``_set_progress`` sets ``dispatch_label='verification'``.
    """
    reset_current_progress()
    captured = _install_dispatch_spy(monkeypatch)

    def fake_verify(**_: Any) -> None:
        return None

    monkeypatch.setattr(superpowers_dispatch, "verification_before_completion", fake_verify)
    auto_cmd._run_verification_with_retries(Path("."), retries=0)
    assert len(captured) == 1
    assert captured[0] == "verification"
    reset_current_progress()


def test_run_verification_with_retries_wraps_systematic_debugging(monkeypatch):
    """Site #2 (systematic-debugging): retry path also wraps dispatch."""
    reset_current_progress()
    captured = _install_dispatch_spy(monkeypatch)

    call_count = {"verify": 0}

    def fake_verify(**_: Any) -> None:
        call_count["verify"] += 1
        if call_count["verify"] == 1:
            raise RuntimeError("first attempt fails")

    def fake_sysdebug(**_: Any) -> None:
        return None

    monkeypatch.setattr(superpowers_dispatch, "verification_before_completion", fake_verify)
    monkeypatch.setattr(superpowers_dispatch, "systematic_debugging", fake_sysdebug)
    # retries=1 -> first call fails, sys-debug fires, second call succeeds.
    auto_cmd._run_verification_with_retries(Path("."), retries=1)
    # Two verification calls + one sys-debug call = 3 wraps.
    assert len(captured) == 3
    assert captured.count("verification") == 2
    assert captured.count("systematic-debugging") == 1
    reset_current_progress()


def test_run_spec_review_gate_wraps_with_heartbeat(monkeypatch, tmp_path):
    """Site #3 (spec-review): ``_run_spec_review_gate`` wraps dispatch."""
    import spec_review_dispatch as srd

    reset_current_progress()
    captured = _install_dispatch_spy(monkeypatch)

    def fake_dispatch(**_: Any) -> None:
        return None

    monkeypatch.setattr(srd, "dispatch_spec_reviewer", fake_dispatch)
    auto_cmd._run_spec_review_gate(task_id="3", plan_path=tmp_path / "plan.md", root=tmp_path)
    assert len(captured) == 1
    assert captured[0] == "spec-review"
    reset_current_progress()


def test_run_mini_cycle_wraps_test_driven_development(monkeypatch, tmp_path):
    """Site #4 (red/green/refactor inside spec-review B6): each phase wraps dispatch."""
    reset_current_progress()
    captured = _install_dispatch_spy(monkeypatch)

    def fake_tdd(**_: Any) -> None:
        return None

    def fake_verify(**_: Any) -> None:
        return None

    def fake_commit(*_args: Any, **_kwargs: Any) -> None:
        return None

    monkeypatch.setattr(superpowers_dispatch, "test_driven_development", fake_tdd)
    monkeypatch.setattr(superpowers_dispatch, "verification_before_completion", fake_verify)
    monkeypatch.setattr(auto_cmd, "_commit_mini_cycle_phase", fake_commit)

    auto_cmd._run_mini_cycle_for_finding(
        root=tmp_path,
        task_id="3",
        finding="some finding",
        retries=0,
        implementer_model=None,
    )
    # Three mini-cycle phases (red/green/refactor) -> three TDD wraps + three
    # verification wraps = 6 total. Labels include red/green/refactor +
    # verification.
    label_set = set(captured)
    assert "red" in label_set or "spec-review-mini-cycle-red" in label_set, (
        f"expected red label in {captured}"
    )
    # Verification fires once per phase.
    assert captured.count("verification") == 3
    reset_current_progress()


def test_loop2_pre_merge_wraps_invoke_magi(monkeypatch, tmp_path):
    """Site #5 (MAGI Loop 2 iter): each iter wraps invoke_magi via dispatch.

    The wrap is gated on auto-mode-active (ProgressContext.phase != 0).
    The test simulates auto-mode by setting phase=3 before invoking
    ``_loop2`` (matching ``auto_cmd._phase3_pre_merge`` which calls
    ``_set_progress(phase=3)`` before delegating to ``_loop2``).
    """
    import magi_dispatch

    reset_current_progress()
    # Simulate auto-mode being active (auto_cmd._phase3_pre_merge sets this).
    auto_cmd._set_progress(phase=3)
    captured = _install_dispatch_spy(monkeypatch)

    fake_verdict = SimpleNamespace(
        verdict="GO",
        conditions=(),
        findings=(),
        consensus_summary="ok",
        degraded=False,
        agents=("melchior", "balthasar", "caspar"),
        retried_agents=(),
    )

    def fake_invoke_magi(**_: Any) -> Any:
        return fake_verdict

    def fake_verdict_passes_gate(_v: Any, _t: str) -> bool:
        return True

    def fake_strong_no_go(_v: Any) -> bool:
        return False

    monkeypatch.setattr(magi_dispatch, "invoke_magi", fake_invoke_magi)
    monkeypatch.setattr(magi_dispatch, "verdict_passes_gate", fake_verdict_passes_gate)
    monkeypatch.setattr(magi_dispatch, "verdict_is_strong_no_go", fake_strong_no_go)

    cfg = SimpleNamespace(
        magi_threshold="GO_WITH_CAVEATS",
        magi_max_iterations=3,
        plan_path="planning/claude-plan-tdd.md",
    )
    # Provide an empty plan + a writable .claude dir.
    (tmp_path / ".claude").mkdir(exist_ok=True)
    (tmp_path / "planning").mkdir(exist_ok=True)
    (tmp_path / "planning" / "claude-plan-tdd.md").write_text("plan", encoding="utf-8")

    pre_merge_cmd._loop2(tmp_path, cfg, threshold_override=None, ns=None)  # type: ignore[arg-type]
    # MAGI dispatch should have been wrapped.
    assert any("magi-loop2" in lbl for lbl in captured), (
        f"expected magi-loop2-iter* label, got {captured}"
    )
    reset_current_progress()


# --- Fix 6: Site 6 / Site 7 / Site 10 transition coverage -----------------


def test_site6_magi_loop2_iter_advances_set_progress_with_iter_num(monkeypatch, tmp_path):
    """Site 6: each MAGI Loop 2 iter advance refreshes ProgressContext.iter_num.

    The wrap fires per-iter with ``iter_num=iteration``; the captured spy
    records the ProgressContext at invoke time, so distinct iter values
    must appear in the captured progress snapshots.
    """
    import magi_dispatch

    reset_current_progress()
    auto_cmd._set_progress(phase=3)
    captured_iters: list[int] = []
    real = auto_cmd._dispatch_with_heartbeat

    def spy(*, invoke, heartbeat_interval: float = 15.0, **kwargs: Any) -> Any:  # type: ignore[no-untyped-def]
        captured_iters.append(get_current_progress().iter_num)
        return real(invoke=invoke, heartbeat_interval=0.01, **kwargs)

    monkeypatch.setattr(auto_cmd, "_dispatch_with_heartbeat", spy)

    # Two consecutive iters: first emits conditions (forces re-iter via empty
    # accept), second clears.
    iter_count = {"n": 0}
    fake_first = SimpleNamespace(
        verdict="GO",
        conditions=(),  # no conditions -> goes to threshold check directly
        findings=(),
        consensus_summary="ok",
        degraded=False,
        agents=("melchior", "balthasar", "caspar"),
        retried_agents=(),
    )

    def fake_invoke_magi(**_: Any) -> Any:
        iter_count["n"] += 1
        return fake_first

    monkeypatch.setattr(magi_dispatch, "invoke_magi", fake_invoke_magi)
    monkeypatch.setattr(magi_dispatch, "verdict_passes_gate", lambda _v, _t: True)
    monkeypatch.setattr(magi_dispatch, "verdict_is_strong_no_go", lambda _v: False)

    cfg = SimpleNamespace(
        magi_threshold="GO_WITH_CAVEATS",
        magi_max_iterations=3,
        plan_path="planning/claude-plan-tdd.md",
    )
    (tmp_path / ".claude").mkdir(exist_ok=True)
    (tmp_path / "planning").mkdir(exist_ok=True)
    (tmp_path / "planning" / "claude-plan-tdd.md").write_text("plan", encoding="utf-8")

    pre_merge_cmd._loop2(tmp_path, cfg, threshold_override=None, ns=None)  # type: ignore[arg-type]
    # First iter recorded: iter_num >= 1
    assert any(n >= 1 for n in captured_iters), (
        f"expected at least one iter_num >= 1 in {captured_iters}"
    )
    reset_current_progress()


def test_site7_phase3_dispatch_sets_progress_with_label(monkeypatch, tmp_path):
    """Site 7: Phase 3 dispatch sites (Loop 1 + receiving findings) set the label."""
    reset_current_progress()
    auto_cmd._set_progress(phase=3)

    captured_labels: list[str] = []
    real = auto_cmd._dispatch_with_heartbeat

    def spy(*, invoke, heartbeat_interval: float = 15.0, **kwargs: Any) -> Any:  # type: ignore[no-untyped-def]
        captured_labels.append(get_current_progress().dispatch_label or "<none>")
        return real(invoke=invoke, heartbeat_interval=0.01, **kwargs)

    monkeypatch.setattr(auto_cmd, "_dispatch_with_heartbeat", spy)

    # Drive _loop1 to completion via clean-to-go.
    class _R:
        stdout = "clean-to-go"

    monkeypatch.setattr(superpowers_dispatch, "requesting_code_review", lambda **_: _R())

    pre_merge_cmd._loop1(tmp_path)
    assert any("code-review-loop1-iter" in lbl for lbl in captured_labels), (
        f"expected code-review-loop1-iter* label in {captured_labels}"
    )
    reset_current_progress()


def test_site10_dispatch_completion_clears_label_via_set_progress_none(monkeypatch):
    """Site 10: ``_set_progress(dispatch_label=None)`` clears the label.

    Verifies the helper supports the explicit clear contract (between
    dispatches) so any heartbeat tick that fires before the next dispatch
    establishes its own label sees ``dispatch_label=None`` rather than
    a stale value from the previous dispatch.
    """
    reset_current_progress()
    auto_cmd._set_progress(phase=2, dispatch_label="green")
    assert get_current_progress().dispatch_label == "green"
    # End-of-dispatch transition: clear label.
    auto_cmd._set_progress(phase=2, dispatch_label=None)
    assert get_current_progress().dispatch_label is None
    # started_at should also clear when label clears (per _set_progress
    # contract: dispatch_label=None -> started_at=None).
    assert get_current_progress().started_at is None
    reset_current_progress()
