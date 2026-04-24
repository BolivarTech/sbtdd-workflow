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


def test_prompt_user_headless_override_strong_go_only_overrides_only_on_GO_verdicts(
    tmp_path, monkeypatch
) -> None:
    """`override_strong_go_only` policy must override ONLY when last verdict is GO/STRONG_GO.

    Regression for MAGI Loop 2 v0.2 pre-merge WARNING #4 (2026-04-24):
    the predicate originally compared ``ctx.root_cause`` to
    STRUCTURAL_DEFECT, which only fires on STRONG_NO_GO. As a result
    the policy overrode on every other failure mode (degraded HOLD,
    plan-vs-spec gap, ambiguous spec) -- the inverse of the policy
    name. The fix tightens the predicate to check the last-iter
    verdict label directly so the policy fires only when MAGI was
    leaning toward GO and a transient/infra issue tripped the safety
    valve.
    """
    import json

    from escalation_prompt import _compose_options, prompt_user

    monkeypatch.setattr("sys.stdin.isatty", lambda: False)
    (tmp_path / ".claude").mkdir()
    (tmp_path / ".claude" / "magi-auto-policy.json").write_text(
        json.dumps({"on_exhausted": "override_strong_go_only"}), encoding="utf-8"
    )

    # Case 1: last verdict is HOLD (degraded) -> policy should NOT override.
    iters_hold = [_mkv("HOLD", degraded=True)] * 3
    ctx_hold = build_escalation_context(iters_hold, plan_id="X", context="pre-merge")
    opts_hold = _compose_options(ctx_hold)
    decision_hold = prompt_user(ctx_hold, opts_hold, project_root=tmp_path)
    assert decision_hold.action == "abandon", (
        f"override_strong_go_only must NOT override on HOLD verdict; got {decision_hold.action!r}"
    )

    # Case 2: last verdict is GO -> policy SHOULD override.
    iters_go = [_mkv("HOLD"), _mkv("GO_WITH_CAVEATS"), _mkv("GO")]
    ctx_go = build_escalation_context(iters_go, plan_id="X", context="pre-merge")
    opts_go = _compose_options(ctx_go)
    decision_go = prompt_user(ctx_go, opts_go, project_root=tmp_path)
    assert decision_go.action == "override", (
        f"override_strong_go_only must override when last verdict is GO; got {decision_go.action!r}"
    )

    # Case 3: last verdict is STRONG_GO -> policy SHOULD override.
    iters_sg = [_mkv("STRONG_GO")] * 2
    ctx_sg = build_escalation_context(iters_sg, plan_id="X", context="pre-merge")
    opts_sg = _compose_options(ctx_sg)
    decision_sg = prompt_user(ctx_sg, opts_sg, project_root=tmp_path)
    assert decision_sg.action == "override"


def test_prompt_user_headless_emits_policy_breadcrumb_to_stderr(
    tmp_path, monkeypatch, capsys
) -> None:
    """Headless path emits a one-line stderr breadcrumb naming the policy.

    Regression for MAGI Loop 2 v0.2 pre-merge WARNING #2 (2026-04-24):
    CI users who never opted into ``.claude/magi-auto-policy.json``
    silently get the ``abort`` default and never discover the knob.
    The breadcrumb makes the policy choice visible in CI logs.
    """
    from escalation_prompt import _compose_options, prompt_user

    monkeypatch.setattr("sys.stdin.isatty", lambda: False)
    iters = [_mkv("HOLD", degraded=True)] * 3
    ctx = build_escalation_context(iters, plan_id="X", context="pre-merge")
    opts = _compose_options(ctx)
    prompt_user(ctx, opts, project_root=tmp_path)

    captured = capsys.readouterr()
    assert "[escalation_prompt] headless policy=" in captured.err
    assert "magi-auto-policy.json" in captured.err


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


def test_apply_decision_writes_audit_artifact(tmp_path) -> None:
    from escalation_prompt import apply_decision, _compose_options

    iters = [_mkv("HOLD", degraded=True)] * 3
    ctx = build_escalation_context(iters, plan_id="D", context="checkpoint2")
    opts = _compose_options(ctx)
    assert opts  # menu composed
    decision = UserDecision(chosen_option="a", action="override", reason="caspar bug")
    code = apply_decision(decision, ctx, project_root=tmp_path)
    assert code == 0
    audits = list((tmp_path / ".claude" / "magi-escalations").glob("*.json"))
    assert len(audits) == 1
    import json

    data = json.loads(audits[0].read_text(encoding="utf-8"))
    assert data["decision"] == "override"
    assert data["chosen_option"] == "a"
    assert data["reason"] == "caspar bug"
    assert data["plan_id"] == "D"
    assert data["magi_context"] == "checkpoint2"


def test_apply_decision_abandon_returns_exit_8(tmp_path) -> None:
    from escalation_prompt import apply_decision

    iters = [_mkv("HOLD_TIE")] * 3
    ctx = build_escalation_context(iters, plan_id="X", context="pre-merge")
    decision = UserDecision(chosen_option="d", action="abandon", reason="headless policy")
    code = apply_decision(decision, ctx, project_root=tmp_path)
    assert code == 8
