#!/usr/bin/env python3
# Author: Julian Bolivar
# Version: 1.0.0
# Date: 2026-04-23
"""Interactive MAGI escalation prompt (Feature A, v0.2.0).

Fires when INV-11 safety valve exhausts in `/sbtdd spec` (Checkpoint 2) or
`/sbtdd pre-merge` (Loop 2). INV-22 forbids running inside `/sbtdd auto`:
auto invocations consult `.claude/magi-auto-policy.json` instead.

Public API:
    build_escalation_context(iterations, plan_id, context) -> EscalationContext
    format_escalation_message(ctx) -> str
    prompt_user(ctx, options) -> UserDecision
    apply_decision(decision, ctx, root) -> int  # writes audit artifact

Precedent: Milestone D Checkpoint 2 iter 3 chat escalation (commit 5d7bfc4).
"""

from __future__ import annotations

import enum
from dataclasses import dataclass
from typing import Any, Literal

from magi_dispatch import MAGIVerdict


class _RootCause(enum.Enum):
    INFRA_TRANSIENT = "infra_transient"  # same agent fails across iters
    PLAN_VS_SPEC = "plan_vs_spec"  # CRITICAL findings persist
    STRUCTURAL_DEFECT = "structural_defect"  # STRONG_NO_GO from >=1 agent
    SPEC_AMBIGUITY = "spec_ambiguity"  # confidence trending down


_ContextLit = Literal["checkpoint2", "pre-merge", "auto"]
_ActionLit = Literal["override", "retry", "abandon", "alternative"]


@dataclass(frozen=True)
class EscalationOption:
    letter: str  # 'a' | 'b' | 'c' | 'd'
    action: _ActionLit
    rationale: str  # shown in the menu after the action verb
    caveat: str = ""  # optional consequence / tradeoff line


@dataclass(frozen=True)
class EscalationContext:
    iterations: tuple[dict[str, Any], ...]  # per-iter verdict snapshots
    plan_id: str
    context: _ContextLit
    per_agent_verdicts: tuple[tuple[str, str], ...]  # (agent_name, verdict)
    findings: tuple[tuple[str, str], ...]  # (severity, text)
    root_cause: _RootCause


@dataclass(frozen=True)
class UserDecision:
    chosen_option: str
    action: _ActionLit
    reason: str


_ROOT_LABELS: dict[_RootCause, str] = {
    _RootCause.INFRA_TRANSIENT: "transient-infra (agent degraded repite)",
    _RootCause.PLAN_VS_SPEC: "plan-vs-spec gap (CRITICAL findings persisten)",
    _RootCause.STRUCTURAL_DEFECT: "defecto estructural (STRONG_NO_GO)",
    _RootCause.SPEC_AMBIGUITY: "spec ambiguity (confidence trending down)",
}

_OPT_OVERRIDE = EscalationOption(
    letter="a",
    action="override",
    rationale="Override INV-0 (user authority)",
    caveat="requires --reason; audit artifact written.",
)
_OPT_RETRY = EscalationOption(
    letter="b",
    action="retry",
    rationale="Re-invocar MAGI una iter mas (safety valve +1)",
    caveat="consume iter extra; INV-0 override del INV-11.",
)
_OPT_ALTERNATIVE = EscalationOption(
    letter="c",
    action="alternative",
    rationale="Replan: split spec o ajustar scope",
    caveat="reinicia flujo desde sec.1.",
)
_OPT_ABANDON = EscalationOption(
    letter="d",
    action="abandon",
    rationale="Exit 8 (v0.1 behavior) + artefactos para review manual",
    caveat="default en non-TTY.",
)

_MENU_LETTERS = ("a", "b", "c", "d")


def _finding_severity(finding: Any, default: str = "INFO") -> str:
    """Normalize a finding's ``severity`` field to an uppercase string."""
    return str(finding.get("severity", default)).upper()


