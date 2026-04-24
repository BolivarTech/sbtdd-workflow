#!/usr/bin/env python3
# Author: Julian Bolivar
# Version: 1.0.0
# Date: 2026-04-23
"""Unit tests for escalation_prompt module (Feature A)."""

from __future__ import annotations

from pathlib import Path

import pytest

from escalation_prompt import (
    EscalationContext,
    EscalationOption,
    UserDecision,
    _classify_root_cause,
    _RootCause,
    build_escalation_context,
)
from magi_dispatch import MAGIVerdict

FIXTURES = Path(__file__).resolve().parent / "fixtures" / "magi-escalations"


def test_escalation_context_is_frozen() -> None:
    ctx = EscalationContext(
        iterations=(),
        plan_id="A",
        context="checkpoint2",
        per_agent_verdicts=(),
        findings=(),
        root_cause=_RootCause.INFRA_TRANSIENT,
    )
    with pytest.raises((AttributeError, Exception)):
        ctx.plan_id = "B"  # frozen


def test_user_decision_is_frozen_and_carries_reason() -> None:
    d = UserDecision(chosen_option="a", action="override", reason="caspar JSON bug again")
    assert d.chosen_option == "a"
    assert d.reason == "caspar JSON bug again"
    with pytest.raises((AttributeError, Exception)):
        d.reason = "changed"


def test_escalation_option_has_letter_action_rationale() -> None:
    opt = EscalationOption(letter="a", action="override", rationale="INV-0 user authority")
    assert opt.letter == "a"
    assert opt.action == "override"


def _mkv(
    verdict: str, degraded: bool = False, findings: tuple = (), conds: tuple = ()
) -> MAGIVerdict:
    return MAGIVerdict(
        verdict=verdict, degraded=degraded, conditions=conds, findings=findings, raw_output=""
    )


def test_classify_infra_transient_when_degraded_repeats() -> None:
    iters = [
        _mkv("HOLD", degraded=True),
        _mkv("GO", degraded=False),
        _mkv("HOLD", degraded=True),
    ]
    assert _classify_root_cause(iters) == _RootCause.INFRA_TRANSIENT


def test_classify_structural_defect_when_strong_no_go_present() -> None:
    iters = [_mkv("STRONG_NO_GO")]
    assert _classify_root_cause(iters) == _RootCause.STRUCTURAL_DEFECT


def test_classify_plan_vs_spec_when_critical_findings_persist() -> None:
    critical = ({"severity": "CRITICAL", "text": "f"},)
    iters = [_mkv("HOLD", findings=critical), _mkv("HOLD", findings=critical)]
    assert _classify_root_cause(iters) == _RootCause.PLAN_VS_SPEC


def test_build_escalation_context_checkpoint2_returns_frozen_struct() -> None:
    iters = [_mkv("HOLD_TIE"), _mkv("HOLD"), _mkv("HOLD_TIE")]
    ctx = build_escalation_context(iterations=iters, plan_id="A", context="checkpoint2")
    assert ctx.plan_id == "A"
    assert ctx.context == "checkpoint2"
    assert len(ctx.iterations) == 3
    assert ctx.root_cause in set(_RootCause)


def test_format_escalation_message_matches_golden_checkpoint2_infra() -> None:
    from escalation_prompt import format_escalation_message

    iters = [
        _mkv("HOLD", degraded=True),
        _mkv("GO", degraded=False),
        _mkv("HOLD", degraded=True),
    ]
    ctx = build_escalation_context(iters, plan_id="D", context="checkpoint2")
    msg = format_escalation_message(ctx)
    # Render must be <=40 lines and include the four expected markers
    assert msg.count("\n") <= 40
    assert "Escalando al usuario" in msg
    assert "Opciones per INV-0" in msg
    assert "(a)" in msg and "(b)" in msg and "(c)" in msg and "(d)" in msg
    assert "Cual?" in msg or "¿Cuál?" in msg


def test_format_escalation_message_structural_defect_omits_retry() -> None:
    from escalation_prompt import format_escalation_message

    iters = [_mkv("STRONG_NO_GO")]
    ctx = build_escalation_context(iters, plan_id="X", context="pre-merge")
    msg = format_escalation_message(ctx)
    # option (b) retry should be absent when STRONG_NO_GO present
    assert "retry" not in msg.lower() or "abandonar" in msg.lower()


def test_prompt_user_non_tty_defaults_to_abandon(monkeypatch, capsys) -> None:
    from escalation_prompt import prompt_user, _compose_options
    iters = [_mkv("HOLD", degraded=True), _mkv("HOLD", degraded=True)]
    ctx = build_escalation_context(iters, plan_id="X", context="pre-merge")
    opts = _compose_options(ctx)
    monkeypatch.setattr("sys.stdin.isatty", lambda: False)
    decision = prompt_user(ctx, opts, non_interactive=True)
    assert decision.action == "abandon"
    assert decision.chosen_option == "d"


def test_prompt_user_tty_accepts_letter(monkeypatch) -> None:
    from escalation_prompt import prompt_user, _compose_options
    iters = [_mkv("HOLD", degraded=True)] * 3
    ctx = build_escalation_context(iters, plan_id="X", context="checkpoint2")
    opts = _compose_options(ctx)
    monkeypatch.setattr("sys.stdin.isatty", lambda: True)
    inputs = iter(["a", "caspar JSON bug"])
    monkeypatch.setattr("builtins.input", lambda prompt="": next(inputs))
    decision = prompt_user(ctx, opts, non_interactive=False)
    assert decision.action == "override"
    assert decision.reason == "caspar JSON bug"


def test_prompt_user_invalid_letter_reprompts(monkeypatch) -> None:
    from escalation_prompt import prompt_user, _compose_options
    iters = [_mkv("HOLD", degraded=True)] * 3
    ctx = build_escalation_context(iters, plan_id="X", context="checkpoint2")
    opts = _compose_options(ctx)
    monkeypatch.setattr("sys.stdin.isatty", lambda: True)
    inputs = iter(["z", "A", "reason text"])
    monkeypatch.setattr("builtins.input", lambda prompt="": next(inputs))
    decision = prompt_user(ctx, opts, non_interactive=False)
    assert decision.chosen_option == "a"
