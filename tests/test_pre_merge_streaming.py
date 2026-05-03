#!/usr/bin/env python3
# Author: Julian Bolivar
# Version: 1.0.0
# Date: 2026-04-25
"""Tests for v0.4.0 J8 pre-merge stream_prefix wiring.

J8.1 -- ``_loop2`` MAGI dispatch threads a ``stream_prefix`` containing
the ``magi-loop2`` tag and the iteration number.

J8.2 -- ``_loop1`` ``/requesting-code-review`` and ``/receiving-code-review``
dispatches thread a ``stream_prefix`` containing the ``loop1`` tag and
the iteration number.

J8.3 -- Loop 2 finding-remediation dispatch (the inner
``/receiving-code-review`` call orchestrating MAGI conditions) threads a
``stream_prefix`` starting with ``fix-finding-`` so operators can
correlate the streaming output with which iteration's findings are being
processed. v0.4.0 surface adaptation: ``_loop2``'s iter-3 redesign
removed the literal three-commit mini-cycle, so J8.3 is satisfied by
tagging the per-iter finding-batch dispatch rather than per-phase
red/green/refactor commits (those now live behind ``sbtdd close-phase``,
out of pre_merge_cmd's control).
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "skills" / "sbtdd" / "scripts"))

import magi_dispatch
import pre_merge_cmd
import superpowers_dispatch


def _make_magi_verdict(
    *,
    verdict: str = "GO",
    degraded: bool = False,
    conditions: tuple[str, ...] = (),
    findings: tuple[dict[str, object], ...] = (),
) -> magi_dispatch.MAGIVerdict:
    """Build a minimal :class:`MAGIVerdict` for monkeypatched dispatch."""
    return magi_dispatch.MAGIVerdict(
        verdict=verdict,
        degraded=degraded,
        conditions=conditions,
        findings=findings,
        raw_output="{}",
    )


def test_loop2_magi_dispatch_passes_stream_prefix(tmp_path, monkeypatch):
    """J8.1: pre_merge ``_loop2`` MAGI dispatch threads ``stream_prefix``.

    Forces a clean ``GO`` verdict on iter 1 so ``_loop2`` exits via the
    happy-path. Captures the kwargs ``invoke_magi`` was called with and
    asserts that the iter-N tagged stream_prefix landed in the kwargs.
    """
    captured_kwargs: list[dict[str, object]] = []

    def fake_invoke_magi(*args, **kwargs):  # type: ignore[no-untyped-def]
        captured_kwargs.append(dict(kwargs))
        return _make_magi_verdict(verdict="GO")

    monkeypatch.setattr(magi_dispatch, "invoke_magi", fake_invoke_magi)
    # Build a minimal config: pass a non-existent plan path; ``_loop2``
    # only stringifies ``cfg.plan_path`` for the context-paths list, so
    # any value works for this test.
    from types import SimpleNamespace

    cfg = SimpleNamespace(
        plan_path="planning/claude-plan-tdd.md",
        magi_threshold="GO_WITH_CAVEATS",
        magi_max_iterations=3,
    )
    pre_merge_cmd._loop2(tmp_path, cfg, threshold_override=None)
    assert captured_kwargs, "invoke_magi was never called"
    sp = captured_kwargs[0].get("stream_prefix")
    assert isinstance(sp, str), (
        f"stream_prefix kwarg must be a string, got {type(sp).__name__}: {sp!r}"
    )
    assert "magi-loop2" in sp, (
        f"Loop 2 MAGI dispatch must thread a 'magi-loop2'-tagged stream_prefix, got {sp!r}"
    )
    assert "iter-1" in sp, (
        f"Loop 2 MAGI dispatch must include the iteration number in stream_prefix, got {sp!r}"
    )


def test_loop1_dispatches_pass_stream_prefix(tmp_path, monkeypatch):
    """J8.2: ``_loop1`` ``requesting_code_review`` and ``receiving_code_review``
    dispatches thread ``stream_prefix`` tagged ``loop1`` with iter number.

    Drives the loop with a stub that reports ``not-clean-to-go`` once
    then ``clean-to-go`` so both ``requesting_code_review`` and
    ``receiving_code_review`` fire at least once before the loop exits
    cleanly.
    """
    requesting_calls: list[dict[str, object]] = []
    receiving_calls: list[dict[str, object]] = []
    iter_holder = {"n": 0}

    class FakeResult:
        def __init__(self, clean: bool) -> None:
            # ``_is_clean_to_go`` does substring match for
            # ``clean-to-go``; pick a non-clean payload that does NOT
            # contain that substring (the literal ``not-clean-to-go``
            # would still match because ``clean-to-go`` is embedded).
            self.stdout = "clean-to-go" if clean else "findings outstanding"

    def fake_requesting(**kwargs):  # type: ignore[no-untyped-def]
        requesting_calls.append(dict(kwargs))
        iter_holder["n"] += 1
        return FakeResult(clean=iter_holder["n"] >= 2)

    def fake_receiving(**kwargs):  # type: ignore[no-untyped-def]
        receiving_calls.append(dict(kwargs))
        return FakeResult(clean=True)

    monkeypatch.setattr(superpowers_dispatch, "requesting_code_review", fake_requesting)
    monkeypatch.setattr(superpowers_dispatch, "receiving_code_review", fake_receiving)
    pre_merge_cmd._loop1(tmp_path)
    assert requesting_calls, "requesting_code_review was never called"
    # First requesting call corresponds to iter 1; loop1 may iterate
    # multiple times before clean-to-go. Every call should carry a
    # loop1-tagged prefix.
    assert all(
        isinstance(call.get("stream_prefix"), str) and "loop1" in (call["stream_prefix"] or "")
        for call in requesting_calls
    ), (
        "every Loop 1 requesting_code_review call must thread a 'loop1'-tagged "
        f"stream_prefix; got {[c.get('stream_prefix') for c in requesting_calls]!r}"
    )
    # iter-1 must appear at least once (first iteration).
    assert any("iter-1" in (call.get("stream_prefix") or "") for call in requesting_calls), (
        "first Loop 1 requesting_code_review call must include 'iter-1' tag; "
        f"got {[c.get('stream_prefix') for c in requesting_calls]!r}"
    )
    # receiving_code_review fires when the requesting result is not
    # clean-to-go: check at least one call carries a loop1 prefix.
    assert receiving_calls, "receiving_code_review was never called in Loop 1"
    assert all(
        isinstance(call.get("stream_prefix"), str) and "loop1" in (call["stream_prefix"] or "")
        for call in receiving_calls
    ), (
        "every Loop 1 receiving_code_review call must thread a 'loop1'-tagged "
        f"stream_prefix; got {[c.get('stream_prefix') for c in receiving_calls]!r}"
    )


def test_loop2_finding_dispatch_passes_phase_specific_stream_prefix(tmp_path, monkeypatch):
    """J8.3: Loop 2 finding-remediation ``receiving_code_review`` dispatch
    threads a ``stream_prefix`` starting with ``fix-finding-``.

    v0.4.0 surface adaptation: ``_loop2``'s iter-3 redesign no longer
    drives a per-finding red/green/refactor mini-cycle from inside
    pre_merge_cmd. The closest analogue is the per-iter
    ``/receiving-code-review`` dispatch that classifies MAGI conditions
    as accepted/rejected. Tagging that call with ``fix-finding-iter-N``
    satisfies the operator-visibility intent of J8.3 (correlate streaming
    output with which iteration's findings are being remediated) without
    inventing a new mini-cycle that does not exist in the v0.4.0 code
    path.
    """
    captured_magi: list[dict[str, object]] = []
    captured_receiving: list[dict[str, object]] = []

    def fake_invoke_magi(*args, **kwargs):  # type: ignore[no-untyped-def]
        captured_magi.append(dict(kwargs))
        # Return verdict with one MAGI condition so receiving_code_review
        # is invoked at least once.
        if len(captured_magi) == 1:
            return _make_magi_verdict(
                verdict="GO_WITH_CAVEATS",
                conditions=("Add docstring to foo()",),
            )
        return _make_magi_verdict(verdict="GO")

    def fake_receiving(**kwargs):  # type: ignore[no-untyped-def]
        captured_receiving.append(dict(kwargs))

        # Return a result whose parser (parse_receiving_review reads
        # ``.stdout``) produces all-rejected so _loop2 avoids the
        # "accepted -> exit 8" branch and continues iterating until the
        # next MAGI verdict (clean GO) returns success.
        class _R:
            stdout = "## Accepted\n\n## Rejected\n\n- Add docstring to foo() -- noise.\n"

        return _R()

    monkeypatch.setattr(magi_dispatch, "invoke_magi", fake_invoke_magi)
    monkeypatch.setattr(superpowers_dispatch, "receiving_code_review", fake_receiving)
    from types import SimpleNamespace

    cfg = SimpleNamespace(
        plan_path="planning/claude-plan-tdd.md",
        magi_threshold="GO_WITH_CAVEATS",
        magi_max_iterations=3,
    )
    pre_merge_cmd._loop2(tmp_path, cfg, threshold_override=None)
    assert captured_receiving, "Loop 2 receiving_code_review was never invoked"
    sp = captured_receiving[0].get("stream_prefix")
    assert isinstance(sp, str), (
        f"Loop 2 receiving_code_review stream_prefix must be a string, "
        f"got {type(sp).__name__}: {sp!r}"
    )
    assert "fix-finding-" in sp, (
        f"Loop 2 finding-remediation dispatch must include 'fix-finding-' tag "
        f"in stream_prefix; got {sp!r}"
    )


# v1.0.0 S1-26 + S1-27: spec-snapshot drift check + plan-approval emit hook.
def test_h2_3_pre_merge_raises_on_spec_snapshot_drift(tmp_path, monkeypatch):
    """H2-3: _check_spec_snapshot_drift raises MAGIGateError when scenarios changed."""
    import pytest
    from errors import MAGIGateError

    # Persisted snapshot at plan-approval time.
    persisted = tmp_path / "spec-snapshot.json"
    persisted.write_text('{"S1: parser handles empty input": "old-hash"}', encoding="utf-8")
    spec = tmp_path / "spec-behavior.md"
    spec.write_text("# placeholder; emit_snapshot is monkeypatched", encoding="utf-8")
    state = tmp_path / "session-state.json"  # absent — file-based detection

    monkeypatch.setattr(
        "spec_snapshot.emit_snapshot",
        lambda _p: {"S1: parser handles empty input": "new-hash"},
    )

    with pytest.raises(MAGIGateError) as excinfo:
        pre_merge_cmd._check_spec_snapshot_drift(
            spec_path=spec,
            snapshot_path=persisted,
            state_file_path=state,
        )
    msg = str(excinfo.value)
    assert "S1: parser handles empty input" in msg
    assert "re-approve" in msg.lower() or "re-run" in msg.lower()


def test_h2_3_pre_merge_passes_when_no_drift(tmp_path, monkeypatch):
    """H2-3: no drift -> _check_spec_snapshot_drift returns None silently."""
    persisted = tmp_path / "spec-snapshot.json"
    persisted.write_text('{"S1": "matching"}', encoding="utf-8")
    spec = tmp_path / "spec-behavior.md"
    spec.write_text("# placeholder", encoding="utf-8")
    state = tmp_path / "session-state.json"  # absent

    monkeypatch.setattr(
        "spec_snapshot.emit_snapshot",
        lambda _p: {"S1": "matching"},
    )

    assert (
        pre_merge_cmd._check_spec_snapshot_drift(
            spec_path=spec,
            snapshot_path=persisted,
            state_file_path=state,
        )
        is None
    )


def test_h2_3_missing_snapshot_warns_but_does_not_block(tmp_path, monkeypatch, capsys):
    """H2-3: missing snapshot file + missing watermark -> stderr breadcrumb, no error.

    Backward compat: pre-v1.0.0 plan-approval flows did not emit a snapshot
    AND did not write the watermark. Pre-merge logs a warning but does not
    block.
    """
    spec = tmp_path / "spec-behavior.md"
    spec.write_text("# placeholder", encoding="utf-8")
    snapshot_path = tmp_path / "spec-snapshot.json"  # does not exist
    state = tmp_path / "session-state.json"  # also does not exist

    monkeypatch.setattr(
        "spec_snapshot.emit_snapshot",
        lambda _p: {"S1": "anything"},
    )

    assert (
        pre_merge_cmd._check_spec_snapshot_drift(
            spec_path=spec,
            snapshot_path=snapshot_path,
            state_file_path=state,
        )
        is None
    )
    captured = capsys.readouterr()
    assert "spec-snapshot.json" in captured.err


def test_h2_5_missing_snapshot_with_watermark_raises(tmp_path, monkeypatch):
    """H2-5 (caspar iter 4 W2): watermark in state file + missing snapshot
    file = bypass-by-deletion detected, MAGIGateError raised.
    """
    import json as _json
    import pytest
    from errors import MAGIGateError

    spec = tmp_path / "spec-behavior.md"
    spec.write_text("# placeholder", encoding="utf-8")
    snapshot_path = tmp_path / "spec-snapshot.json"  # does NOT exist
    state = tmp_path / "session-state.json"
    state.write_text(
        _json.dumps({"spec_snapshot_emitted_at": "2026-05-01T12:00:00Z"}),
        encoding="utf-8",
    )

    monkeypatch.setattr(
        "spec_snapshot.emit_snapshot",
        lambda _p: {"S1": "anything"},
    )

    with pytest.raises(MAGIGateError) as excinfo:
        pre_merge_cmd._check_spec_snapshot_drift(
            spec_path=spec,
            snapshot_path=snapshot_path,
            state_file_path=state,
        )
    msg = str(excinfo.value)
    assert "deleted" in msg.lower() or "re-emit" in msg.lower()
    assert "2026-05-01T12:00:00Z" in msg  # watermark surfaced as evidence


# ---------------------------------------------------------------------------
# v1.0.0 O-2 Loop 1 review CRITICAL #2 (C2): Wire _check_spec_snapshot_drift
# at pre-merge entry. Spec sec.3.2 H2-3 + H2-5 escenarios unreachable in
# production without the wiring; the helper is unit-tested but never called.
# ---------------------------------------------------------------------------


def _seed_basic_pre_merge_env(tmp_path):
    """Seed minimal valid env for pre_merge_cmd.main: state, plan, plugin.local.md, repo."""
    import json as _json
    import shutil
    import subprocess as _sp
    from pathlib import Path as _P

    # plugin.local.md
    (tmp_path / ".claude").mkdir(exist_ok=True)
    fixture = _P(__file__).parent / "fixtures" / "plugin-locals" / "valid-python.md"
    shutil.copy(fixture, tmp_path / ".claude" / "plugin.local.md")

    # state
    state = {
        "plan_path": "planning/claude-plan-tdd.md",
        "current_task_id": None,
        "current_task_title": None,
        "current_phase": "done",
        "phase_started_at_commit": "abc1234",
        "last_verification_at": "2026-04-20T03:30:00Z",
        "last_verification_result": "passed",
        "plan_approved_at": "2026-04-20T03:30:00Z",
    }
    (tmp_path / ".claude" / "session-state.json").write_text(_json.dumps(state), encoding="utf-8")

    # plan with all checkboxes done
    (tmp_path / "planning").mkdir(exist_ok=True)
    (tmp_path / "planning" / "claude-plan-tdd.md").write_text(
        "# Plan\n\n### Task 1: done\n- [x] step\n", encoding="utf-8"
    )

    # spec
    (tmp_path / "sbtdd").mkdir(exist_ok=True)
    (tmp_path / "sbtdd" / "spec-behavior.md").write_text("# placeholder spec\n", encoding="utf-8")

    # git repo
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


def test_c2_pre_merge_main_invokes_spec_snapshot_drift_check(tmp_path, monkeypatch):
    """C2: pre_merge_cmd.main() calls _check_spec_snapshot_drift before Loop 1.

    Spy on _check_spec_snapshot_drift; assert it's called once with the three
    expected paths (spec, snapshot, state file).
    """
    import magi_dispatch
    import pre_merge_cmd

    _seed_basic_pre_merge_env(tmp_path)

    spy = {"calls": 0, "kwargs": None}

    def fake_drift_check(*, spec_path, snapshot_path, state_file_path):
        spy["calls"] += 1
        spy["kwargs"] = {
            "spec_path": spec_path,
            "snapshot_path": snapshot_path,
            "state_file_path": state_file_path,
        }

    monkeypatch.setattr(pre_merge_cmd, "_check_spec_snapshot_drift", fake_drift_check)
    # Stub Loop 1 + Loop 2 to keep the test focused on the wiring.
    monkeypatch.setattr(pre_merge_cmd, "_loop1", lambda root: None)

    def fake_loop2(root, cfg, override, ns):
        return magi_dispatch.MAGIVerdict(
            verdict="GO",
            degraded=False,
            conditions=(),
            findings=(),
            raw_output='{"verdict": "GO"}',
        )

    monkeypatch.setattr(pre_merge_cmd, "_loop2", fake_loop2)
    monkeypatch.setattr(magi_dispatch, "write_verdict_artifact", lambda *a, **kw: None)
    monkeypatch.setattr(pre_merge_cmd, "detect_drift", lambda *a, **kw: None)

    rc = pre_merge_cmd.main(["--project-root", str(tmp_path)])
    assert rc == 0
    assert spy["calls"] == 1
    # Three expected paths (the wiring contract).
    assert spy["kwargs"]["spec_path"] == tmp_path / "sbtdd" / "spec-behavior.md"
    assert spy["kwargs"]["snapshot_path"] == tmp_path / "planning" / "spec-snapshot.json"
    assert spy["kwargs"]["state_file_path"] == tmp_path / ".claude" / "session-state.json"


def test_c2_pre_merge_main_aborts_on_spec_drift_before_loop1(tmp_path, monkeypatch):
    """C2: drift detected -> MAGIGateError raised BEFORE Loop 1 runs."""
    import pytest as _pytest
    import magi_dispatch
    import pre_merge_cmd
    from errors import MAGIGateError

    _seed_basic_pre_merge_env(tmp_path)
    # Persisted snapshot at plan-approval time.
    persisted = tmp_path / "planning" / "spec-snapshot.json"
    persisted.write_text('{"S1: parser handles empty input": "old-hash"}', encoding="utf-8")
    # Force the spec_snapshot.emit_snapshot to return a different hash so drift fires.
    monkeypatch.setattr(
        "spec_snapshot.emit_snapshot",
        lambda _p: {"S1: parser handles empty input": "new-hash"},
    )

    loop1_calls = {"count": 0}

    def fake_loop1(root):
        loop1_calls["count"] += 1

    monkeypatch.setattr(pre_merge_cmd, "_loop1", fake_loop1)
    # Stub Loop 2 to keep the test fast; if drift gate fires correctly, this
    # stub is never reached (the gate must abort before Loop 1 / Loop 2).
    monkeypatch.setattr(
        pre_merge_cmd,
        "_loop2",
        lambda *a, **kw: magi_dispatch.MAGIVerdict(
            verdict="GO",
            degraded=False,
            conditions=(),
            findings=(),
            raw_output='{"verdict": "GO"}',
        ),
    )
    monkeypatch.setattr(magi_dispatch, "write_verdict_artifact", lambda *a, **kw: None)
    monkeypatch.setattr(pre_merge_cmd, "detect_drift", lambda *a, **kw: None)

    with _pytest.raises(MAGIGateError) as excinfo:
        pre_merge_cmd.main(["--project-root", str(tmp_path)])
    msg = str(excinfo.value)
    assert "S1: parser handles empty input" in msg
    # Loop 1 must NOT have run (the drift gate fires before Loop 1).
    assert loop1_calls["count"] == 0


def test_c2_auto_phase3_invokes_spec_snapshot_drift_check(tmp_path, monkeypatch):
    """C2: auto_cmd._phase3_pre_merge invokes _check_spec_snapshot_drift before Loop 1."""
    import auto_cmd
    import magi_dispatch
    import pre_merge_cmd
    from config import load_plugin_local

    _seed_basic_pre_merge_env(tmp_path)
    cfg = load_plugin_local(tmp_path / ".claude" / "plugin.local.md")

    spy = {"calls": 0, "kwargs": None}

    def fake_drift_check(*, spec_path, snapshot_path, state_file_path):
        spy["calls"] += 1
        spy["kwargs"] = {
            "spec_path": spec_path,
            "snapshot_path": snapshot_path,
            "state_file_path": state_file_path,
        }

    monkeypatch.setattr(pre_merge_cmd, "_check_spec_snapshot_drift", fake_drift_check)
    monkeypatch.setattr(pre_merge_cmd, "_loop1", lambda root: None)

    def fake_loop2(root, cfg2, threshold):
        return magi_dispatch.MAGIVerdict(
            verdict="GO",
            degraded=False,
            conditions=(),
            findings=(),
            raw_output='{"verdict": "GO"}',
        )

    monkeypatch.setattr(pre_merge_cmd, "_loop2", fake_loop2)
    monkeypatch.setattr(magi_dispatch, "write_verdict_artifact", lambda *a, **kw: None)

    ns = auto_cmd._build_parser().parse_args(["--project-root", str(tmp_path)])
    auto_cmd._phase3_pre_merge(ns, cfg)
    assert spy["calls"] == 1
    assert spy["kwargs"]["spec_path"] == tmp_path / "sbtdd" / "spec-behavior.md"
    assert spy["kwargs"]["snapshot_path"] == tmp_path / "planning" / "spec-snapshot.json"
    assert spy["kwargs"]["state_file_path"] == tmp_path / ".claude" / "session-state.json"