def _classify_root_cause(iterations: list[MAGIVerdict]) -> _RootCause:
    """Infer the dominant failure mode across iterations."""
    if any(v.verdict == "STRONG_NO_GO" for v in iterations):
        return _RootCause.STRUCTURAL_DEFECT
    degraded_count = sum(1 for v in iterations if v.degraded)
    if degraded_count >= 2 and degraded_count >= len(iterations) / 2:
        return _RootCause.INFRA_TRANSIENT
    critical_across = [
        any(_finding_severity(f, default="") == "CRITICAL" for f in v.findings) for v in iterations
    ]
    if sum(critical_across) >= 2:
        return _RootCause.PLAN_VS_SPEC
    return _RootCause.SPEC_AMBIGUITY


def build_escalation_context(
    iterations: list[MAGIVerdict],
    plan_id: str,
    context: _ContextLit,
) -> EscalationContext:
    """Collect iter history + classify root cause."""
    snapshots = tuple(
        {
            "verdict": v.verdict,
            "degraded": v.degraded,
            "n_conditions": len(v.conditions),
            "n_findings": len(v.findings),
        }
        for v in iterations
    )
    per_agent: tuple[tuple[str, str], ...] = ()  # v0.2: MAGI does not expose per-agent breakdown
    findings = tuple(
        (_finding_severity(f), str(f.get("text", f))) for v in iterations for f in v.findings
    )
    return EscalationContext(
        iterations=snapshots,
        plan_id=plan_id,
        context=context,
        per_agent_verdicts=per_agent,
        findings=findings,
        root_cause=_classify_root_cause(iterations),
    )


def _compose_options(ctx: EscalationContext) -> tuple[EscalationOption, ...]:
    """Build a context-aware menu (<=4 options) keyed by root cause.

    STRUCTURAL_DEFECT only exposes (a) abandon; every other root cause
    exposes override, retry, alternative, abandon so the canonical
    template emits four sequential letters.
    """
    if ctx.root_cause == _RootCause.STRUCTURAL_DEFECT:
        opts: tuple[EscalationOption, ...] = (_OPT_ABANDON,)
    else:
        opts = (_OPT_OVERRIDE, _OPT_RETRY, _OPT_ALTERNATIVE, _OPT_ABANDON)
    return tuple(
        EscalationOption(
            letter=_MENU_LETTERS[i],
            action=o.action,
            rationale=o.rationale,
            caveat=o.caveat,
        )
        for i, o in enumerate(opts)
    )


def format_escalation_message(ctx: EscalationContext) -> str:
    """Render the canonical escalation template (<=40 lines).

    Output mirrors the precedent from Milestone D Checkpoint 2 iter 3
    escalation (commit 5d7bfc4): root-cause hint, iter counter, findings
    tally, and the dynamic option menu followed by the Spanish prompt.
    """
    n = len(ctx.iterations)
    last = ctx.iterations[-1] if ctx.iterations else {"verdict": "?", "degraded": False}
    root_label = _ROOT_LABELS[ctx.root_cause]
    opts = _compose_options(ctx)
    lines = [
        f"MAGI iter {n} FINAL ({ctx.context}): veredicto '{last['verdict']}' degraded={last['degraded']}.",
        f"Causa raiz inferida: {root_label}.",
        f"Safety valve INV-11 exhausted tras {n} iter.",
        "",
        "Escalando al usuario per INV-11 + INV-18:",
        "",
        f"Estado plan {ctx.plan_id}:",
        f"- Iteraciones: {n}",
        f"- Findings residuales: {len(ctx.findings)}",
        "",
        "Opciones per INV-0 (user authority):",
    ]
    for o in opts:
        line = f"- ({o.letter}) {o.action}: {o.rationale}."
        if o.caveat:
            line += f" {o.caveat}"
        lines.append(line)
    lines.append("")
    lines.append("¿Cuál?")
    return "\n".join(lines)
