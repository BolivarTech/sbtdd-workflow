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
    findings: tuple[object, ...] = (),
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
